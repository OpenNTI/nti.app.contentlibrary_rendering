#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from nti.contentlibrary.interfaces import IContentValidator


class IRSTContentValidator(IContentValidator):
    """
    Marker interface for a content validator utility
    """

    def doctree(content, settings=None):
        """
        :param content: The content to parse
        :param settings: Parser settings
        :return a docutils DOM tree
        """
