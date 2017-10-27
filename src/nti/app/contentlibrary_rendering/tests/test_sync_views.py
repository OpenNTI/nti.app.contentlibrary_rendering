#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_entries
does_not = is_not

import fudge

from nti.app.contentlibrary.tests import PersistentApplicationTestLayer

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.cabinet.mixins import SourceFile


class TestSyncViews(ApplicationLayerTest):

    layer = PersistentApplicationTestLayer

    default_origin = 'http://janux.ou.edu'

    @WithSharedApplicationMockDS(testapp=True, users=True)
    @fudge.patch('nti.app.contentlibrary_rendering.views.sync_views.get_all_sources',
                 'nti.app.contentlibrary_rendering.views.sync_views.render_archive')
    def test_render_source(self, mock_gas, mock_ra):
        name = u'cs.zip'
        source = SourceFile(name=name,
                            data=b'',
                            contentType="application/zip")
        mock_gas.is_callable().with_args().returns({
            "CS1323_F_2015_Intro_to_Computer_Programming.zip": source
        })

        mock_ra.is_callable().with_args().returns('job')
        res = self.testapp.post_json('/dataserver2/Library/@@RenderContentSource',
                                     {
                                         'site': 'platform.ou.edu',
                                         'provider': 'OU'
                                     },
                                     status=200)
        assert_that(res.json_body,
                    has_entry('Items', has_entry(name, 'job')))


    @WithSharedApplicationMockDS(testapp=True, users=True)
    @fudge.patch('nti.app.contentlibrary_rendering.views.sync_views.get_job_status')
    def test_get_job_status(self, mock_gjs):
        mock_gjs.is_callable().with_args().returns('Failed')
        res = self.testapp.get('/dataserver2/Library/@@RenderJobStatus?jobId=job',
                               status=200)
        assert_that(res.json_body,
                    has_entries('jobId', is_('job'),
                                'status', is_('Failed')))

    @WithSharedApplicationMockDS(testapp=True, users=True)
    @fudge.patch('nti.app.contentlibrary_rendering.views.sync_views.get_job_error')
    def test_get_job_error(self, mock_gje):
        mock_gje.is_callable().with_args().returns({'Error':'NPE'})
        res = self.testapp.get('/dataserver2/Library/@@RenderJobError?jobId=job',
                               status=200)
        assert_that(res.json_body,
                    has_entries('jobId', is_('job'),
                                'Error', is_('NPE')))
