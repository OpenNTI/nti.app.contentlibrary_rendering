#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from six import StringIO

from docutils.frontend import OptionParser

from docutils.parsers.rst import Parser

from zope import interface

from nti.contentlibrary.interfaces import IContentValidator

from nti.contentlibrary_rendering.docutils import publish_doctree

from nti.contentlibrary_rendering.docutils.validators import RSTContentValidationError


@interface.implementer(IContentValidator)
class ReStructuredTextValidator(object):

    def _get_settings(self):
        settings = OptionParser(components=(Parser,)).get_default_values()
        settings.halt_level = 2  # stop at warning
        settings.report_level = 2  # warnings
        settings.traceback = True
        settings.warning_stream = StringIO()
        return settings

    def _do_validate(self, content, context=None):
        settings = self._get_settings()
        try:
            publish_doctree(content, settings=settings)
        except Exception as e:
            settings.warning_stream.seek(0)
            warnings = settings.warning_stream.read()
            exct = RSTContentValidationError(str(e), warnings)
            raise exct

    def validate(self, content=b'', context=None):
        if content:
            self._do_validate(content)
