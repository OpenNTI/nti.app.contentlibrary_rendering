#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import shutil
import tempfile

from zope import component

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import get_all_sources

from nti.app.contentlibrary.views import LibraryPathAdapter

from nti.app.contentlibrary.views.sync_views import _AbstractSyncAllLibrariesView

from nti.app.contentlibrary_rendering.views import MessageFactory as _

from nti.app.externalization.error import raise_json_error

from nti.cabinet.filer import transfer_to_native_file

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contentlibrary_rendering._archive import move_content
from nti.contentlibrary_rendering._archive import process_source
from nti.contentlibrary_rendering._archive import update_library
from nti.contentlibrary_rendering._archive import get_rendered_package_ntiid

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT


@view_config(name="Import")
@view_config(name="ImportContents")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=LibraryPathAdapter,
               permission=nauth.ACT_SYNC_LIBRARY)
class ImportContentPackageContentsView(_AbstractSyncAllLibrariesView):

    def _do_call(self):
        library = component.queryUtility(IContentPackageLibrary)
        if library is None:
            raise_json_error(
                    self.request,
                    hexc.HTTPUnprocessableEntity,
                    {
                        u'message': _("Library not available"),
                        u'code': 'LibraryNotAvailable',
                    },
                    None)

        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result[ITEMS] = items = {}
        tmp_dir = tempfile.mkdtemp()
        try:
            sources = get_all_sources(self.request)
            for name, source in sources.items():
                # 1. save source
                path = os.path.join(tmp_dir, name)
                transfer_to_native_file(source, path)
                source = process_source(path)
                # 2. get package ntiid
                ntiid = get_rendered_package_ntiid(source)
                # 3. move content to library
                move_content(library, source)
                # 4. sync
                synced = update_library(ntiid, source, library=library)
                items[ntiid] = synced
            result[ITEM_COUNT] = result[TOTAL] = len(items)
            return result
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
