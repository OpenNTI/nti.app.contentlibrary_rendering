#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 5

from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotations

from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from nti.contentlibrary import RENDERABLE_CONTENT_MIME_TYPES

from nti.contentlibrary.utils import get_content_packages
from nti.contentlibrary.utils import get_content_package_site

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.recorder.interfaces import TRX_RECORD_HISTORY_KEY

from nti.site.hostpolicy import get_host_site


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


def remove_annotation(package):
    annotes = IAnnotations(package, None)
    try:
        meta = annotes.data.pop(TRX_RECORD_HISTORY_KEY, None)
        meta.clear()
        return True
    except AttributeError:
        pass
    return False


def do_evolve(context):
    setHooks()
    conn = context.connection
    root = conn.root()
    ds_folder = root['nti.dataserver']

    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"

        for package in get_renderable_packages():
            site_name = get_content_package_site(package)
            if site_name is None:
                remove_annotation(package)
            else:
                site = get_host_site(site_name)
                with current_site(site):
                    remove_annotation(package)

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Dataserver evolution %s done.', generation)


def evolve(context):
    """
    Evolve to gen 5 by removing trx history records (away from annotation storage).
    We do not have to retain data in this case (change affects alpha only).
    """
    do_evolve(context)
