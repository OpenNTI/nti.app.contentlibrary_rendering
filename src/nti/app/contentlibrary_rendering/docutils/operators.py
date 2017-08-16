#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from docutils.nodes import GenericNodeVisitor

from zope import component
from zope import interface

from nti.app.contentlibrary_rendering.docutils.nodes import nticard
from nti.app.contentlibrary_rendering.docutils.nodes import ntivideo
from nti.app.contentlibrary_rendering.docutils.nodes import ntivideoref

from nti.app.contentlibrary_rendering.docutils.utils import make_video_ntiid

from nti.app.contentlibrary_rendering.interfaces import IRSTContentValidator

from nti.contentlibrary.interfaces import IContentOperator

from nti.ntiids.ntiids import hash_ntiid
from nti.ntiids.ntiids import get_specific


def get_backup(**kwargs):
    return kwargs.get('backup')


def get_salt(**kwargs):
    return kwargs.get('salt')


class ContentNodeVisitor(GenericNodeVisitor):

    def __init__(self, document, salt):
        super(ContentNodeVisitor, self).__init__(document)
        self.salt = salt

    def default_visit(self, node):
        if isinstance(node, ntivideoref):
            ntiid = node['ntiid']
            node['ntiid'] = hash_ntiid(ntiid, self.salt)
        elif    isinstance(node, (nticard, ntivideo)) \
            and node.attributes.get('uid'):
            uid = node.attributes.get('uid')
            ntiid = hash_ntiid(make_video_ntiid(uid), self.salt)
            uid = get_specific(ntiid)
            node.attributes['uid'] = uid

    def default_departure(self, node):
        pass

    def unknown_visit(self, node):
        self.default_visit(node) 
    
    def unknown_departure(self, node):
        self.default_departure(node)


@interface.implementer(IContentOperator)
class RenderablePackageContentOperator(object):

    __slots__ = ()

    def __init__(self, *args):
        pass

    def doctree(self, content):
        try:
            validator = component.getUtility(IRSTContentValidator)
            return validator.doctree(content)
        except Exception as e:
            logger.error("Cannot parse content %s", e)
        return None

    def operate(self, content, unused_context, **kwargs):
        backup = get_backup(**kwargs)
        if backup is None or backup:
            return content
        salt = get_salt(**kwargs)
        if not salt and not backup:
            return content
        document = self.doctree(content)
        if document is None:
            return content
        visitor = ContentNodeVisitor(document, salt)
        document.walkabout(visitor)
        return document.pformat()
