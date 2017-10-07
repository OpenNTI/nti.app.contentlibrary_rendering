#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import greater_than
does_not = is_not

import shutil
import zipfile
import tempfile

from nti.cabinet.mixins import get_file_size

from nti.contentlibrary.zodb import RenderableContentPackage

from nti.externalization.externalization import to_external_object

from nti.app.contentlibrary.tests import PersistentApplicationTestLayer

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS


class TestExportViews(ApplicationLayerTest):

    layer = PersistentApplicationTestLayer

    default_origin = 'http://janux.ou.edu'

    ntiid = 'tag:nextthought.com,2011-10:OU-HTML-CS1323_F_2015_Intro_to_Computer_Programming.introduction_to_computer_programming'

    def _test_export(self, res):
        tmp_dir = tempfile.mkdtemp(dir="/tmp")
        try:
            path = tmp_dir + "/exported.zip"
            with open(path, "wb") as fp:
                for data in res.app_iter:
                    fp.write(data)
            assert_that(get_file_size(path), greater_than(0))
            assert_that(zipfile.is_zipfile(path), is_(True))
        finally:
            shutil.rmtree(tmp_dir, True)

    @WithSharedApplicationMockDS(testapp=True, users=True)
    def test_export_contents(self):
        res = self.testapp.get('/dataserver2/Objects/%s/@@Export' % self.ntiid,
                               status=200)
        self._test_export(res)

    @WithSharedApplicationMockDS(testapp=True, users=True)
    def test_admin_export(self):
        href = '/dataserver2/Library/@@ExportRenderedContents'
        res = self.testapp.get(href + "?ntiid=%s" % self.ntiid,
                               status=200)
        self._test_export(res)

    def _create_package(self):
        href = '/dataserver2/Library'
        package = RenderableContentPackage(title=u'Bleach',
                                           description=u'Manga bleach')
        ext_obj = to_external_object(package)
        ext_obj.pop('NTIID', None)
        ext_obj.pop('ntiid', None)

        res = self.testapp.post_json(href, ext_obj, status=201)
        return res.json_body['NTIID']
    
    @WithSharedApplicationMockDS(testapp=True, users=True)
    def test_export_editable(self):
        ntiid = self._create_package()
        href = '/dataserver2/Library/%s/@@Export' % ntiid
        res = self.testapp.get(href + "?backup=False&salt=ichigo",
                               status=200)
        assert_that(res.json_body,
                    has_entries('MimeType', 'application/vnd.nextthought.renderablecontentpackage',
                                'description', 'Manga bleach',
                                'isPublished', False,
                                'title', 'Bleach',
                                'salt', 'ichigo'))
