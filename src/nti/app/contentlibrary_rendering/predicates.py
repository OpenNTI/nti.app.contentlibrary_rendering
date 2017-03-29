#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from functools import partial

from zope import component

from zope.intid.interfaces import IIntIds

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IRenderableContentPackage

from nti.contentlibrary_rendering.interfaces import IContentPackageRenderMetadata

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ISystemUserPrincipal

from nti.metadata.predicates import BasePrincipalObjects

from nti.property.property import Lazy

from nti.site.hostpolicy import run_job_in_all_host_sites


class _RenderingObjectsMixin(BasePrincipalObjects):

    @Lazy
    def intids(self):
        return component.getUtility(IIntIds)

    @property
    def library(self):
        return component.queryUtility(IContentPackageLibrary)

    def iter_objects(self):
        result = []
        seen = set()
        run_job_in_all_host_sites(partial(self.iter_items, result, seen))
        return result


@component.adapter(ISystemUserPrincipal)
class _SystemContentRenderMetadata(_RenderingObjectsMixin):

    def iter_items(self, result, seen):
        library = self.library
        if library is None:
            return result
        for package in library.contentPackages:
            if not IRenderableContentPackage.providedBy(package):
                continue
            meta = IContentPackageRenderMetadata(package, None)
            if not meta:
                continue
            doc_id = self.intids.queryId(meta)
            if doc_id is not None and doc_id not in seen:
                seen.add(doc_id)
                result.append(meta)
        return result


@component.adapter(IUser)
class _ContentPackageRenderJobs(_RenderingObjectsMixin):

    def iter_items(self, result, seen):
        user = self.user
        library = self.library
        if library is None:
            return result
        for package in library.contentPackages:
            if not IRenderableContentPackage.providedBy(package):
                continue
            meta = IContentPackageRenderMetadata(package, None)
            if not meta:
                continue
            for job in meta.render_jobs:
                doc_id = self.intids.queryId(job)
                if doc_id is not None and doc_id not in seen:
                    creator = getattr(job.creator, 'username', None)
                    creator = getattr(creator, 'id', creator) or u''
                    seen.add(doc_id)
                    if creator.lower() == user.username.lower():
                        result.append(job)
        return result
