#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import assert_that
does_not = is_not

import os

from zope import component

from nti.app.contentlibrary_rendering.validators import ReStructuredTextValidator

from nti.contentlibrary.interfaces import IContentValidator

from nti.contentlibrary_rendering.docutils.validators import RSTContentValidationError

from nti.app.contentlibrary_rendering.tests import ContentlibraryRenderingLayerTest


class TestValidators(ContentlibraryRenderingLayerTest):

    def test_validate_empty(self):
        validator = component.getUtility(IContentValidator, name="text/x-rst")
        validator.validate(None)
        validator.validate(b'')

    def test_validate_error(self):
        validator = component.getUtility(IContentValidator, name="text/x-rst")
        with self.assertRaises(RSTContentValidationError) as e:
            validator.validate(b"""Chapter 1 Title
                                   ========
                                """)
        assert_that(e.exception.warnings, not_none())
        assert_that(e.exception.message, 
                    is_('Unexpected section title or transition.'))

    def test_warnings(self):
        path = os.path.join(os.path.dirname(__file__), "formats.rst")
        with open(path, 'r') as f:
            content = f.read()
        validator = ReStructuredTextValidator()
        warnings = validator.validate(content)
        assert_that(warnings, is_not(none()))
