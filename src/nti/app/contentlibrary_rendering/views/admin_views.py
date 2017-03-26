#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from requests.structures import CaseInsensitiveDict

from zope import component

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import get_all_sources
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import BatchingUtilsMixin
from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.contentlibrary.views import LibraryPathAdapter

from nti.app.contentlibrary_rendering.views import MessageFactory as _

from nti.app.contentlibrary_rendering.utils import get_failed_render_jobs
from nti.app.contentlibrary_rendering.utils import get_pending_render_jobs

from nti.app.contentlibrary_rendering.views import perform_content_validation

from nti.app.externalization.error import raise_json_error

from nti.cabinet import NamedSource

from nti.contentlibrary import RENDERABLE_CONTENT_MIME_TYPES

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IRenderableContentPackage

from nti.contentlibrary.utils import get_content_packages

from nti.contentlibrary_rendering import QUEUE_NAMES

from nti.contentlibrary_rendering.archive import render_archive

from nti.contentlibrary_rendering.interfaces import IContentPackageRenderMetadata

from nti.contentlibrary_rendering.processing import get_job_queue

from nti.contentlibrary_rendering.utils import render_package

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT


def get_renderable_packages():
    packages = get_content_packages(mime_types=RENDERABLE_CONTENT_MIME_TYPES)
    return packages


@view_config(context=LibraryPathAdapter)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               name="RenderableContentPackages",
               permission=nauth.ACT_NTI_ADMIN)
class RenderableContentPackagesView(AbstractAuthenticatedView,
                                    BatchingUtilsMixin):

    _DEFAULT_BATCH_SIZE = 20
    _DEFAULT_BATCH_START = 0

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        packages = get_renderable_packages()
        result[TOTAL] = result['TotalItemCount'] = len(packages)
        self._batch_items_iterable(result, packages)
        result[ITEM_COUNT] = len(result[ITEMS])
        return result


@view_config(context=LibraryPathAdapter)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               name="RenderAllContentPackages",
               permission=nauth.ACT_NTI_ADMIN)
class RenderAllContentPackagesView(AbstractAuthenticatedView):

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result[ITEMS] = items = {}
        packages = get_renderable_packages()
        for package in packages:
            ntiid = package.ntiid
            error = perform_content_validation(package)
            if error is not None:
                data, _ = error
                items[ntiid] = data
            else:
                job = render_package(package, self.remoteUser)
                items[ntiid] = job
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(context=LibraryPathAdapter)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               name="RemoveAllRenderableContentPackages",
               permission=nauth.ACT_NTI_ADMIN)
class RemoveAllRenderableContentPackagesView(AbstractAuthenticatedView):

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        library = component.getUtility(IContentPackageLibrary)
        result[ITEMS] = items = {}
        packages = get_renderable_packages()
        for package in packages:
            logger.info('Removing renderable package (%s)', package.ntiid)
            items[package.ntiid] = package
            library.remove(package, event=True)
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(context=LibraryPathAdapter)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               name="RemoveInvalidRenderableContentPackages",
               permission=nauth.ACT_NTI_ADMIN)
class RemoveInvalidRenderableContentPackagesView(AbstractAuthenticatedView):
    """
    Remove all `authored` content packages that are not
    IRenderableContentPackages.
    """

    def _is_renderable_path(self, package):
        return package.root.name.startswith('_authored_')

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        library = component.getUtility(IContentPackageLibrary)
        result[ITEMS] = items = {}
        for package in library.contentPackages:
            if      not IRenderableContentPackage.providedBy(package) \
                and self._is_renderable_path(package):
                logger.info('Removing invalid renderable package (%s) (%s)',
                            package.ntiid,
                            package.root.name)
                items[package.ntiid] = package
                library.remove(package, event=True)
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(name="clear_jobs")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=IRenderableContentPackage,
               permission=nauth.ACT_NTI_ADMIN)
class RemoveContentPackageRenderJobsView(AbstractAuthenticatedView):

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        meta = IContentPackageRenderMetadata(self.context)
        items = result[ITEMS] = list(meta.render_jobs)
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        meta.clear()  # clear container
        return result


@view_config(name="RemoveAllRenderContentJobs")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=LibraryPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class RemoveAllContentPackageRenderJobsView(AbstractAuthenticatedView):

    def __call__(self):
        packages = get_renderable_packages()
        for package in packages:
            meta = IContentPackageRenderMetadata(package, None)
            if meta:
                meta.clear()
        return hexc.HTTPNoContent()


@view_config(name="GetAllPendingRenderJobs")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               context=LibraryPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class GetAllPendingRenderJobsView(AbstractAuthenticatedView):

    def __call__(self):
        data = CaseInsensitiveDict(self.request.params)
        packages = data.get('ntiid') or data.get('package')
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        items = result[ITEMS] = get_pending_render_jobs(packages=packages)
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(name="GetAllFailedRenderJobs")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               context=LibraryPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class GetAllFailedRenderJobsView(AbstractAuthenticatedView):

    def __call__(self):
        data = CaseInsensitiveDict(self.request.params)
        packages = data.get('ntiid') or data.get('package')
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        items = result[ITEMS] = get_failed_render_jobs(packages=packages)
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(name="RenderContentBundle")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=LibraryPathAdapter,
               permission=nauth.ACT_SYNC_LIBRARY)
class RenderContentBundleView(AbstractAuthenticatedView,
                              ModeledContentUploadRequestUtilsMixin):

    MAX_SOURCE_SIZE = 524288000 # 500mb

    def readInput(self, value=None):
        result = super(RenderContentBundleView, self).readInput(value)
        return CaseInsensitiveDict(result)

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result[ITEMS] = items = []
        # read params
        data = self.readInput()
        creator = self.remoteUser.username
        provider = data.get('provider') or 'NTI'
        site = data.get('site') or data.get('site_name')
        # process sources
        sources = get_all_sources(self.request, None)
        for name, source in sources.items():
            if source.length >= self.MAX_SOURCE_SIZE:
                raise_json_error(
                    self.request,
                    hexc.HTTPUnsupportedMediaType,
                    {
                        u'message': _("Max file size exceeded"),
                        u'code': 'MaxFileSizeExceeded',
                    },
                    None)
            filename = getattr(source, 'filename', None) or name
            # save source
            target = NamedSource(filename, source.data)
            # schedule
            status_id = render_archive(target, 
                                       creator, 
                                       site=site,
                                       provider=provider)
            items.append(status_id)
        result[ITEM_COUNT] = result[TOTAL] = len(items)
        return result
    

# queue views


@view_config(name='RenderJobs')
@view_config(name='render_jobs')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               context=LibraryPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class QueueJobsView(AbstractAuthenticatedView):

    def __call__(self):
        total = 0
        result = LocatedExternalDict()
        items = result[ITEMS] = {}
        for name in QUEUE_NAMES:
            queue = get_job_queue(name)
            items[name] = list(queue.keys())  # snapshopt
            total += len(items[name])
        result[TOTAL] = result[ITEM_COUNT] = total
        return result


@view_config(name='EmptyQueues')
@view_config(name='empty_queues')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=LibraryPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class EmptyQueuesView(AbstractAuthenticatedView):

    def __call__(self):
        for name in QUEUE_NAMES:
            queue = get_job_queue(name)
            queue.empty()
        return hexc.HTTPNoContent()
