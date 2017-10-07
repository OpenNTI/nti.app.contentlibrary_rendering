#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from zope.cachedescriptors.property import Lazy

from nti.appserver.interfaces import IApplicationSettings

from nti.contentlibrary_rendering.locators import S3Locator as BaseS3Locator
from nti.contentlibrary_rendering.locators import FilesystemLocator as BaseFilesystemLocator


class FilesystemLocator(BaseFilesystemLocator):
    pass


class S3Locator(BaseS3Locator):

    @Lazy
    def settings(self):
        return component.queryUtility(IApplicationSettings) or {}
