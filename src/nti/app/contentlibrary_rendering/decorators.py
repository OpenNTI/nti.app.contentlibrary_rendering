#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid.interfaces import IRequest

from zope import component
from zope import interface

from zope.location.interfaces import ILocation

from nti.app.contentlibrary_rendering import VIEW_QUERY_JOB

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.appserver.pyramid_authorization import has_permission

from nti.contentlibrary.interfaces import IRenderableContentPackage

from nti.contentlibrary_rendering.interfaces import IContentPackageRenderMetadata

from nti.dataserver.authorization import ACT_CONTENT_EDIT

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.links.links import Link

LINKS = StandardExternalFields.LINKS

def _package_url_path(package, request):
    ds2 = request.path_info_peek()
    path = '%s/Library/%s' % (ds2, package.ntiid)
    return path


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
                # Decorate the job itself along with a link to fetch job status.
                result['LatestRenderJob'] = latest_job
                _links = result.setdefault(LINKS, [])
                path = _package_url_path( self.context, self.request )
                link = Link(path,
                            rel=VIEW_QUERY_JOB,
                            elements=(VIEW_QUERY_JOB,),
                            params={'job_id': latest_job.job_id})
                interface.alsoProvides(link, ILocation)
                link.__name__ = ''
                link.__parent__ = context
                _links.append(link)
