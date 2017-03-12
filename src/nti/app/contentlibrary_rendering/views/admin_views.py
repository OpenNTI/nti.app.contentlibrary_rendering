#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import BatchingUtilsMixin

from nti.app.contentlibrary.views import LibraryPathAdapter

from nti.app.contentlibrary_rendering.views import perform_content_validation

from nti.contentlibrary import RENDERABLE_CONTENT_MIME_TYPES

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contentlibrary.utils import get_content_packages

from nti.contentlibrary_rendering import QUEUE_NAMES

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
        result['TotalItemCount'] = len(packages)
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
            items[package.ntiid] = package
            library.remove(package, event=True, unregister=True)
        result[TOTAL] = result[ITEM_COUNT] = len(items)
        return result


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
