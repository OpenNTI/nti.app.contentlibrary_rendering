#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid import httpexceptions as hexc

from nti.app.externalization.error import raise_json_error

from nti.contentlibrary.validators import validate_content_package as perform_content_validation

def validate_content(package, request):
    """
    Validate the given contents.
    """
    error = perform_content_validation(package)
    if error is not None:
        data, exc_info = error
        raise_json_error(request,
                         hexc.HTTPUnprocessableEntity,
                         data,
                         exc_info[2])
