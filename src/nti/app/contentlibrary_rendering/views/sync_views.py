#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from requests.structures import CaseInsensitiveDict

from zope import interface

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import get_all_sources
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.contentlibrary.views import LibraryPathAdapter

from nti.app.contentlibrary_rendering import VIEW_LIB_JOB_ERROR
from nti.app.contentlibrary_rendering import VIEW_LIB_JOB_STATUS

from nti.app.contentlibrary_rendering.views import MessageFactory as _

from nti.app.externalization.error import raise_json_error

from nti.app.renderers.interfaces import INoHrefInResponse

from nti.cabinet import NamedSource

from nti.contentlibrary_rendering import NTI_PROVIDER

from nti.contentlibrary_rendering._archive import get_job_error
from nti.contentlibrary_rendering._archive import get_job_status
from nti.contentlibrary_rendering._archive import render_archive

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT


@view_config(name="RenderContentSource")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=LibraryPathAdapter,
               permission=nauth.ACT_SYNC_LIBRARY)
class RenderContentSourceView(AbstractAuthenticatedView,
                              ModeledContentUploadRequestUtilsMixin):

    MAX_SOURCE_SIZE = 524288000  # 500mb

    def readInput(self, value=None):
        result = super(RenderContentSourceView, self).readInput(value)
        return CaseInsensitiveDict(result)

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result[ITEMS] = items = {}
        # read params
        data = self.readInput()
        creator = self.remoteUser.username
        provider = data.get('provider') or NTI_PROVIDER
        site = data.get('site') or data.get('site_name')
        # process sources
        sources = get_all_sources(self.request)
        for name, source in sources.items():
            if source.length >= self.MAX_SOURCE_SIZE:
                raise_json_error(
                    self.request,
                    hexc.HTTPUnprocessableEntity,
                    {
                        'message': _(u"Max file size exceeded"),
                        'code': u'MaxFileSizeExceeded',
                    },
                    None)
            filename = getattr(source, 'filename', None) or name
            # save source
            target = NamedSource(filename, source.data)
            # schedule
            job = render_archive(target,
                                 creator,
                                 site=site,
                                 provider=provider)
            items[filename] = job
        result[ITEM_COUNT] = result[TOTAL] = len(items)
        return result


@view_config(name=VIEW_LIB_JOB_STATUS)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               context=LibraryPathAdapter,
               permission=nauth.ACT_SYNC_LIBRARY)
class LibraryJobStatusView(AbstractAuthenticatedView):

    def __call__(self):
        data = CaseInsensitiveDict(self.request.params)
        job_id = data.get('jobId') or data.get('job_id')
        if not job_id:
            raise_json_error(
                self.request,
                hexc.HTTPUnprocessableEntity,
                {
                    'message': _(u"Must provide a job identifier"),
                    'field': u'jobId',
                    'code': u'InvalidJobID',
                },
                None)
        status = get_job_status(job_id)
        if status is None:
            raise hexc.HTTPNotFound()
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result['jobId'] = job_id
        result['status'] = status
        interface.alsoProvides(result, INoHrefInResponse)
        return result


@view_config(name=VIEW_LIB_JOB_ERROR)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               context=LibraryPathAdapter,
               permission=nauth.ACT_SYNC_LIBRARY)
class LibraryJobErrorView(AbstractAuthenticatedView):

    def __call__(self):
        data = CaseInsensitiveDict(self.request.params)
        job_id = data.get('jobId') or data.get('job_id')
        if not job_id:
            raise_json_error(
                self.request,
                hexc.HTTPUnprocessableEntity,
                {
                    'message': _(u"Must provide a job identifier"),
                    'field': u'jobId',
                    'code': u'InvalidJobID',
                },
                None)
        error = get_job_error(job_id)
        if error is None:
            raise hexc.HTTPNotFound()
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result['jobId'] = job_id
        result.update(error)
        interface.alsoProvides(result, INoHrefInResponse)
        return result
