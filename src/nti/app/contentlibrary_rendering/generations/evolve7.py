#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=W0212,W0621,W0703

import time
import zlib
import pickle
from io import BytesIO
from datetime import datetime

from zope import component

from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contentlibrary_rendering import QUEUE_NAMES

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


def _reset(redis, name, hash_key):
    keys = redis.pipeline().zremrangebyscore(name, 0, MAX_TIMESTAMP) \
                .hkeys(hash_key).execute()
    if keys and keys[1]:
        redis.hdel(hash_key, *keys[1])


def _all_jobs(redis, hash_key):
    all_jobs = redis.hgetall(hash_key) or {}
    for data in all_jobs.values():
        if data is not None:
            yield _unpickle(data)


def _load_library():
    library = component.queryUtility(IContentPackageLibrary)
    if library is not None:
        library.syncContentPackages()


def do_evolve(context, generation=generation):
    setHooks()
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']

    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"

        _load_library()

        _redis = component.queryUtility(IRedisClient)
        for name in QUEUE_NAMES:
            # process jobs
            hash_key = name + '/hash'
            for job in _all_jobs(_redis, hash_key):
                try:
                    job()
                except Exception:
                    logger.error("Cannot execute library rendering job %s", 
                                 job)
            _reset(_redis, name, hash_key)

            # reset failed
            name += "/failed"
            hash_key = name + '/hash'
            _reset(_redis, name, hash_key)

    logger.info('Library rendering evolution %s done', generation)


def evolve(context):
    """
    Evolve to generation 7 by executing all jobs in the queues 
    """
    do_evolve(context, generation)
