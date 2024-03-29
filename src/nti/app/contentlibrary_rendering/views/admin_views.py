#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from requests.structures import CaseInsensitiveDict

from zope import component
from zope import lifecycleevent

from zope.cachedescriptors.property import Lazy

from zope.component.hooks import site as current_site

from zope.intid.interfaces import IIntIds

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.app.contentlibrary.views import LibraryPathAdapter

from nti.app.contentlibrary_rendering.utils import get_failed_render_jobs
from nti.app.contentlibrary_rendering.utils import get_pending_render_jobs

from nti.app.contentlibrary_rendering.views import perform_content_validation
from nti.app.contentlibrary_rendering.views import MessageFactory as _

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.externalization.error import raise_json_error

from nti.contentlibrary.interfaces import IContentRendered
from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IRenderableContentPackage

from nti.contentlibrary_rendering import QUEUE_NAMES

from nti.contentlibrary_rendering.interfaces import IContentPackageRenderMetadata

from nti.contentlibrary_rendering.index import get_contentrenderjob_catalog

from nti.contentlibrary_rendering.processing import get_job_queue

from nti.contentlibrary_rendering.utils import render_package

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.metadata import queue_add
            
from nti.publishing.interfaces import IPublishable

from nti.site.hostpolicy import get_all_host_sites

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

logger = __import__('logging').getLogger(__name__)


def get_renderable_packages():
    library = component.queryUtility(IContentPackageLibrary)
    if library is not None:
        for package in list(library.contentPackages):
            if IRenderableContentPackage.providedBy(package):
                yield package


def is_published(package):
    return not IPublishable.providedBy(package) \
        or package.is_published()


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
        packages = list(get_renderable_packages())
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
        for package in get_renderable_packages():
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
               name="PublishAllRenderableContentPackages",
               permission=nauth.ACT_NTI_ADMIN)
class PublishAllRenderableContentPackagesView(AbstractAuthenticatedView):

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result[ITEMS] = items = {}
        for package in get_renderable_packages():
            if not is_published(package):
                package.publish()
                lifecycleevent.modified(package)
                items[package.ntiid] = package.title
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(context=LibraryPathAdapter)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               name="UnpublishAllRenderableContentPackages",
               permission=nauth.ACT_NTI_ADMIN)
class UnpublishAllRenderableContentPackagesView(AbstractAuthenticatedView):

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result[ITEMS] = items = {}
        for package in get_renderable_packages():
            if is_published(package):
                package.unpublish()
                lifecycleevent.modified(package)
                items[package.ntiid] = package.title
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
        result[ITEMS] = items = {}
        library = component.getUtility(IContentPackageLibrary)
        for package in get_renderable_packages():
            logger.info('Removing renderable package (%s)', package.ntiid)
            items[package.ntiid] = package.title
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

    def _is_invalid_renderable(self, package):
        return (
            (   not IRenderableContentPackage.providedBy(package)
             and package.root.name.startswith('_authored_'))
         or (    IRenderableContentPackage.providedBy(package)
             and IContentRendered.providedBy(package)
             and package.root is None)
        )

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result[ITEMS] = items = {}
        library = component.getUtility(IContentPackageLibrary)
        for package in list(library.contentPackages):
            if self._is_invalid_renderable(package):
                logger.info('Removing invalid renderable package (%s)',
                            package.ntiid)
                items[package.ntiid] = package.title
                library.remove(package, event=True)
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(name="ClearJobs")
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
        # pylint: disable=too-many-function-args
        meta.clear()  # clear container
        return hexc.HTTPNoContent()


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
                # pylint: disable=too-many-function-args
                meta.clear()
        return hexc.HTTPNoContent()


@view_config(name="GetAllPendingRenderJobs")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               context=LibraryPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class GetAllPendingRenderJobsView(AbstractAuthenticatedView):

    def readInput(self):
        return CaseInsensitiveDict(self.request.params)

    def __call__(self):
        data = self.readInput()
        packages = data.get('ntiid') or data.get('package')
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        items = result[ITEMS] = get_pending_render_jobs(packages)
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(name="RemoveAllPendingRenderJobs")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=LibraryPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class RemoveAllPendingRenderJobsView(AbstractAuthenticatedView,
                                     ModeledContentUploadRequestUtilsMixin):

    def readInput(self, value=None):
        result = CaseInsensitiveDict()
        if self.request.body:
            data = super(RemoveAllPendingRenderJobsView, self).readInput(value)
            result.update(data)
        return result

    def __call__(self):
        data = self.readInput()
        packages = data.get('ntiid') or data.get('package')
        items = get_pending_render_jobs(packages)
        for job in items or ():
            meta = IContentPackageRenderMetadata(job)
            # pylint: disable=too-many-function-args
            meta.removeJob(job)
        return hexc.HTTPNoContent()


@view_config(name="GetAllFailedRenderJobs")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               context=LibraryPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class GetAllFailedRenderJobsView(AbstractAuthenticatedView):

    def readInput(self):
        return CaseInsensitiveDict(self.request.params)

    def __call__(self):
        data = self.readInput()
        packages = data.get('ntiid') or data.get('package')
        items = get_failed_render_jobs(packages)
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        items = result[ITEMS] = items
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


@view_config(name="RemoveAllFailedRenderJobs")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=LibraryPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class RemoveAllFailedRenderJobsView(AbstractAuthenticatedView,
                                    ModeledContentUploadRequestUtilsMixin):

    def readInput(self, value=None):
        result = CaseInsensitiveDict()
        if self.request.body:
            data = super(RemoveAllFailedRenderJobsView, self).readInput(value)
            result.update(data)
        return result

    def __call__(self):
        data = self.readInput()
        packages = data.get('ntiid') or data.get('package')
        items = get_failed_render_jobs(packages)
        for job in items or ():
            meta = IContentPackageRenderMetadata(job)
            # pylint: disable=too-many-function-args
            meta.removeJob(job)
        return hexc.HTTPNoContent()


@view_config(context=LibraryPathAdapter)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               name="RebuildContentRenderingJobCatalog",
               permission=nauth.ACT_NTI_ADMIN)
class RebuildContentRenderingJobCatalogView(AbstractAuthenticatedView):

    def __call__(self):
        intids = component.getUtility(IIntIds)
        # clear indexes
        catalog = get_contentrenderjob_catalog()
        for index in list(catalog.values()):
            index.clear()
        # reindex
        seen = set()
        for host_site in get_all_host_sites():  # check all sites
            with current_site(host_site):
                library = component.queryUtility(IContentPackageLibrary)
                packages = library.contentPackages if library else ()
                for package in list(packages):
                    if not IRenderableContentPackage.providedBy(package):
                        continue
                    meta = IContentPackageRenderMetadata(package)
                    for job in list(meta.render_jobs):
                        doc_id = intids.queryId(job)
                        if doc_id is None or doc_id in seen:
                            continue
                        seen.add(doc_id)
                        queue_add(job)
                        catalog.index_doc(doc_id, job)
        result = LocatedExternalDict()
        result[ITEM_COUNT] = result[TOTAL] = len(seen)
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


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             request_method='POST',
             context=LibraryPathAdapter,
             name='MarkOrphanedJobsFailed',
             permission=nauth.ACT_NTI_ADMIN)
class MarkOrphanedJobsFailedView(AbstractAuthenticatedView):
    """
    Mark pending jobs as failed if they have been running for
    more than a specific time (one hour by default).
    """
    @Lazy
    def _params(self):
        return CaseInsensitiveDict(self.request.params)

    @Lazy
    def max_rendering_duration(self):
        duration = self._params.get('max_rendering_duration', 60*60)
        try:
            duration = float(duration)
        except ValueError:
            duration = None

        if duration is None or duration <= 0:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"max_rendering_duration should be positive number."),
                             },
                             None)
        return duration

    def __call__(self):
        max_duration = self.max_rendering_duration
        now = time.time()

        seen = set()
        for host_site in get_all_host_sites():
            with current_site(host_site):
                jobs = get_pending_render_jobs(sites=(host_site.__name__,))
                for job in jobs or ():
                    if now - job.createdTime < max_duration or job in seen:
                        continue

                    seen.add(job)
                    job.update_to_failed_state("Rendering time takes too long (equals to or more than {} seconds).".format(max_duration))

        result = LocatedExternalDict()
        result[ITEM_COUNT] = result[TOTAL] = len(seen)
        return result
