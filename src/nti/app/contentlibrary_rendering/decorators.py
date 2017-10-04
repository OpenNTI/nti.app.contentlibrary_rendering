#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import six

from zope import component
from zope import interface

from pyramid.interfaces import IRequest

from pyramid.threadlocal import get_current_request

from nti.app.contentlibrary_rendering import VIEW_QUERY_JOB
from nti.app.contentlibrary_rendering import LIBRARY_ADAPTER
from nti.app.contentlibrary_rendering import VIEW_LIB_JOB_ERROR
from nti.app.contentlibrary_rendering import VIEW_LIB_JOB_STATUS

from nti.app.renderers.decorators import AbstractAuthenticatedRequestAwareDecorator

from nti.appserver.pyramid_authorization import has_permission

from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentRendered
from nti.contentlibrary.interfaces import IContentUnitHrefMapper
from nti.contentlibrary.interfaces import IRenderableContentPackage

from nti.contentlibrary_rendering.interfaces import ILibraryRenderJob
from nti.contentlibrary_rendering.interfaces import IContentPackageRenderJob
from nti.contentlibrary_rendering.interfaces import IContentPackageRenderMetadata

from nti.dataserver.authorization import ACT_CONTENT_EDIT
from nti.dataserver.authorization import ACT_SYNC_LIBRARY 

from nti.dataserver.interfaces import IUser

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.externalization.singleton import SingletonMetaclass

from nti.links.links import Link

LINKS = StandardExternalFields.LINKS

logger = __import__('logging').getLogger(__name__)


def get_ds2(request=None):
    request = request if request else get_current_request()
    try:
        # e.g. /dataserver2
        result = request.path_info_peek() if request else None
    except AttributeError:  # in unit test we may see this
        result = None
    return result or "dataserver2"


def _library_adapter_path(request=None):
    path = '/%s/%s' % (get_ds2(request), LIBRARY_ADAPTER)
    return path


def _package_url_path(package, request=None):
    path = '%s/%s' % (_library_adapter_path(request), package.ntiid)
    return path


@six.add_metaclass(SingletonMetaclass)
@component.adapter(IRenderableContentPackage)
@interface.implementer(IExternalMappingDecorator)
class _RenderablePackageDecorator(object):
    """
    Decorates IRenderableContentPackage.
    """

    def __init__(self, *args):
        pass

    def decorateExternalMapping(self, context, mapping):
        mapping['isRendered'] = IContentRendered.providedBy(context)


@interface.implementer(IExternalMappingDecorator)
@component.adapter(IRenderableContentPackage, IRequest)
class _RenderablePackageEditorDecorator(AbstractAuthenticatedRequestAwareDecorator):
    """
    Decorates IRenderableContentPackage with render info.
    """

    def _predicate(self, context, unused_result):
        return self._is_authenticated \
           and has_permission(ACT_CONTENT_EDIT, context, self.request)

    def _render_job_link(self, context, result):
        meta = IContentPackageRenderMetadata(context, None)
        if meta is not None:
            latest_job = meta.mostRecentRenderJob()
            if latest_job is not None:
                # Decorate the job itself along with a link to fetch job
                # status.
                result['LatestRenderJob'] = latest_job
                _links = result.setdefault(LINKS, [])
                path = _package_url_path(context, self.request)
                link = Link(path,
                            rel=VIEW_QUERY_JOB,
                            elements=('@@' + VIEW_QUERY_JOB,),
                            ignore_properties_of_target=True)
                link.__name__ = ''
                link.__parent__ = context
                _links.append(link)

    def _render_link(self, context, result):
        _links = result.setdefault(LINKS, [])
        path = _package_url_path(context, self.request)
        link = Link(path,
                    rel="render",
                    elements=("@@render",),
                    ignore_properties_of_target=True)
        link.__name__ = ''
        link.__parent__ = context
        _links.append(link)

    def _do_decorate_external(self, context, result):
        self._render_link(context, result)
        self._render_job_link(context, result)


@interface.implementer(IExternalMappingDecorator)
@component.adapter(IContentPackageRenderJob, IRequest)
class _ContentPackageRenderJobDecorator(AbstractAuthenticatedRequestAwareDecorator):
    """
    Decorates IContentPackageRenderJob with render info.
    """

    def _do_decorate_external(self, context, result):
        # set jobId link
        _links = result.setdefault(LINKS, [])
        package = IRenderableContentPackage(context)
        path = _package_url_path(package, self.request)
        link = Link(path,
                    rel=VIEW_QUERY_JOB,
                    elements=('@@' + VIEW_QUERY_JOB,),
                    params={'jobId': context.job_id},
                    ignore_properties_of_target=True)
        link.__name__ = ''
        link.__parent__ = context
        _links.append(link)
        # set index property
        mapper = IContentUnitHrefMapper(context.OutputRoot, None)
        if mapper is not None:
            href = mapper.href
            result['root'] = href
            result['href'] = os.path.join(href, 'index.html')
            result['index'] = os.path.join(href, 'eclipse-toc.xml')
            result['index_jsonp'] = os.path.join(href, 'eclipse-toc.xml.jsonp')


@component.adapter(ILibraryRenderJob, IRequest)
@interface.implementer(IExternalObjectDecorator)
class _LibraryRenderJobDecorator(AbstractAuthenticatedRequestAwareDecorator):
    """
    Decorates ILibraryRenderJob with render info.
    """

    def _do_decorate_external(self, context, result):
        _links = result.setdefault(LINKS, [])
        path = _library_adapter_path(self.request)
        for rel, name in (('error', VIEW_LIB_JOB_ERROR),
                          ('status', VIEW_LIB_JOB_STATUS)):
            link = Link(path,
                        rel=rel,
                        elements=('@@' + name,),
                        params={'jobId': context.job_id},
                        ignore_properties_of_target=True)
            link.__name__ = ''
            link.__parent__ = context
            _links.append(link)
        # remove unused
        result.pop('Error', None)
        result.pop('State', None)


@component.adapter(IContentPackage, IRequest)
@interface.implementer(IExternalMappingDecorator)
class _ContentPackageDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, unused_result):
        return  self._is_authenticated \
            and has_permission(ACT_SYNC_LIBRARY, context, self.request)

    def _do_decorate_external(self, context, result):
        if     not IRenderableContentPackage.providedBy(context) \
            or IContentRendered.providedBy(context):
            _links = result.setdefault(LINKS, [])
            path = _package_url_path(context, self.request)
            for name, method in (('Export', 'GET'),):
                link = Link(path,
                            rel=name,
                            method=method,
                            elements=('@@' + name,),
                            ignore_properties_of_target=True)
                link.__name__ = ''
                link.__parent__ = context
                _links.append(link)


@component.adapter(IUser, IRequest)
@interface.implementer(IExternalMappingDecorator)
class _UserDecorator(AbstractAuthenticatedRequestAwareDecorator):

    def _predicate(self, context, unused_result):
        return  self._is_authenticated \
            and has_permission(ACT_SYNC_LIBRARY, context, self.request)

    def _do_decorate_external(self, context, result):
        _links = result.setdefault(LINKS, [])
        path = _library_adapter_path(self.request)
        for name, method in (('ExportRenderedContent', 'GET'),
                             ('ImportRenderedContent', 'POST')):
            link = Link(path,
                        rel=name,
                        method=method,
                        elements=('@@' + name,),
                        ignore_properties_of_target=True)
            link.__name__ = ''
            link.__parent__ = context
            _links.append(link)
