#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from requests.structures import CaseInsensitiveDict

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.contentlibrary_rendering.views import validate_content
from nti.app.contentlibrary_rendering.views import MessageFactory as _

from nti.app.externalization.error import raise_json_error

from nti.app.publishing import VIEW_PUBLISH
from nti.app.publishing import VIEW_UNPUBLISH

from nti.common.string import is_true

from nti.contentlibrary.interfaces import IRenderableContentPackage
from nti.contentlibrary.interfaces import resolve_content_unit_associations

from nti.dataserver import authorization as nauth

from nti.externalization.externalization import to_external_object
from nti.externalization.externalization import StandardExternalFields

from nti.links.links import Link

CLASS = StandardExternalFields.CLASS
LINKS = StandardExternalFields.LINKS
MIME_TYPE = StandardExternalFields.MIMETYPE


@view_config(context=IRenderableContentPackage)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               name=VIEW_PUBLISH,
               permission=nauth.ACT_CONTENT_EDIT)
class RenderableContentPackagePublishView(AbstractAuthenticatedView):

    def __call__(self):
        validate_content(self.context, self.request)
        self.context.publish()
        return self.context


@view_config(context=IRenderableContentPackage)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               name=VIEW_UNPUBLISH,
               permission=nauth.ACT_CONTENT_EDIT)
class RenderableContentPackageUnpublishView(AbstractAuthenticatedView):
    """
    A view to unpublish a renderable content package.
    """
    CONFIRM_CODE = u'RenderableContentPackageUnpublish'
    CONFIRM_MSG = _(u'This content has been published to courses. Are you sure you want to unpublish?')

    def _ntiids(self, associations):
        for x in associations or ():
            try:
                yield x.ntiid
            except AttributeError:
                pass

    def _raise_conflict_error(self, code, message, courses):
        associations = resolve_content_unit_associations(self.context)
        associations = [x for x in self._ntiids(associations)]
        logger.warn('Attempting to unpublish content unit in course(s) (%s) (%s)',
                    self.context.ntiid,
                    associations)
        params = dict(self.request.params)
        params['force'] = True
        links = (
            Link(self.request.path, rel='confirm',
                 params=params, method='POST'),
        )
        raise_json_error(self.request,
                         hexc.HTTPConflict,
                         {
                             CLASS: 'DestructiveChallenge',
                             u'message': message,
                             u'code': code,
                             LINKS: to_external_object(links),
                             MIME_TYPE: 'application/vnd.nextthought.destructivechallenge'
                         },
                         None)

    def __call__(self):
        associations = resolve_content_unit_associations(self.context)
        params = CaseInsensitiveDict(self.request.params)
        force = is_true(params.get('force'))
        if not associations or force:
            self.context.unpublish()
        else:
            self._raise_conflict_error(self.CONFIRM_CODE,
                                       self.CONFIRM_MSG,
                                       associations)
        return self.context
