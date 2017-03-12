#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 2

from zope import component
from zope import interface

from zope.component.hooks import site
from zope.component.hooks import setHooks

from zope.intid.interfaces import IIntIds

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contentlibrary_rendering.interfaces import IContentPackageRenderJob
from nti.contentlibrary_rendering.interfaces import IContentPackageRenderMetadata

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.dataserver.metadata_index import IX_MIMETYPE

from nti.intid.common import removeIntId

from nti.metadata import dataserver_metadata_catalog

from nti.traversal.traversal import find_interface


@interface.implementer(IDataserver)
class MockDataserver(object):

    root = None

    def get_by_oid(self, oid, ignore_creator=False):
        resolver = component.queryUtility(IOIDResolver)
        if resolver is None:
            logger.warn("sing dataserver without a proper ISiteManager.")
        else:
            return resolver.get_object_by_oid(oid, ignore_creator=ignore_creator)
        return None


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

        lsm = ds_folder.getSiteManager()
        intids = lsm.getUtility(IIntIds)

        catalog = dataserver_metadata_catalog()
        mimeType = u'application/vnd.nextthought.content.packagerenderjob'
        query = {
            IX_MIMETYPE: {'any_of': (mimeType,)}
        }
        metas = set()
        for uid in catalog.apply(query) or ():
            item = intids.queryObject(uid)
            if not IContentPackageRenderJob.providedBy(item):
                continue
            library = find_interface(item,
                                     IContentPackageLibrary,
                                     strict=False)
            if library is None:
                removeIntId(item) # unindex
                meta = find_interface(item,
                                      IContentPackageRenderMetadata,
                                      strict=False)
                if meta is not None:
                    metas.add(meta)

        for meta in metas:
            meta.clear()  # clear jobs
            uid = intids.queryId(meta)
            if uid is not None:
                removeIntId(meta)

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Dataserver evolution %s done.', generation)


def evolve(context):
    """
    Evolve to gen 2 by removing possible leaks
    """
    do_evolve(context)
