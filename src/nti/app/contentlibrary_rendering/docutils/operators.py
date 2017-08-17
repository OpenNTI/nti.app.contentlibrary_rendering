#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re

from zope import interface

from nti.base._compat import text_
from nti.base._compat import bytes_

from nti.contentlibrary.interfaces import IContentOperator

from nti.ntiids.ntiids import hash_ntiid


def directive(name):
    return re.compile(r"""
                      \.\.[ ]+          # explicit markup start
                      (%s)              # directive name
                      [ ]?              # optional space
                      ::                # directive delimiter
                      ([ ]+|$)          # whitespace or end of line
                      """ % name, re.VERBOSE | re.UNICODE)


@interface.implementer(IContentOperator)
class RenderablePackageContentOperator(object):

    __slots__ = ()

    def __init__(self, *args):
        pass

    def _replace_refs(self, pattern, content, salt):
        for m in re.finditer(pattern, content, re.VERBOSE | re.UNICODE):
            for ntiid in m.groups():  # should only be one
                salted = hash_ntiid(ntiid, salt)
                content = re.sub(ntiid, salted, content)
        return content

    def _replace_noderefs(self, content, salt):
        for prefix in ('ntivideoref', 'napollref', 'naquestionref',
                       'naassignmentref', 'nasurveyref', 'naquestionsetref'):
            pattern = r'\.\.[ ]+%s\s?::\s?(.+)' % prefix
            content = self._replace_refs(pattern, content, salt)
        return content

    def _replace_media(self, content, salt):
        for prefix in ('ntivideoref', 'napollref', 'naquestionref',
                       'naassignmentref', 'nasurveyref', 'naquestionsetref'):
            pattern = r'%s::\s?(.+)' % prefix
            content = self._replace_refs(pattern, content, salt)
        return content

    def replace_all(self, content, salt):
        return self._replace_noderefs(content, salt)

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
        content = self.replace_all(content, salt)
        return bytes_(content) if is_bytes else content
