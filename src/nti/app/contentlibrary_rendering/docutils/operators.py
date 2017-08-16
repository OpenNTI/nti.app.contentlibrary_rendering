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


def get_backup(**kwargs):
    return kwargs.get('backup')


def get_salt(**kwargs):
    return kwargs.get('salt')


@interface.implementer(IContentOperator)
class RenderablePackageContentOperator(object):

    __slots__ = ()

    def __init__(self, *args):
        pass

    def _replace_refs(self, pattern, content, salt):
        for m in re.finditer(pattern, content):
            for ntiid in m.groups():  # should only be one
                salted = hash_ntiid(ntiid, salt)
                content = re.sub(ntiid, salted, content)
        return content

    def replace_all(self, content, salt):
        # replace refs
        for prefix in ('ntivideoref', 'napollref', 'naquestionref',
                       'naassignmentref', 'nasurveyref', 'naquestionsetref'):
            pattern = r'%s::\s?(.+)' % prefix
            content = self._replace_refs(pattern, content, salt)
        return content

    def operate(self, content, unused_context=None, **kwargs):
        if not content:
            return content
        backup = get_backup(**kwargs)
        if backup is None or backup:
            return content
        salt = get_salt(**kwargs)
        if not salt and not backup:
            return content
        is_bytes = isinstance(content, bytes)
        content = text_(content) if is_bytes else content
        content = self.replace_all(content, salt)
        return bytes_(content) if is_bytes else content
