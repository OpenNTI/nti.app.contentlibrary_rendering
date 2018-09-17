#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time
import zlib
import pickle
from io import BytesIO
from datetime import datetime

from zope import component
from zope import interface

from zope.component.hooks import getSite
from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contentlibrary_rendering import QUEUE_NAMES

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver
from nti.dataserver.interfaces import IRedisClient

MAX_TIMESTAMP = time.mktime(datetime.max.timetuple())

generation = 7

logger = __import__('logging').getLogger(__name__)


def _unpickle(data):
    data = zlib.decompress(data)
    bio = BytesIO(data)
    bio.seek(0)
    result = pickle.load(bio)
    return result

def _reset_failed(redis_client, name, hash_key):
    keys = redis_client.pipeline().delete(name) \
                       .hkeys(hash_key).execute()
    if keys and keys[1]:
        redis_client.hdel(hash_key, *keys[1])
        return keys[1]
    return ()


def _reset_queue(redis_client, name, hash_key):
    keys = redis_client.pipeline().zremrangebyscore(name, 0, MAX_TIMESTAMP) \
                       .hkeys(hash_key).execute()
    if keys and keys[1]:
        redis_client.hdel(hash_key, *keys[1])


def _all_jobs(redis_client, hash_key):
    all_jobs = redis_client.hgetall(hash_key) or {}
    for data in all_jobs.values():
        if data is not None:
            yield _unpickle(data)


def _load_library():
    library = component.queryUtility(IContentPackageLibrary)
    if library is not None:
        library.syncContentPackages()


@interface.implementer(IDataserver)
class MockDataserver(object):

    root = None
    root_folder = None

    def get_by_oid(self, oid, ignore_creator=False):
        resolver = component.queryUtility(IOIDResolver)
        if resolver is None:
            logger.warning("Using dataserver without a proper ISiteManager.")
        else:
            return resolver.get_object_by_oid(oid, ignore_creator=ignore_creator)
        return None


def do_evolve(context, generation=generation):  # pylint: disable=redefined-outer-name
    setHooks()
    conn = context.connection

    ds_folder = conn.root()['nti.dataserver']
    redis_client = component.getUtility(IRedisClient)

    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"

        # set root folder
        mock_ds.root_folder = getSite().__parent__

        # always load library
        _load_library()

        # process queue/jobs
        for name in QUEUE_NAMES:
            # process jobs
            hash_key = name + '/hash'
            for job in _all_jobs(redis_client, hash_key):
                try:
                    job()
                except Exception:  # pylint: disable=broad-except
                    logger.error("Cannot execute library rendering job %s",
                                 job)
            _reset_queue(redis_client, name, hash_key)

            # reset failed
            name += "/failed"
            hash_key = name + '/hash'
            _reset_failed(redis_client, name, hash_key)

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('Library rendering evolution %s done', generation)


def evolve(context):
    """
    Evolve to generation 7 by executing all jobs in the queues 
    """
    do_evolve(context, generation)
