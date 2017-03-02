#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope import component

from nti.app.contentlibrary_rendering import LOCK_TIMEOUT
from nti.app.contentlibrary_rendering import SYNC_LOCK_NAME

from nti.appserver.interfaces import IApplicationSettings

from nti.contentlibrary_rendering.locators import S3Locator as BaseS3Locator
from nti.contentlibrary_rendering.locators import FilesystemLocator as BaseFilesystemLocator

from nti.dataserver.interfaces import IRedisClient

from nti.property.property import Lazy


def redis(self):
    return component.getUtility(IRedisClient)


def acquire(blocking=True):
    lock = redis.lock(SYNC_LOCK_NAME, LOCK_TIMEOUT)
    try:
        acquired = lock.acquire(blocking=blocking)
        if acquired:
            return lock
    except Exception:
        logger.exception("Cannot get a redis lock")
    return None


def release(lock=None):
    try:
        if lock is not None:
            lock.release()
    except Exception:
        logger.exception("Error while releasing Sync lock")


def needs_lock(func):
    def decorator(func):
        def wrapper(self, *args, **kw):
            lock = acquire()
            try:
                return func(self, *args, **kw)
            finally:
                release(lock)
        return wrapper
    return decorator


class FilesystemLocator(BaseFilesystemLocator):

    @needs_lock
    def _do_locate(self, path, root, context):
        return BaseFilesystemLocator._do_locate(self, path, root, context)

    @needs_lock
    def _do_remove(self, bucket):
        BaseFilesystemLocator._do_remove(self, bucket)


class S3Locator(BaseS3Locator):

    @Lazy
    def settings(self):
        return component.queryUtility(IApplicationSettings) or {}

    @needs_lock
    def _do_locate(self, path, root, context, debug=True):
        return BaseS3Locator._do_locate(self, path, root, context, debug=debug)

    @needs_lock
    def _do_remove(self, bucket, debug=True):
        return BaseS3Locator._do_remove(self, bucket, debug=debug)
