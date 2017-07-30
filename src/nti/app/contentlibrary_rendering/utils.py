#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import component

from zope.intid.interfaces import IIntIds

from nti.contentlibrary_rendering.index import IX_SITE
from nti.contentlibrary_rendering.index import IX_STATE
from nti.contentlibrary_rendering.index import IX_PACKAGE_NTIID
from nti.contentlibrary_rendering.index import get_contentrenderjob_catalog

from nti.contentlibrary_rendering.interfaces import FAILED
from nti.contentlibrary_rendering.interfaces import PENDING
from nti.contentlibrary_rendering.interfaces import IContentPackageRenderJob

from nti.site.site import get_component_hierarchy_names


def query_render_jobs(packages=(), status=PENDING, sites=()):
    if not sites:
        sites = get_component_hierarchy_names()
    elif isinstance(sites, six.string_types):
        sites = sites.split()

    if isinstance(packages, six.string_types):
        packages = packages.split()

    catalog = get_contentrenderjob_catalog()
    if catalog is None:  # tests
        return ()

    query = {
        IX_SITE: {'any_of': sites},
        IX_STATE: {'any_of': (status,)}
    }
    if packages:
        query[IX_PACKAGE_NTIID] = {'any_of': packages}

    return catalog.apply(query) or ()


def get_pending_render_jobs(packages=(), sites=()):
    result = list()
    intids = component.getUtility(IIntIds)
    for doc_id in query_render_jobs(packages, PENDING, sites):
        context = intids.queryObject(doc_id)
        if      IContentPackageRenderJob.providedBy(context) \
            and context.is_pending():
            result.append(context)
    return result


def get_failed_render_jobs(packages=(), sites=()):
    result = list()
    intids = component.getUtility(IIntIds)
    for doc_id in query_render_jobs(packages, FAILED, sites):
        context = intids.queryObject(doc_id)
        if      IContentPackageRenderJob.providedBy(context) \
            and context.has_failed():
            result.append(context)
    return result
