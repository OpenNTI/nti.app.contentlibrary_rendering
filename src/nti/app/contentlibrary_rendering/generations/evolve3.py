#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 3

from zope import component
from zope import interface

from zope.component.hooks import site
from zope.component.hooks import setHooks

from zope.intid.interfaces import IIntIds

from nti.contentlibrary import RENDERABLE_CONTENT_MIME_TYPES

from nti.contentlibrary.utils import get_content_packages

from nti.contentlibrary_rendering.index import install_contentrenderjob_catalog

from nti.contentlibrary_rendering.interfaces import IContentPackageRenderMetadata

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.metadata import metadata_queue


def get_renderable_packages():
    packages = get_content_packages(mime_types=RENDERABLE_CONTENT_MIME_TYPES)
    return packages


@interface.implementer(IDataserver)
class MockDataserver(object):

    root = None

    def get_by_oid(self, oid, ignore_creator=False):
        resolver = component.queryUtility(IOIDResolver)
        if resolver is None:
            logger.warn("Using dataserver without a proper ISiteManager.")
        else:
            return resolver.get_object_by_oid(oid, ignore_creator=ignore_creator)
        return None


def add_2_queue(queue, uid):
    try:
        queue.add(uid)
    except TypeError:
        pass


def do_evolve(context):
    setHooks()
    conn = context.connection
    root = conn.root()
    ds_folder = root['nti.dataserver']

    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    with site(ds_folder):
        assert  component.getSiteManager() == ds_folder.getSiteManager(), \
                "Hooks not installed?"

        queue = metadata_queue()

        lsm = ds_folder.getSiteManager()
        intids = lsm.getUtility(IIntIds)

        catalog = install_contentrenderjob_catalog(ds_folder, intids)
        for package in get_renderable_packages():
            meta = IContentPackageRenderMetadata(package, None)
            if not meta:
                continue
            # index metadata
            uid = intids.queryId(meta)
            if uid is not None:
                add_2_queue.add(queue, uid)
            # index jobs
            for job in meta.render_jobs:
                uid = intids.queryId(job)
                if uid is not None:
                    add_2_queue.add(queue, uid)
                    catalog.index_doc(uid, job)

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Dataserver evolution %s done.', generation)


def evolve(context):
    """
    Evolve to gen 3 by indexing render job objects
    """
    do_evolve(context)
