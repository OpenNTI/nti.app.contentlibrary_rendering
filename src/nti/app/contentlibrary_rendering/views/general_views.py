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

from nti.app.contentlibrary_rendering.views import MessageFactory as _

from nti.contentlibrary.interfaces import IRenderableContentPackage

from nti.contentlibrary_rendering.interfaces import IContentPackageRenderMetadata

from nti.contentlibrary_rendering.utils import render_package

from nti.dataserver import authorization as nauth


@view_config(context=IRenderableContentPackage)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               name="render",
               permission=nauth.ACT_CONTENT_EDIT)
class RenderContentPackageView(AbstractAuthenticatedView):

    def __call__(self):
        job = render_package(self.context, self.remoteUser)
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
        job_id = params.get('JobId') or params.get('job') or params.get('job_id')
        meta = IContentPackageRenderMetadata(self.context, None)
        if meta is None:
            logger.warn(
                'No meta found for content package (%s)',
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
