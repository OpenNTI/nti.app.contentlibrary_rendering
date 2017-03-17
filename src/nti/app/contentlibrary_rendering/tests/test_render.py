#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division

__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_item
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import contains_string
does_not = is_not

import os
import fudge

from zope import component

from nti.contentlibrary.zodb import RenderableContentPackage

from nti.contentlibrary_rendering.interfaces import IContentTransformer
from nti.contentlibrary_rendering.interfaces import IContentPackageRenderMetadata

from nti.contentlibrary_rendering._render import render_document

from nti.app.contentlibrary_rendering.tests import ContentlibraryRenderingLayerTest

from nti.namedfile.file import safe_filename

from nti.ntiids.ntiids import TYPE_HTML
from nti.ntiids.ntiids import make_ntiid
from nti.ntiids.ntiids import make_specific_safe


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
    def test_render_job(self, mock_find_package):
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

    def _get_rst_data(self, filename='sample.rst'):
        path = os.path.join(os.path.dirname(__file__), filename)
        with open(path, 'r') as f:
            result = f.read()
        return result

    def _get_rst_dom(self, rst_source):
        transformer = component.getUtility(IContentTransformer, 'rst')
        return transformer.transform(rst_source, context=None)

    def _get_page_filename(self, job_name, page_name):
        specific = make_specific_safe('%s %s' % (job_name, page_name))
        ntiid = make_ntiid(provider='NTI', nttype=TYPE_HTML, specific=specific)
        filename = safe_filename(ntiid)
        # Rendering also obscures periods/commas.
        filename = filename.replace('.', '_')
        filename = filename.replace(',', '_')
        filename = '%s.html' % filename
        return filename

    def test_sections(self):
        new_content = self._get_rst_data('sections.rst')
        rst_dom = self._get_rst_dom(new_content)
        job_name = 'wowza_sections'
        page_name = 'Section Title'.lower()
        page_file = self._get_page_filename(job_name, page_name)

        tex_dom = render_document(rst_dom, jobname=job_name)
        output_dir = tex_dom.userdata['working-dir']
        output_files = os.listdir(output_dir)
        assert_that(output_files, has_item('index.html'))
        assert_that(output_files, has_item('eclipse-toc.xml'))
        assert_that(output_files, does_not(has_item(page_file)))

        with open('%s/%s' % (output_dir, 'index.html'), 'r') as f:
            page_contents = f.read()

        assert_that(page_contents, contains_string('This is a title, with punctuation.'))
        assert_that(page_contents.count('This is a title, with punctuation.</div>'), is_(1))
        assert_that(page_contents, contains_string('This is a section title.'))
        assert_that(page_contents.count('This is a section title.</div>'), is_(1))
        assert_that(page_contents, contains_string('Paragraph title'))
        assert_that(page_contents.count('Paragraph title</div>'), is_(1))
        assert_that(page_contents,
                    contains_string('<div class="subsection title" id="5">literals \' " , . - _ ! \ / [ ]*+=#(){}&lt;&gt;@|^&amp;'))
        assert_that(page_contents,
                    contains_string('<div class="paragraph title" id="6">literals \' " , . - _ ! \ / [ ]*+=#(){}&lt;&gt;@|^&amp;'))

    def test_render_basic(self):
        new_content = self._get_rst_data('basic.rst')
        rst_dom = self._get_rst_dom(new_content)
        job_name = 'wowza_basic'
        page_name = 'Section Title'.lower()
        page_file = self._get_page_filename(job_name, page_name)

        tex_dom = render_document(rst_dom, jobname=job_name)
        output_dir = tex_dom.userdata['working-dir']
        output_files = os.listdir(output_dir)
        assert_that(output_files, has_item('index.html'))
        assert_that(output_files, has_item('eclipse-toc.xml'))
        assert_that(output_files, does_not(has_item(page_file)))

        with open('%s/%s' % (output_dir, 'index.html'), 'r') as f:
            page_contents = f.read()

        assert_that(page_contents, contains_string('Section Title'))
        assert_that(page_contents, contains_string('SubSection1'))
        assert_that(page_contents, contains_string('SubSection2'))
        assert_that(page_contents, contains_string('SubsubSection1'))
        assert_that(page_contents, contains_string('SubsubSection2'))
        assert_that(page_contents, contains_string('basic text'))

    def test_render_sample(self):
        new_content = self._get_rst_data('sample.rst')
        rst_dom = self._get_rst_dom(new_content)
        job_name = 'wowza_sample'
        page_name = 'Section Title'.lower()
        page_file = self._get_page_filename(job_name, page_name)

        tex_dom = render_document(rst_dom, jobname=job_name)
        output_dir = tex_dom.userdata['working-dir']
        output_files = os.listdir(output_dir)
        assert_that(output_files, has_item('index.html'))
        assert_that(output_files, has_item('eclipse-toc.xml'))
        assert_that(output_files, does_not(has_item(page_file)))

        with open('%s/%s' % (output_dir, 'index.html'), 'r') as f:
            page_contents = f.read()

        assert_that(page_contents,
                    does_not(contains_string('Duplicate implicit target')))

        # Requirements
        # 1. headers
        assert_that(page_contents, contains_string('SubSection1'))
        assert_that(page_contents, contains_string('SubSection2'))
        assert_that(page_contents.count('SubSection1</div>'), is_(1))
        assert_that(page_contents.count('SubSection2</div>'), is_(1))
        assert_that(page_contents, contains_string('SubsubSection1'))
        assert_that(page_contents, contains_string('SubsubSection2'))
        # 2. paragraphs
        assert_that(page_contents, contains_string('<p class="par"'))
        # 3. bold
        assert_that(page_contents,
                    contains_string('<b class="bfseries">bold</b>'))
        # 4. italic
        assert_that(page_contents, contains_string('<em>italics</em>'))
        # 5. underlines
        assert_that(page_contents, contains_string('<span class="underline">underlined text</span>'))
        # 6. unordered list
        assert_that(page_contents, contains_string('<ul'))
        assert_that(page_contents, contains_string('<li>'))
        assert_that(page_contents, contains_string('Bullet List Item 1'))
        # 7. ordered list
        assert_that(page_contents, contains_string('<ol'))
        assert_that(page_contents, contains_string('Ordered List Item 1'))
        assert_that(page_contents, contains_string('<ol'))
        assert_that(page_contents, contains_string('Ordered List Item 1'))
        # 8. boldunderline
        assert_that(page_contents, contains_string('<b class="bfseries"><span class="underline">boldunderline</span></b>'))
        assert_that(page_contents, contains_string('<b class="bfseries"><span class="underline">boldunderlined</span></b>'))
        # 9. bolditalic
        assert_that(page_contents, contains_string('<b class="bfseries"><em>bolditalic</em></b>'))
        # 10. italicunderline
        assert_that(page_contents, contains_string('<em><span class="underline">italicunderline</span></em>'))
        assert_that(page_contents, contains_string('<em><span class="underline">italicunderlined</span></em>'))
        # 11. bolditalicunderline
        assert_that(page_contents,
                    contains_string('<b class="bfseries"><em><span class="underline">bolditalicunderline</span></em></b>'))
        assert_that(page_contents,
                    contains_string('<b class="bfseries"><em><span class="underline">bolditalicunderlined</span></em></b>'))

        # images/figures
        # video embed
        # links
