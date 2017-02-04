#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from pyramid.interfaces import IRequest

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.appserver.pyramid_authorization import has_permission

from nti.contentlibrary.interfaces import IRenderableContentPackage

from nti.contentlibrary_rendering.interfaces import IContentPackageRenderMetadata

from nti.dataserver.authorization import ACT_CONTENT_EDIT

from nti.externalization.interfaces import IExternalMappingDecorator


@interface.implementer(IExternalMappingDecorator)
@component.adapter(IRenderableContentPackage, IRequest)
class _RenderablePackageEditorDecorator(AbstractAuthenticatedRequestAwareDecorator):
    """
    Decorates IRenderableContentPackage with render info.
    """

    def _predicate(self, context, result):
        return  self._is_authenticated \
            and has_permission(ACT_CONTENT_EDIT, context, self.request)

    def _do_decorate_external(self, context, result):
        meta = IContentPackageRenderMetadata(context, None)
        if meta is not None:
            latest_job = meta.mostRecentRenderJob()
            if latest_job is not None:
                result['LatestRenderJob'] = latest_job
