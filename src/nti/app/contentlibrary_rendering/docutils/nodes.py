#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from docutils.nodes import Element
from docutils.nodes import General


class nticard(General, Element):
    pass


class ntivideo(General, Element):
    pass


class ntivideoref(General, Element):
    pass
