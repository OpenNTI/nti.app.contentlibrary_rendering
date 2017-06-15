#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from requests.structures import CaseInsensitiveDict

from zope import component

from zope.component.hooks import site as current_site

from zope.intid.interfaces import IIntIds

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.app.contentlibrary.views import LibraryPathAdapter

from nti.app.contentlibrary_rendering.views import MessageFactory as _

from nti.app.contentlibrary_rendering.utils import get_failed_render_jobs
from nti.app.contentlibrary_rendering.utils import get_pending_render_jobs

from nti.app.contentlibrary_rendering.views import perform_content_validation

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IRenderableContentPackage

from nti.contentlibrary_rendering import QUEUE_NAMES

from nti.contentlibrary_rendering.interfaces import IContentPackageRenderMetadata

from nti.contentlibrary_rendering.index import get_contentrenderjob_catalog
from nti.contentlibrary_rendering.index import create_contentrenderjob_catalog

from nti.contentlibrary_rendering.processing import get_job_queue

from nti.contentlibrary_rendering.utils import render_package

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.site.hostpolicy import get_all_host_sites

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT


def get_renderable_packages():
    library = component.queryUtility(IContentPackageLibrary)
    if library is not None:
        for package in list(library.contentPackages):
            if IRenderableContentPackage.providedBy(package):
                yield package


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
               name="RemoveAllRenderableContentPackages",
               permission=nauth.ACT_NTI_ADMIN)
class RemoveAllRenderableContentPackagesView(AbstractAuthenticatedView):

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        library = component.getUtility(IContentPackageLibrary)
        result[ITEMS] = items = {}
        for package in get_renderable_packages():
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
        return package.root is None \
            or package.root.name.startswith('_authored_')

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        library = component.getUtility(IContentPackageLibrary)
        result[ITEMS] = items = {}
        for package in list(library.contentPackages):
            if      not IRenderableContentPackage.providedBy(package) \
                and self._is_renderable_path(package):
                logger.info('Removing invalid renderable package (%s) (%s)',
                            package.ntiid,
                            package.root.name)
                items[package.ntiid] = package
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


@view_config(name="RemoveAllPendingRenderJobs")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=LibraryPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class RemoveAllPendingRenderJobsView(GetAllPendingRenderJobsView):

    def __call__(self):
        result = super(RemoveAllPendingRenderJobsView, self).__call__()
        for job in result[ITEMS]:
            meta = IContentPackageRenderMetadata(job)
            meta.removeJob(job)
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


@view_config(name="RemoveAllFailedRenderJobs")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=LibraryPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class RemoveAllFailedRenderJobsView(GetAllFailedRenderJobsView):

    def __call__(self):
        result = super(RemoveAllFailedRenderJobsView, self).__call__()
        for job in result[ITEMS]:
            meta = IContentPackageRenderMetadata(job)
            meta.removeJob(job)
        return result


@view_config(context=LibraryPathAdapter)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               name="RebuildContentRenderingJobCatalog",
               permission=nauth.ACT_NTI_ADMIN)
class RebuildContentRenderingJobCatalogView(AbstractAuthenticatedView):

    def __call__(self):
        intids = component.getUtility(IIntIds)
        # remove indexes
        catalog = get_contentrenderjob_catalog()
        for name, index in list(catalog.items()):
            intids.unregister(index)
            del catalog[name]
        # recreate indexes
        catalog = create_contentrenderjob_catalog(catalog=catalog,
                                                  family=intids.family)
        for index in catalog.values():
            intids.register(index)
        # reindex
        seen = set()
        for host_site in get_all_host_sites():  # check all sites
            logger.info("Processing site %s", host_site.__name__)
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
