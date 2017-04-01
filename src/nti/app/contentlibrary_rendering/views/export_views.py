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
import zipfile
import tempfile

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.contentlibrary.views import LibraryPathAdapter

from nti.app.contentlibrary.views.sync_views import _AbstractSyncAllLibrariesView

from nti.app.contentlibrary_rendering.views import MessageFactory as _

from nti.coremetadata.interfaces import IPublishable

from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentRendered
from nti.contentlibrary.interfaces import IFilesystemBucket

from nti.dataserver import authorization as nauth

from nti.ntiids.ntiids import find_object_with_ntiid


@view_config(name="Export")
@view_config(name="ExportContents")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               context=IContentPackage,
               permission=nauth.ACT_NTI_ADMIN)
class ExportContentPackageContentsView(_AbstractSyncAllLibrariesView):

    blocking = True

    def _export_fs(self, root):
        tempdir = tempfile.mkdtemp()
        zip_file = os.path.join(tempdir, "export")
        shutil.make_archive(zip_file, 'zip', root.absolute_path)
        return zip_file + ".zip"

    def _export_boto(self, pkg_key):
        tempdir = tempfile.mkdtemp()
        zip_file = os.path.join(tempdir, "export.zip")
        zf = zipfile.ZipFile(zip_file,  "w")
        try:
            bucket = pkg_key.bucket
            for key in bucket.list(prefix=pkg_key.name):
                arcname = key.name[len(pkg_key.name):]
                zf.writestr(arcname, key.get_contents_as_string())
        finally:
            zf.close()
        return zip_file

    def _export_response(self, zip_file, response):
        try:
            filename = os.path.split(zip_file)[1]
            response.content_encoding = b'identity'
            response.content_type = b'application/zip; charset=UTF-8'
            content_disposition = b'attachment; filename="%s"' % filename
            response.content_disposition = str(content_disposition)
            response.body_file = open(zip_file, "rb")
            return response
        finally:
            os.remove(zip_file)

    def _export_package(self, package):
        if      IPublishable.providedBy(self.context) \
            and not IContentRendered.providedBy(self.context):
            raise ValueError(_("Content has not been published."))
        root = getattr(self.context, 'root', None)
        if IFilesystemBucket.providedBy(root):
            zip_file = self._export_fs(root)
        else:  # boto
            key = self.context.key
            zip_file = self._export_boto(key)
        return self._export_response(zip_file, self.request.response)

    def _do_call(self):
        return self._export_package(self.context)


@view_config(name="ExportRenderedContent")
@view_config(name="ExportRenderedContents")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               context=LibraryPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class ExportRenderedContentView(ExportContentPackageContentsView):

    def _do_call(self):
        data = self.readInput()
        ntiid = data.get('ntiid') or data.get('package')
        if not ntiid:
            raise ValueError(_("Invalid package NTIID."))
        package = find_object_with_ntiid(ntiid)
        if not IContentPackage.providedBy(package):
            raise ValueError(_("Object is not a content package."))
        return self._export_package(package)
