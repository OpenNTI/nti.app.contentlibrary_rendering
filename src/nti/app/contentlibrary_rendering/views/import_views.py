#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import shutil
import tempfile

from zope import component

from zope.component.hooks import getSite
from zope.component.hooks import site as current_site

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import get_all_sources

from nti.app.contentlibrary.views import LibraryPathAdapter

from nti.app.contentlibrary.views.sync_views import _AbstractSyncAllLibrariesView

from nti.app.contentlibrary_rendering.views import MessageFactory as _

from nti.app.externalization.error import raise_json_error

from nti.cabinet.filer import transfer_to_native_file

from nti.common.string import is_true

from nti.contentlibrary.interfaces import IContentPackageLibrary

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

from nti.site.hostpolicy import get_host_site

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT


@view_config(name="ImportRenderedContent")
@view_config(name="ImportRenderedContents")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=LibraryPathAdapter,
               permission=nauth.ACT_SYNC_LIBRARY)
class ImportRenderedContentView(_AbstractSyncAllLibrariesView):

    def _get_site(self, request_site, package):
        if request_site:
            site_name = request_site
        elif package is not None:
            site_name = get_content_package_site(package)
        else:
            site_name = getSite().__name__
        return site_name

    def _process_source(self, content, name, path, obfuscate=True):
        # seek to 0 in case of a retry
        if hasattr(content, 'seek'):
            content.seek(0)
        # transfer to local directory
        transfer_to_native_file(content, path)
        source = process_source(path)
        if obfuscate:
            source = obfuscate_source(source)
        return source

    def _do_call(self):
        data = self.readInput()
        request_site = data.get('site')
        obfuscate = data.get('obfuscate')
        if obfuscate is None: # default to True
            obfuscate = True 
        else:
            obfuscate = is_true(obfuscate)
        request_library = component.getUtility(IContentPackageLibrary)
        # preapre results
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
                source = self._process_source(source, name, path, obfuscate)
                # 2. get package ntiid
                ntiid = get_rendered_package_ntiid(source)
                # 3. get existing package if any
                package = request_library.get(ntiid)
                # 4. get update site
                site_name = self._get_site(request_site, package)
                if not site_name:
                    raise_json_error(self.request,
                                     hexc.HTTPUnprocessableEntity,
                                     {
                                         'message': _(u"Cannot update a global package."),
                                     },
                                     None)
                with current_site(get_host_site(site_name)):
                    # 5. remove content
                    if package is not None:
                        remove_content(package)
                    library = component.getUtility(IContentPackageLibrary)
                    # 6. move content to library
                    move_content(library, source)
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
