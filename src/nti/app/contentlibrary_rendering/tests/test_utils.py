#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
does_not = is_not

import fudge

from zope import component

from zope.intid.interfaces import IIntIds

from nti.app.contentlibrary_rendering.utils import get_pending_render_jobs

from nti.contentlibrary_rendering.index import get_contentrenderjob_catalog

from nti.contentlibrary_rendering.model import ContentPackageRenderJob

from nti.app.contentlibrary_rendering.tests import ContentlibraryRenderingLayerTest

from nti.dataserver.tests import mock_dataserver


class TestUtils(ContentlibraryRenderingLayerTest):

    @mock_dataserver.WithMockDS
    @fudge.patch("nti.contentlibrary_rendering.index.find_interface")
    def test_get_pending_render_jobs(self, mock_fi):
        job = ContentPackageRenderJob()
        job.state = u'Pending'
        job.jobId = u'tag:nextthought.com,2011-10:NTI-RenderJob-58'
        job.package = u'tag:nextthought.com,2011-10:NTI-HTML-58'

        fake_folder = fudge.Fake()
        fake_folder.__name__ = u'janux.dev'
        mock_fi.is_callable().with_args().returns(fake_folder)

        with mock_dataserver.mock_db_trans(self.ds):
            intids = component.getUtility(IIntIds)
            current_transaction = mock_dataserver.current_transaction
            current_transaction.add(job)
            intids.register(job)
            doc_id = intids.getId(job)

            catalog = get_contentrenderjob_catalog()
            catalog.index_doc(doc_id, job)

            jobs = get_pending_render_jobs(sites='janux.dev')
            assert_that(jobs, has_length(1))

            jobs = get_pending_render_jobs(sites='janux.dev',
                                           packages='tag:nextthought.com,2011-10:NTI-HTML-58')
            assert_that(jobs, has_length(1))

            jobs = get_pending_render_jobs(sites='janux.dev', packages='foo')
            assert_that(jobs, has_length(0))
