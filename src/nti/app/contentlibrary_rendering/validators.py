#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from six.moves import cStringIO

from docutils.core import publish_doctree

from docutils.frontend import OptionParser

from docutils.parsers.rst import Parser

from zope import interface

from nti.app.contentlibrary_rendering.interfaces import IRSTContentValidator

from nti.contentlibrary_rendering.docutils.validators import RSTContentValidationError

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IRSTContentValidator)
class ReStructuredTextValidator(object):

    def _get_settings(self):
        settings = OptionParser(components=(Parser,)).get_default_values()
        settings.halt_level = 3  # stop at error
        settings.report_level = 2  # warnings
        settings.traceback = True
        settings.warning_stream = cStringIO()
        settings.character_level_inline_markup = True
        return settings

    def doctree(self, content, settings=None):
        settings = settings or self._get_settings()
        return publish_doctree(content, settings=settings)
         
    def _log_warnings(self, settings):
        settings.warning_stream.seek(0)
        warnings = settings.warning_stream.read()
        if warnings:
            logger.warn("reStructuredText parsing warnings\n" +
                        warnings + "\n")
        return warnings

    def _do_validate(self, content, unused_context=None):
        settings = self._get_settings()
        try:
            self.doctree(content, settings)
            return self._log_warnings(settings)
        except Exception as e:
            warnings = self._log_warnings(settings)
            exct = RSTContentValidationError(str(e), warnings)
            raise exct

    def validate(self, content=b'', context=None):
        if content:
            return self._do_validate(content, context)
