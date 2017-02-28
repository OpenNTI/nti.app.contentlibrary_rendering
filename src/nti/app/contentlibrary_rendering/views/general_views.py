#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from requests.structures import CaseInsensitiveDict

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.contentlibrary_rendering import VIEW_QUERY_JOB
from nti.app.contentlibrary_rendering import VIEW_RENDER_JOBS

from nti.app.contentlibrary_rendering.views import MessageFactory as _

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.common.string import is_true

from nti.contentlibrary.interfaces import IRenderableContentPackage

from nti.contentlibrary_rendering.interfaces import IContentPackageRenderMetadata

from nti.contentlibrary_rendering.utils import render_package

from nti.dataserver import authorization as nauth

from nti.externalization.externalization import StandardExternalFields

from nti.externalization.interfaces import LocatedExternalDict

ITEMS = StandardExternalFields.ITEMS
NTIID = StandardExternalFields.NTIID
ITEM_COUNT = StandardExternalFields.ITEM_COUNT


@view_config(context=IRenderableContentPackage)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               name="render",
               permission=nauth.ACT_CONTENT_EDIT)
class RenderContentPackageView(AbstractAuthenticatedView,
                               ModeledContentUploadRequestUtilsMixin):

    def readInput(self, value=None):
        result = super(RenderContentPackageView, self).readInput(self, value=value)
        return CaseInsensitiveDict(result)

    def __call__(self):
        data = self.readInput()
        provider = data.get('provider') or 'NTI'
        mark_rendered = data.get('MarkRendered') \
                     or data.get('mark_rendered') or 'True'
        job = render_package(self.context,
                             self.remoteUser,
                             provider,
                             is_true(mark_rendered))
        return job


@view_config(context=IRenderableContentPackage)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               name=VIEW_QUERY_JOB,
               permission=nauth.ACT_CONTENT_EDIT)
class QueryJobView(AbstractAuthenticatedView):
    """
    Fetch the render job for the contextual `IContentPackage`. Optionally,
    a specific job status can be asked for via `job_id`.
    """

    def __call__(self):
        params = CaseInsensitiveDict(self.request.params)
        job_id = params.get('JobId') \
            or params.get('job') \
            or params.get('job_id')
        meta = IContentPackageRenderMetadata(self.context, None)
        if meta is None:
            logger.warn('No meta found for content package (%s)',
                        self.context.ntiid)
            raise hexc.HTTPNotFound(_('Content has not been processed.'))

        if job_id:
            try:
                render_job = meta[job_id]
            except KeyError:
                logger.warn('No job found for content package (%s) (%s)',
                            self.context.ntiid, job_id)
                raise hexc.HTTPNotFound(_('No content found for job key.'))
        else:
            render_job = meta.mostRecentRenderJob()

        if render_job is None:
            logger.warn('No job found for content package (%s)',
                        self.context.ntiid)
            raise hexc.HTTPNotFound(_('Content has not been processed.'))
        return render_job


@view_config(context=IRenderableContentPackage)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               name=VIEW_RENDER_JOBS,
               permission=nauth.ACT_CONTENT_EDIT)
class RenderJobsView(AbstractAuthenticatedView):
    """
    Fetch all render jobs for the contextual `IContentPackage`
    """

    def __call__(self):
        meta = IContentPackageRenderMetadata(self.context, None)
        if meta is None:
            logger.warn('No meta found for content package (%s)',
                        self.context.ntiid)
            raise hexc.HTTPNotFound(_('Content has not been processed.'))

        result = LocatedExternalDict()
        result[NTIID] = self.context.ntiid
        result[ITEMS] = items = []
        for job in sorted(meta.render_jobs):
            items.append(job)
        return result
