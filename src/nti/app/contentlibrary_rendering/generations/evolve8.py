#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IEditableContentPackage

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.site.hostpolicy import get_all_host_sites

generation = 8

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IDataserver)
class MockDataserver(object):

    root = None

    def get_by_oid(self, oid, ignore_creator=False):
        resolver = component.queryUtility(IOIDResolver)
        if resolver is None:
            logger.warning("Using dataserver without a proper ISiteManager.")
        else:
            return resolver.get_object_by_oid(oid, ignore_creator=ignore_creator)
        return None


def _process_site(current, seen):
    with current_site(current):
        library = component.queryUtility(IContentPackageLibrary)
        if library is not None:
            for package in library.contentPackages or ():
                if package.ntiid in seen:
                    continue
                seen.add(package.ntiid)
                if IEditableContentPackage.providedBy(package):
                    try:
                        delattr(package, 'version')
                        logger.info('Removed version attr from %s',
                                    package.ntiid)
                    except AttributeError:
                        pass


def do_evolve(context, generation=generation):  # pylint: disable=redefined-outer-name
    setHooks()
    conn = context.connection
    root = conn.root()
    ds_folder = root['nti.dataserver']

    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    seen = set()
    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"

        # Load library
        library = component.queryUtility(IContentPackageLibrary)
        if library is not None:
            library.syncContentPackages()

        for current in get_all_host_sites():
            _process_site(current, seen)

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Dataserver evolution %s done.', generation)


def evolve(context):
    """
    Evolve to gen 8 by removing the `version` attr from all editable content
    packages. This was caused by exporting/importing editable content packages
    with a `version` attribute.
    """
    do_evolve(context)
