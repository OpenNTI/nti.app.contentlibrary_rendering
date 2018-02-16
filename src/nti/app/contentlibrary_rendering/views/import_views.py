#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import zlib
import base64
import shutil
import tempfile

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from zope import component

from zope.component.hooks import getSite
from zope.component.hooks import site as current_site

from nti.app.base.abstract_views import get_all_sources
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.contentlibrary.views import LibraryPathAdapter

from nti.app.contentlibrary.views.sync_views import _AbstractSyncAllLibrariesView

from nti.app.contentlibrary_rendering.views import MessageFactory as _

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.cabinet.filer import transfer_to_native_file

from nti.common.string import is_true

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IRenderableContentPackage

from nti.contentlibrary.mixins import ContentPackageImporterMixin

from nti.contentlibrary.utils import get_content_package_site

from nti.contentlibrary_rendering._archive import move_content
from nti.contentlibrary_rendering._archive import process_source
from nti.contentlibrary_rendering._archive import remove_content
from nti.contentlibrary_rendering._archive import update_library
from nti.contentlibrary_rendering._archive import obfuscate_source
from nti.contentlibrary_rendering._archive import get_rendered_package_ntiid

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import StandardInternalFields

from nti.externalization.proxy import removeAllProxies

from nti.site.hostpolicy import get_host_site

from nti.site.site import get_component_hierarchy_names

ITEMS = StandardExternalFields.ITEMS
NTIID = StandardExternalFields.NTIID
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

INTERNAL_NTIID = StandardInternalFields.NTIID

logger = __import__('logging').getLogger(__name__)


@view_config(name="ImportRenderedContent")
@view_config(name="ImportRenderedContents")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=LibraryPathAdapter,
               permission=nauth.ACT_SYNC_LIBRARY)
class ImportRenderedContentView(_AbstractSyncAllLibrariesView):

    @property
    def current_site_name(self):
        return getSite().__name__

    def _get_site(self, request_site, package):
        if package is not None:
            site_name = get_content_package_site(package)
        elif request_site:
            site_name = request_site
        else:
            site_name = self.current_site_name
        return site_name

    def _process_source(self, content, path, obfuscate=True):
        # seek to 0 in case of a retry
        if hasattr(content, 'seek'):
            content.seek(0)
        # transfer to local directory
        transfer_to_native_file(content, path)
        source = process_source(path)
        if obfuscate:
            source = obfuscate_source(source)
        return source

    def _remove_content(self, ntiid, library, source):
        """
        Remove all content packages on disk with our ntiid (should only be one).
        """
        new_root_name = os.path.basename(source)
        enumeration = library.enumeration
        content_packages = (
            x for x in enumeration.enumerateContentPackages() if x.ntiid == ntiid
        )
        for package in content_packages:
            # Do not delete the package if we're merging.
            if package.root.name != new_root_name:
                remove_content(package)

    def _do_call(self):
        data = self.readInput() or self.request.params
        request_site = data.get('site')
        obfuscate = is_true(data.get('obfuscate'))
        request_library = component.getUtility(IContentPackageLibrary)
        # prepare results
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result[ITEMS] = items = {}
        # process sources
        tmp_dir = tempfile.mkdtemp()
        try:
            sources = get_all_sources(self.request)
            for name, source in sources.items():
                # 1. process source
                name = getattr(source, 'name', None) or name
                path = os.path.join(tmp_dir, name)
                source = self._process_source(source, path, obfuscate)
                # 2. get package ntiid
                ntiid = get_rendered_package_ntiid(source)
                # 3. get existing package if any
                try:
                    package = request_library[ntiid]
                except KeyError:
                    package = None
                logger.info('Importing package (%s) (current_site=%s) (request_site=%s) (obfuscate=%s)',
                            ntiid, self.current_site_name, request_site, obfuscate)
                # 4. get update site, preferring package site
                site_name = self._get_site(request_site, package)
                if not site_name:
                    raise_json_error(self.request,
                                     hexc.HTTPUnprocessableEntity,
                                     {
                                         'message': _(u"Cannot update a global package."),
                                         'code': 'CannotUpdateGlobalPackage'
                                     },
                                     None)
                if site_name not in get_component_hierarchy_names():
                    raise_json_error(self.request,
                                     hexc.HTTPUnprocessableEntity,
                                     {
                                         'message': _(u"Invalid site."),
                                         'code': 'InvalidImportSite'
                                     },
                                     None)
                with current_site(get_host_site(site_name)):
                    # 5. remove content (before moving new content)
                    library = component.getUtility(IContentPackageLibrary)
                    logger.info("Removing package (%s) (site=%s)",
                                ntiid, site_name)
                    self._remove_content(ntiid, library, source)
                    # 6. move content to library
                    bucket = move_content(library, source)
                    logger.info("Content for package %s moved to %s",
                                ntiid, bucket)
                    # 7. sync
                    synced = update_library(ntiid,
                                            source,
                                            move=False,
                                            library=library)
                items[ntiid] = synced
            result[ITEM_COUNT] = result[TOTAL] = len(items)
            return result
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


@view_config(name="Import")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=IRenderableContentPackage,
               permission=nauth.ACT_CONTENT_EDIT)
class ImportEditableContentsView(AbstractAuthenticatedView,
                                 ContentPackageImporterMixin,
                                 ModeledContentUploadRequestUtilsMixin):

    def __call__(self):
        data = self.readInput()
        if not data:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"Invalid input data."),
                             },
                             None)
        # pylint: disable=expression-not-assigned
        [data.pop(x, None) for x in (NTIID, INTERNAL_NTIID)]
        if 'contents' in data:
            decoded = base64.b64decode(data['contents'])
            data['contents'] = zlib.decompress(decoded)
        context = removeAllProxies(self.context)
        ContentPackageImporterMixin.handle_package(self, context,
                                                   data, context)
        return context
