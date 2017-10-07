#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from docutils.nodes import Element
from docutils.nodes import General

logger = __import__('logging').getLogger(__name__)


class nticard(General, Element):
    pass


class ntivideo(General, Element):
    pass


class ntivideoref(General, Element):
    pass


class naassessmentref(General, Element):
    pass


class naassignmentref(naassessmentref):
    pass


class naquestionsetref(naassessmentref):
    pass


class naquestionref(naassessmentref):
    pass


class nasurveyref(naassessmentref):
    pass


class napollref(naassessmentref):
    pass
