#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.appserver.interfaces import IApplicationSettings

from nti.contentlibrary_rendering.locators import S3Locator as BaseS3Locator
from nti.contentlibrary_rendering.locators import FilesystemLocator as BaseFilesystemLocator

from nti.property.property import Lazy


class FilesystemLocator(BaseFilesystemLocator):

    def _do_locate(self, path, root, context):
        return BaseFilesystemLocator._do_locate(self, path, root, context)

    def _do_remove(self, bucket):
        BaseFilesystemLocator._do_remove(self, bucket)


class S3Locator(BaseS3Locator):

    @Lazy
    def settings(self):
        return component.queryUtility(IApplicationSettings) or {}

    def _do_locate(self, path, root, context, debug=True):
        return BaseS3Locator._do_locate(self, path, root, context, debug=debug)

    def _do_remove(self, bucket, debug=True):
        return BaseS3Locator._do_remove(self, bucket, debug=debug)
