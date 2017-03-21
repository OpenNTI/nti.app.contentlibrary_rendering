#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import component

from zope.intid.interfaces import IIntIds

from nti.contentlibrary_rendering.index import IX_SITE
from nti.contentlibrary_rendering.index import IX_STATE
from nti.contentlibrary_rendering.index import IX_PACKAGE_NTIID
from nti.contentlibrary_rendering.index import get_contentrenderjob_catalog

from nti.contentlibrary_rendering.interfaces import PENDING
from nti.contentlibrary_rendering.interfaces import IContentPackageRenderJob

from nti.site.site import get_component_hierarchy_names


def get_pending_render_jobs(sites=(), packages=()):
    if not sites:
        sites = get_component_hierarchy_names()
    elif isinstance(sites, six.string_types):
        sites = sites.split()

    if isinstance(packages, six.string_types):
        packages = packages.split()

    intids = component.getUtility(IIntIds)
    catalog = get_contentrenderjob_catalog()
    if catalog is None:  # tests
        return ()

    query = {
        IX_SITE: {'any_of': sites},
        IX_STATE: {'any_of': (PENDING,)}
    }
    if packages:
        query[IX_PACKAGE_NTIID] = {'any_of': packages}

    result = list()
    for doc_id in catalog.apply(query) or ():
        context = intids.queryObject(doc_id)
        if      IContentPackageRenderJob.providedBy(context) \
            and context.is_pending():
            result.append(context)
    return result
