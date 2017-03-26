#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from requests.structures import CaseInsensitiveDict

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import get_all_sources
from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.contentlibrary.views import LibraryPathAdapter

from nti.app.contentlibrary_rendering.views import MessageFactory as _

from nti.app.externalization.error import raise_json_error

from nti.cabinet import NamedSource

from nti.contentlibrary_rendering._archive import render_archive

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT


@view_config(name="RenderContentSource")
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=LibraryPathAdapter,
               permission=nauth.ACT_SYNC_LIBRARY)
class RenderContentSourceView(AbstractAuthenticatedView,
                              ModeledContentUploadRequestUtilsMixin):

    MAX_SOURCE_SIZE = 524288000  # 500mb

    def readInput(self, value=None):
        result = super(RenderContentSourceView, self).readInput(value)
        return CaseInsensitiveDict(result)

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.request.view_name
        result.__parent__ = self.request.context
        result[ITEMS] = items = []
        # read params
        data = self.readInput()
        creator = self.remoteUser.username
        provider = data.get('provider') or 'NTI'
        site = data.get('site') or data.get('site_name')
        # process sources
        sources = get_all_sources(self.request, None)
        for name, source in sources.items():
            if source.length >= self.MAX_SOURCE_SIZE:
                raise_json_error(
                    self.request,
                    hexc.HTTPUnsupportedMediaType,
                    {
                        u'message': _("Max file size exceeded"),
                        u'code': 'MaxFileSizeExceeded',
                    },
                    None)
            filename = getattr(source, 'filename', None) or name
            # save source
            target = NamedSource(filename, source.data)
            # schedule
            status_id = render_archive(target,
                                       creator,
                                       site=site,
                                       provider=provider)
            items.append(status_id)
        result[ITEM_COUNT] = result[TOTAL] = len(items)
        return result
