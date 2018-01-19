#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import starts_with
from hamcrest import has_property
does_not = is_not

import os
import shutil
from io import BytesIO

import fudge

from zope import component

from nti.app.contentlibrary.tests import PersistentApplicationTestLayer

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.cabinet.mixins import SourceFile

from nti.contentlibrary import RST_MIMETYPE

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contentlibrary.utils import operate_encode_content
from nti.contentlibrary.utils import get_content_package_site

from nti.contentlibrary.zodb import RenderableContentPackage

from nti.dataserver.tests import mock_dataserver

from nti.externalization.externalization import to_external_object


class TestImportViews(ApplicationLayerTest):

    layer = PersistentApplicationTestLayer

    default_origin = 'http://janux.ou.edu'

    ntiid = 'tag:nextthought.com,2011-10:OU-HTML-CS1323_F_2015_Intro_to_Computer_Programming.introduction_to_computer_programming'

    @WithSharedApplicationMockDS(testapp=True, users=True)
    @fudge.patch('nti.app.contentlibrary_rendering.views.import_views.get_all_sources')
    def test_import_contents(self, mock_gas):
        res = self.testapp.get('/dataserver2/Objects/%s/@@Export' % self.ntiid,
                               status=200)
        source = BytesIO()
        for data in res.app_iter:
            source.write(data)
        source.seek(0)
        source = SourceFile(name=u"CS1323_F_2015_Intro_to_Computer_Programming.zip",
                            data=source.read(),
                            contentType="application/zip")
        mock_gas.is_callable().with_args().returns({
            "CS1323_F_2015_Intro_to_Computer_Programming.zip": source
        })
        try:
            # post new
            res = self.testapp.post_json('/dataserver2/Library/@@ImportRenderedContent',
                                         {'site': 'janux.ou.edu',
                                          'obfuscate': False},
                                         status=200)
            assert_that(res.json_body,
                        has_entry('Items', has_key(self.ntiid)))

            with mock_dataserver.mock_db_trans(self.ds, site_name='janux.ou.edu'):
                library = component.getUtility(IContentPackageLibrary)
                package = library.get(self.ntiid)
                site_name = get_content_package_site(package)
                assert_that(site_name, is_('janux.ou.edu'))

            # post update
            source.seek(0)
            res = self.testapp.post_json('/dataserver2/Library/@@ImportRenderedContent',
                                         {'site': 'janux.ou.edu',
                                          'obfuscate': True},
                                         status=200)

            assert_that(res.json_body,
                        has_entry('Items',
                                  has_entry(self.ntiid,
                                            has_entry('root', starts_with('/sites/janux.ou.edu/_rendered_')))))
        finally:
            path = os.path.join(self.layer.library_path,
                                'sites', 'janux.ou.edu')
            shutil.rmtree(path, True)

    def _create_package(self):
        href = '/dataserver2/Library'
        package = RenderableContentPackage(title=u'Bleach',
                                           description=u'Manga bleach')
        package.write_contents('ichigo', RST_MIMETYPE)
        ext_obj = to_external_object(package)
        # pylint: disable=expression-not-assigned
        [ext_obj.pop(x, None) for x in ('NTIID', 'ntiid')]

        res = self.testapp.post_json(href, ext_obj, status=201)
        return res.json_body['NTIID']

    @WithSharedApplicationMockDS(testapp=True, users=True)
    def test_import_editable(self):
        ntiid = self._create_package()
        href = '/dataserver2/Library/%s/@@Export' % ntiid
        res = self.testapp.get(href + "?backup=True",
                               status=200)
        data = res.json_body
        data['contents'] = operate_encode_content('rukia', None)
        href = '/dataserver2/Library/%s/@@Import' % ntiid
        self.testapp.post_json(href, data, status=200)
        with mock_dataserver.mock_db_trans(self.ds, site_name='janux.ou.edu'):
            library = component.getUtility(IContentPackageLibrary)
            package = library.get(ntiid)
            assert_that(package, has_property('contents', is_(b'rukia')))
