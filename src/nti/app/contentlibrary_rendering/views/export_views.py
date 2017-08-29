#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import time
import shutil
import zipfile
import tempfile

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.contentlibrary.views import LibraryPathAdapter

from nti.app.contentlibrary.views.sync_views import _AbstractSyncAllLibrariesView

from nti.app.contentlibrary_rendering.views import MessageFactory as _

from nti.app.externalization.error import raise_json_error

from nti.common.string import is_true

from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentRendered
from nti.contentlibrary.interfaces import IFilesystemBucket
from nti.contentlibrary.interfaces import IEditableContentPackage

from nti.contentlibrary.utils import export_content_package

from nti.dataserver import authorization as nauth

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.publishing.interfaces import IPublishable


class ExportContentPackageMixin(object):

    def _export_fs(self, root):
        tempdir = tempfile.mkdtemp()
        zip_file = os.path.join(tempdir, "export")
        shutil.make_archive(zip_file, 'zip', root.absolute_path)
        return (zip_file + ".zip", tempdir)

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
        return (zip_file, tempdir)

    def _export_response(self, zip_file, tempdir, response):
        try:
            filename = os.path.split(zip_file)[1]
            response.content_encoding = 'identity'
            response.content_type = 'application/zip; charset=UTF-8'
            content_disposition = 'attachment; filename="%s"' % filename
            response.content_disposition = str(content_disposition)
            response.body_file = open(zip_file, "rb")
            return response
        finally:
            os.remove(zip_file)
            shutil.rmtree(tempdir, True)

    def _export_package(self, package):
        root = getattr(package, 'root', None)
        if IFilesystemBucket.providedBy(root):
            zip_file, tempdir = self._export_fs(root)
        else:  # boto
            key = self.context.key
            zip_file, tempdir = self._export_boto(key)
        return self._export_response(zip_file, tempdir, self.request.response)


@view_config(name="Export")
@view_config(name="ExportContents")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               context=IContentPackage,
               permission=nauth.ACT_NTI_ADMIN)
class ExportContentPackageContentsView(_AbstractSyncAllLibrariesView,
                                       ExportContentPackageMixin):

    def _export_package(self, package):
        if      IPublishable.providedBy(package) \
            and not IContentRendered.providedBy(package):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"Content has not been published.")
                             },
                             None)
        return ExportContentPackageMixin._export_package(self, package)

    def _do_call(self):
        return self._export_package(self.context)


@view_config(name="Export")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               permission=nauth.ACT_CONTENT_EDIT,
               context=IEditableContentPackage)
class ExportEditableContentPackageView(ExportContentPackageContentsView):

    def _export_package(self, package):
        values = self.readInput()
        salt = values.get('salt')
        backup = values.get('backup')
        published = package.is_published()
        if not published or backup is not None or salt is not None:
            backup = is_true(backup)
            salt = salt or str(time.time())
            return export_content_package(self.context, backup, salt)
        return super(ExportEditableContentPackageView, self)._export_package(package)


@view_config(name="ExportRenderedContent")
@view_config(name="ExportRenderedContents")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='GET',
               context=LibraryPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class ExportRenderedContentView(ExportContentPackageContentsView):

    def _do_call(self):
        data = self.readInput()
        ntiid = data.get('ntiid') or data.get('package')
        if not ntiid:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"Invalid package NTIID."),
                                 'field': 'ntiid'
                             },
                             None)
        package = find_object_with_ntiid(ntiid)
        if not IContentPackage.providedBy(package):
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': _(u"Object is not a content package."),
                             },
                             None)
        return self._export_package(package)
