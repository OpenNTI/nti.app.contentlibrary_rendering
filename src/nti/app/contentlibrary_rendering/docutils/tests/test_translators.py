#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import contains_string

import os
import fudge
import shutil
import tempfile

import simplejson

from nti.cabinet.mixins import SourceFile

from nti.contentlibrary_rendering._render import render_document

from nti.contentlibrary_rendering.docutils import publish_doctree

from nti.contenttypes.presentation.media import NTIVideo

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.app.testing.application_webtest import ApplicationLayerTest


class TestTranslators(ApplicationLayerTest):

    URL = u'https://en.wikipedia.org/wiki/Ichigo_Kurosaki'
    
    def _ichigo_asset(self):
        result = SourceFile(name=u"ichigo.png")
        name = os.path.join(os.path.dirname(__file__), 'data/ichigo.png')
        with open(name, "rb") as fp:
            result.data = fp.read()
        return result

    def _question(self):
        name = os.path.join(os.path.dirname(__file__), 'data/evaluation.json')
        with open(name, "rb") as fp:
            data = fp.read()
        data = data.decode('utf-8') if isinstance(data, bytes) else data
        ext_obj = simplejson.loads(data)
        factory = find_factory_for(ext_obj)
        result = factory()
        update_from_external_object(result, ext_obj, notify=False)
        return result

    def _generate_from_file(self, source):
        index = document = None
        current_dir = os.getcwd()
        try:
            # change directory early
            tex_dir = tempfile.mkdtemp(prefix="render_")
            os.chdir(tex_dir)
            # parse and run directives
            name = os.path.join(os.path.dirname(__file__), 'data/%s' % source)
            with open(name, "rb") as fp:
                source_doc = publish_doctree(fp.read())
            # render
            document = render_document(source_doc,
                                       outfile_dir=tex_dir,
                                       jobname=u"sample")
            index = os.path.join(tex_dir, 'index.html')
            assert_that(os.path.exists(index), is_(True))
            with open(index, "r") as fp:
                index = fp.read()
        except Exception:
            print('Exception %s, %s' % (source, tex_dir))
            raise
        else:
            shutil.rmtree(tex_dir)
        finally:
            os.chdir(current_dir)
        return (index, document)

    @fudge.patch('nti.app.contentlibrary_rendering.docutils.translators.is_href_a_dataserver_asset',
                 'nti.app.contentlibrary_rendering.docutils.translators.is_image_a_dataserver_asset',
                 'nti.app.contentlibrary_rendering.docutils.translators.get_dataserver_asset')
    def test_nticard(self, mock_href, mock_image, mock_get):
        mock_href.is_callable().with_args().returns(False)
        mock_image.is_callable().with_args().returns(True)
        mock_get.is_callable().with_args().returns(self._ichigo_asset())
        index, _ = self._generate_from_file('nticard.rst')
        assert_that(index, contains_string('<object class="nticard"'))
        assert_that(index,
                    contains_string('<span class="description">Bankai last form</span>'))
        
    def test_ntivdeo(self):
        index, _ = self._generate_from_file('ntivideo.rst')
        assert_that(index, contains_string('<object class="ntivideo"'))
        assert_that(index, contains_string('<param name="title" value="Structure and Design"'))
        assert_that(index, contains_string('<span class="description">Course'))
        assert_that(index, contains_string('type="application/vnd.nextthought.videosource"'))
        assert_that(index, contains_string('<param name="service" value="kaltura"'))
        assert_that(index, contains_string('<param name="source" value="1500101:0_udtp5zmz"'))
        
    @fudge.patch('nti.app.contentlibrary_rendering.docutils.translators.find_object_with_ntiid')
    def test_ntivideoref(self, mock_fon):
        media = NTIVideo()
        media.creator = u'Tite Kubo'
        media.title = u'Ichigo vs Aizen'
        media.ntiid = u'tag:nextthought.com,2011-10:BLEACH-NTIVideo-Ichigo.vs.Aizen'
        mock_fon.is_callable().with_args().returns(media)
        index, _ = self._generate_from_file('ntivideoref.rst')
        assert_that(index, contains_string('<object class="ntivideoref"'))
        assert_that(index, contains_string('<param name="visibility" value="everyone"'))
        assert_that(index, contains_string('<param name="label" value="Ichigo vs Aizen"'))
        assert_that(index, 
                    contains_string('<param name="mimeType" value="application/vnd.nextthought.ntivideo"'))
        assert_that(index, 
                    contains_string('<param name="ntiid" value="tag:nextthought.com,2011-10:BLEACH-NTIVideo-Ichigo.vs.Aizen"'))

    @fudge.patch('nti.app.contentlibrary_rendering.docutils.translators.find_object_with_ntiid')
    def test_naquestionref(self, mock_fon):
        question = self._question()
        mock_fon.is_callable().with_args().returns(question)
        index, _ = self._generate_from_file('naquestionref.rst')
        assert_that(index, contains_string('<object class="question"'))
        assert_that(index, 
                    contains_string('<param name="type" value="application/vnd.nextthought.naquestion"'))
        assert_that(index, 
                    contains_string('<param name="target-ntiid" value="tag:nextthought.com,2011-10:NTI-NAQ-BLEACH"'))
