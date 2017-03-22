#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 4

from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotations

from zope.component.hooks import site
from zope.component.hooks import setHooks

from nti.contentlibrary import RENDERABLE_CONTENT_MIME_TYPES

from nti.contentlibrary.utils import get_content_packages

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver


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

        for package in get_renderable_packages():
            annotes = IAnnotations(package, None)
            try:
                meta = annotes.data.pop( u'nti.contentlibrary.rendering.ContentPackageRenderMetadata',
                                         None )
                meta.clear()
            except AttributeError:
                pass

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Dataserver evolution %s done.', generation)


def evolve(context):
    """
    Evolve to gen 4 by removing render metadata (away from annotation storage).
    We do not have to retain data in this case (change affects alpha only).
    """
    do_evolve(context)
