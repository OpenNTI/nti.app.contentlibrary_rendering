#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import greater_than
does_not = is_not

import shutil
import zipfile
import tempfile

from nti.cabinet.mixins import get_file_size

from nti.app.contentlibrary.tests import PersistentApplicationTestLayer

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS


class TestExportViews(ApplicationLayerTest):

    layer = PersistentApplicationTestLayer

    default_origin = 'http://janux.ou.edu'

    ntiid = 'tag:nextthought.com,2011-10:OU-HTML-CS1323_F_2015_Intro_to_Computer_Programming.introduction_to_computer_programming'

    @WithSharedApplicationMockDS(testapp=True, users=True)
    def test_export_contents(self):
        res = self.testapp.get('/dataserver2/Objects/%s/@@Export' % self.ntiid,
                               status=200)
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
