#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import contains_string

import os
import unittest

from nti.app.contentlibrary_rendering.docutils.operators import RenderablePackageContentOperator

from nti.base._compat import text_

from nti.ntiids.ntiids import hash_ntiid


class TestOperators(unittest.TestCase):

    salt = '100'

    def _content(self, source):
        name = os.path.join(os.path.dirname(__file__), 'data/%s' % source)
        with open(name, "rb") as fp:
            return fp.read()
        
    def test_ntivideoref(self):
        ntiid = u'tag:nextthought.com,2011-10:BLEACH-NTIVideo-Ichigo.vs.Aizen'
        salted = hash_ntiid(ntiid, self.salt)
        content = text_(self._content('ntivideoref.rst'))
        operator = RenderablePackageContentOperator()
        content = operator.operate(content, backup=False, salt=self.salt)
        assert_that(content, contains_string(salted))
