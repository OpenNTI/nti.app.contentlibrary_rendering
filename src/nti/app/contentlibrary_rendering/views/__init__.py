#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys

from pyramid import httpexceptions as hexc

from zope import component

from nti.app.contentlibrary import MessageFactory

from nti.app.externalization.error import raise_json_error

from nti.contentlibrary.interfaces import IContentValidator
from nti.contentlibrary.interfaces import IContentValidationError

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict


def perform_content_validation(package):
    content_type = package.contentType
    validator = component.queryUtility(IContentValidator,
                                       name=content_type)
    if validator is not None:
        try:
            contents = package.contents
            validator.validate(contents)
        except Exception as e:
            exc_info = sys.exc_info()
            data = LocatedExternalDict({
                u'code': 'ContentValidationError',
            })
            if IContentValidationError.providedBy(e):
                error = to_external_object(e, decorate=False)
                data.update(error)
            else:
                data['message'] = str(e)
            return data, exc_info


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
