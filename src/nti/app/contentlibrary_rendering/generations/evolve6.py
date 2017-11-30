#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=W0212,W0621,W0703

generation = 6

from zope import component
from zope import interface

from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from nti.contentlibrary_rendering import CONTENT_UNITS_QUEUE

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver
from nti.dataserver.interfaces import IRedisClient

logger = __import__('logging').getLogger(__name__)


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


def remove_queue(name):
    redis = component.getUtility(IRedisClient)
    try:
        redis.zremrangebyrank(name, 0, -1)
        redis.delete(name)
    except Exception:
        pass


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

        failed_queue = CONTENT_UNITS_QUEUE + "/failed"
        remove_queue(failed_queue)

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Library rendering evolution %s done.', generation)


def evolve(context):
    """
    Evolve to gen 6 by removing the failed rendering queue
    """
    do_evolve(context)
