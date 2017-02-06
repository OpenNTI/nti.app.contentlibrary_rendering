#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.publishing import VIEW_PUBLISH
from nti.app.publishing import VIEW_UNPUBLISH

from nti.contentlibrary.interfaces import IRenderableContentPackage

from nti.dataserver import authorization as nauth


@view_config(context=IRenderableContentPackage)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               name=VIEW_PUBLISH,
               permission=nauth.ACT_CONTENT_EDIT)
class RenderableContentPackagePublishView(AbstractAuthenticatedView):
    pass


@view_config(context=IRenderableContentPackage)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               name=VIEW_UNPUBLISH,
               permission=nauth.ACT_CONTENT_EDIT)
class RenderableContentPackageUnpublishView(AbstractAuthenticatedView):
    pass
