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

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.contentlibrary.views.sync_views import _AbstractSyncAllLibrariesView

from nti.app.contentlibrary_rendering.views import MessageFactory as _

from nti.app.externalization.error import raise_json_error

from nti.coremetadata.interfaces import IPublishable

from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentRendered 
from nti.contentlibrary.interfaces import IFilesystemBucket 

from nti.dataserver import authorization as nauth


@view_config(context=IContentPackage)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               name="Export",
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

    def _do_call(self):
        if      IPublishable.providedBy(self.context) \
            and not IContentRendered.providedBy(self.context):
            raise_json_error(
                    self.request,
                    hexc.HTTPUnprocessableEntity,
                    {
                        u'message': _("Max file size exceeded"),
                        u'code': 'MaxFileSizeExceeded',
                    },
                    None)
        root = getattr(self.context, 'root', None)
        if IFilesystemBucket.providedBy(root):
            zip_file = self._export_fs(root)
        else: # boto
            key = self.context.key
            zip_file = self._export_boto(key)
        return self._export_response(zip_file, self.request.response)
