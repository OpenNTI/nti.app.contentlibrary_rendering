#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IRenderableContentPackage

from nti.contentlibrary_rendering.interfaces import IContentPackageRenderMetadata

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ISystemUserPrincipal

from nti.dataserver.metadata.predicates import BasePrincipalObjects

logger = __import__('logging').getLogger(__name__)


class _RenderingObjectsMixin(BasePrincipalObjects):  # pylint: disable=abstract-method

    @property
    def library(self):
        return component.queryUtility(IContentPackageLibrary)

    @property
    def metas(self):
        library = self.library
        if library is not None:
            for package in library.contentPackages:
                if not IRenderableContentPackage.providedBy(package):
                    continue
                meta = IContentPackageRenderMetadata(package, None)
                if meta:
                    yield meta


@component.adapter(ISystemUserPrincipal)
class _SystemContentRenderMetadata(_RenderingObjectsMixin):

    def iter_objects(self):
        return self.metas


class _ContentPackageRenderJobs(_RenderingObjectsMixin):

    def _predicate(self, unused_obj):
        return False

    def iter_objects(self):
        result = []
        for meta in self.metas:
            for job in meta.render_jobs:
                if self._predicate(job):
                    result.append(job)
        return result


@component.adapter(ISystemUserPrincipal)
class _SystemContentPackageRenderJobs(_ContentPackageRenderJobs):

    def _predicate(self, job):
        return self.is_system_username(self.creator(job))


@component.adapter(IUser)
class _UserContentPackageRenderJobs(_ContentPackageRenderJobs):

    def _predicate(self, job):
        return self.creator(job) == self.username
