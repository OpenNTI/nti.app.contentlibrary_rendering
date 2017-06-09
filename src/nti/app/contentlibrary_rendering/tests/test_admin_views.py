#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import greater_than_or_equal_to
does_not = is_not

from nti.contentlibrary.zodb import RenderableContentPackage

from nti.contentlibrary_rendering.interfaces import IContentPackageRenderMetadata

from nti.contentlibrary_rendering.model import ContentPackageRenderJob

from nti.externalization.externalization import to_external_object

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.app.contentlibrary.tests import PersistentApplicationTestLayer

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver


class TestAdminViews(ApplicationLayerTest):

    layer = PersistentApplicationTestLayer

    default_origin = 'http://janux.ou.edu'

    def _create_package_and_job(self):
        href = '/dataserver2/Library'
        package = RenderableContentPackage(title=u'Bleach',
                                           description=u'Manga bleach')
        ext_obj = to_external_object(package)
        ext_obj.pop('NTIID', None)
        ext_obj.pop('ntiid', None)

        res = self.testapp.post_json(href, ext_obj, status=201)
        ntiid = res.json_body['NTIID']

        job = ContentPackageRenderJob()
        job.state = u'Failed'
        job.package = ntiid
        job.provider = u'NTI'
        job.creator = self.default_username
        job.jobId = u'tag:nextthought.com,2011-10:NTI-RenderJob-58'

        with mock_dataserver.mock_db_trans(self.ds, site_name='janux.ou.edu'):
            package = find_object_with_ntiid(ntiid)
            meta = IContentPackageRenderMetadata(package)
            meta[job.jobId] = job

    @WithSharedApplicationMockDS(testapp=True, users=True)
    def test_rebuild_job_catalog(self):
        self._create_package_and_job()
        res = self.testapp.post('/dataserver2/Library/@@RebuildContentRenderingJobCatalog',
                                status=200)
        assert_that(res.json_body,
                    has_entries('Total', is_(greater_than_or_equal_to(1)),
                                'ItemCount', is_(greater_than_or_equal_to(1))))
