#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re

from docutils import statemachine

from zope import interface

from zope.cachedescriptors.property import Lazy

from nti.app.contentlibrary_rendering.docutils.utils import make_video_ntiid

from nti.base._compat import text_
from nti.base._compat import bytes_

from nti.contentlibrary.interfaces import IContentOperator

from nti.ntiids.ntiids import hash_ntiid
from nti.ntiids.ntiids import get_specific


@interface.implementer(IContentOperator)
class RenderablePackageContentOperator(object):

    def __init__(self, *args):
        pass

    @Lazy
    def _node_ref_patterns(self):
        result = []
        for prefix in ('ntivideoref', 'napollref', 'naquestionref',
                       'naassignmentref', 'nasurveyref', 'naquestionsetref'):
            pattern = r'\.\.[ ]+%s\s?::\s?(.+)' % prefix
            pattern = re.compile(pattern, re.VERBOSE | re.UNICODE)
            result.append(pattern)
        return result

    @Lazy
    def _media_patterns(self):
        result = []
        for prefix in ('ntivideo', 'nticard'):
            pattern = r'\.\.[ ]+(%s)\s?::.*' % prefix
            pattern = re.compile(pattern, re.VERBOSE | re.UNICODE)
            result.append(pattern)
        return result
    
    @Lazy
    def _uid_pattern(self):
        pattern = re.compile(r'\s*:uid:\s?(.+)', re.VERBOSE | re.UNICODE)
        return pattern

    def _replace_refs(self, pattern, line, salt):
        m = pattern.match(line)
        if m is not None:
            ntiid = m.groups()[0]
            salted = hash_ntiid(ntiid, salt)
            line = re.sub(ntiid, salted, line)
        return bool(m is not None), line

    def _process_node_refs(self, input_lines, salt, idx, result):
        matched = False
        line = input_lines[idx]
        for pattern in self._node_ref_patterns:
            matched, line = self._replace_refs(pattern, line, salt)
            if matched:
                result.append(line)
                break
        return matched, idx

    def _process_media_nodes(self, input_lines, salt, idx, result):
        matched = False
        line = input_lines[idx]
        for pattern in self._media_patterns:
            matched = bool(pattern.match(line) is not None)
            if matched:
                idx += 1
                result.append(line)
                block, _, _ = input_lines.get_indented(idx, strip_indent=False)
                for _, offset, line in block.xitems():
                    m = self._uid_pattern.search(line)
                    if m is not None:
                        uid = m.groups()[0]
                        ntiid = make_video_ntiid(uid)
                        ntiid = hash_ntiid(ntiid, salt)
                        specific = get_specific(ntiid)
                        line = re.sub(uid, specific, line)
                    result.append(line)
                    idx = offset
                break
        return matched, idx
    
    def replace_all(self, content, salt):
        idx = 0
        result = []
        input_lines = statemachine.string2lines(content)
        input_lines = statemachine.StringList(input_lines, '<string>')
        while idx < len(input_lines):
            matched = False
            for m in (self._process_node_refs, self._process_media_nodes):
                matched, idx = m(input_lines, salt, idx, result)
                if matched:
                    break
            if not matched:
                result.append(input_lines[idx])
            idx += 1
        return u'\n'.join(result)

    def operate(self, content, unused_context=None, **kwargs):
        if not content:
            return content
        backup = kwargs.get('backup')
        if backup is None or backup:
            return content
        salt = kwargs.get('salt')
        if not salt and not backup:
            return content
        is_bytes = isinstance(content, bytes)
        content = text_(content) if is_bytes else content
        try:
            content = self.replace_all(content, salt)
        except Exception:
            logger.exception("Cannot operate on content")
        return bytes_(content) if is_bytes else content
