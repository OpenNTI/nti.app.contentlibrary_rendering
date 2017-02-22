#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import os
import fudge
import shutil
import tempfile

from nti.cabinet.mixins import SourceFile

from nti.contentlibrary_rendering._render import render_document

from nti.contentlibrary_rendering.docutils import publish_doctree

from nti.app.testing.application_webtest import ApplicationLayerTest


class TestTranslators(ApplicationLayerTest):

    URL = 'https://en.wikipedia.org/wiki/Ichigo_Kurosaki'

    def _ichigo_asset(self):
        result = SourceFile(name="ichigo.png")
        name = os.path.join(os.path.dirname(__file__), 'data/ichigo.png')
        with open(name, "rb") as fp:
            result.data = fp.read()
        return result

    def _generate_from_file(self, source):
        current_dir = os.getcwd()
        try:
            # change directory early
            tex_dir = tempfile.mkdtemp(prefix="render_")
            os.chdir(tex_dir)
            # parse and run directives
            name = os.path.join(os.path.dirname(__file__), 'data/%s' % source)
            with open(name, "rb") as fp:
                source_doc = publish_doctree(fp.read())
            return
            # render
            document = render_document(source_doc,
                                       outfile_dir=tex_dir,
                                       jobname="sample")
            index = os.path.join(tex_dir, 'index.html')
            assert_that(os.path.exists(index), is_(True))
        except Exception:
            print('Exception %s, %s' % (source, tex_dir))
            raise
        else:
            shutil.rmtree(tex_dir)
        finally:
            os.chdir(current_dir)
        return document

    @fudge.patch('nti.app.contentlibrary_rendering.docutils.directives.validate_reference',
                 'nti.app.contentlibrary_rendering.docutils.directives.is_dataserver_asset',
                 'nti.app.contentlibrary_rendering.docutils.directives.get_dataserver_asset')
    def test_nticard(self, mock_val, mock_isca, mock_gca):
        mock_val.is_callable().with_args().returns(self.URL)
        mock_isca.is_callable().with_args().returns(True)
        mock_gca.is_callable().with_args().returns(self._ichigo_asset())
        self._generate_from_file('nticard.rst')
