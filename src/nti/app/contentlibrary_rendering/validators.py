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

from nti.base._compat import text_

from nti.contentlibrary_rendering.docutils.validators import MSG_PATTERN
from nti.contentlibrary_rendering.docutils.validators import RSTEmptyCodeBlockError
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
            warnings = text_(warnings)
            logger.warn("reStructuredText parsing warnings\n %s \n", warnings)
        return warnings

    def is_empty_code_block(self, message):
        m = MSG_PATTERN.match(message)
        groups = m.groups() if m else ()
        return groups \
           and groups[0] == '(ERROR/3)' \
           and 'Content block expected' in groups[1]

    def create_rst_error(self, e, warnings):
        message = str(e)
        if self.is_empty_code_block(message):
            result = RSTEmptyCodeBlockError(message, warnings)
        else:
            result = RSTContentValidationError(message, warnings)
        return result

    def _do_validate(self, content, unused_context=None):
        settings = self._get_settings()
        try:
            self.doctree(content, settings)
            return self._log_warnings(settings)
        except Exception as e:
            logger.exception("While validating RST")
            warnings = self._log_warnings(settings)
            exct = self.create_rst_error(e, warnings)
            raise exct

    def validate(self, content=b'', context=None):
        if content:
            return self._do_validate(content, context)
