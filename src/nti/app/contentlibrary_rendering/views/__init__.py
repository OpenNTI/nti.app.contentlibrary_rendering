#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from nti.app.contentlibrary import MessageFactory

from nti.app.externalization.error import raise_json_error

from nti.contentlibrary.interfaces import IContentValidationError

from nti.contentlibrary.validators import validate_content_package as perform_content_validation

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import LocatedExternalDict

logger = __import__('logging').getLogger(__name__)


def validate_content(package, request):
    """
    Validate the given contents.
    """
    error = perform_content_validation(package)
    if error is not None:
        e, exc_info = error
        data = LocatedExternalDict({
            'code': 'ContentValidationError',
        })
        if IContentValidationError.providedBy(e):
            error = to_external_object(e, decorate=False)
            data.update(error)
        else:
            data['message'] = repr(e)

        raise_json_error(request,
                         hexc.HTTPUnprocessableEntity,
                         data,
                         exc_info[2])
