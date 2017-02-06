#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys

from docutils import frontend

from docutils import nodes

from docutils.parsers.rst import Parser

from docutils.utils import new_reporter

from zope import interface

from nti.contentlibrary.interfaces import IContentValidator

from nti.contentlibrary_rendering.validators import ValidationError
from nti.contentlibrary_rendering.validators import EmptyContentError

@interface.implementer(IContentValidator)
class ReStructuredTextValidator(object):

    settings = frontend.OptionParser(
        components=(Parser,)).get_default_values()

    def _do_validate(self, content, context=None):
        try:
            parser = Parser()  # XXX: NTI directives should be included
            reporter = new_reporter("contents", self.settings)
            document = nodes.document(self.settings,
                                      reporter,
                                      source='contents')
            parser.parse(content, document)
        except Exception as e:
            exct = ValidationError("Invalid reStructuredText", e)
            exct.exc_info = sys.exc_info()
            raise exct

    def validate(self, content=b'', context=None):
        if content:
            self._do_validate(content)
        else:
            raise EmptyContentError("Empty content")
