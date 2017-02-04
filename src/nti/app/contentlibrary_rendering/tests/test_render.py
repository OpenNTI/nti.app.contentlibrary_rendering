#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division

__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that
does_not = is_not

import fudge

from nti.contentlibrary.zodb import RenderableContentPackage

from nti.contentlibrary_rendering.interfaces import IContentPackageRenderMetadata

from nti.app.contentlibrary_rendering.tests import ContentlibraryRenderingLayerTest


class TestRender(ContentlibraryRenderingLayerTest):

    def _get_package(self):
        # This would need to be in library (with diff ntiid) to test further.
        package = RenderableContentPackage()
        package.ntiid = u'tag:nextthought.com,2011-10:USSC-HTML-Cohen.cohen_v._california'
        package.title = u'Cohen vs California'
        package.description = u'Cohen vs California'
        package.contentType = b'text/x-rst'
        package.publishLastModified = 10000
        package.write_contents(b'foo', b'text/x-rst')
        return package

    @fudge.patch('nti.contentlibrary_rendering.common.find_object_with_ntiid')
    def test_render(self, mock_find_package):
        package = self._get_package()
        mock_find_package.is_callable().returns(package)
        meta = IContentPackageRenderMetadata(package, None)
        assert_that(meta, not_none())
        assert_that(meta, has_length(0))
        assert_that(meta.mostRecentRenderJob(), none())

        # Publish, job1
        package.publish()
        meta = IContentPackageRenderMetadata(package, None)
        job = meta.mostRecentRenderJob()
        assert_that(meta, not_none())
        assert_that(meta, has_length(1))
        assert_that(job, not_none())
        assert_that(job.is_finished(), is_(True))
        assert_that(job.PackageNTIID, is_(package.ntiid))
        assert_that(job.JobId, not_none())

        # Publish, job2
        package.unpublish()
        package.publish()
        meta = IContentPackageRenderMetadata(package, None)
        job2 = meta.mostRecentRenderJob()
        assert_that(meta, not_none())
        assert_that(meta, has_length(2))
        assert_that(job2, not_none())
        assert_that(job2.is_finished(), is_(True))
        assert_that(job2.PackageNTIID, is_(package.ntiid))
        assert_that(job, is_not(job2))
        assert_that(job.JobId, is_not(job2.JobId))
