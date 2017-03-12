#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Event listeners.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.intid.interfaces import IIntIdRemovedEvent

from nti.app.authentication import get_remote_user

from nti.contentlibrary.interfaces import IRenderableContentPackage
from nti.contentlibrary.interfaces import IContentPackageLocationChanged

from nti.contentlibrary_rendering.interfaces import IContentPackageRenderMetadata

from nti.contentlibrary_rendering.utils import render_package
from nti.contentlibrary_rendering.utils import remove_renderered_package

from nti.coremetadata.interfaces import IObjectPublishedEvent

from nti.ntiids.ntiids import get_provider


@component.adapter(IRenderableContentPackage, IObjectPublishedEvent)
def _content_published(package, event):
    """
    When a renderable content package is published, render it.
    """
    user = get_remote_user()
    provider = get_provider(package.ntiid)
    render_package(package, user, provider)


@component.adapter(IRenderableContentPackage, IIntIdRemovedEvent)
def _content_removed(package, event):
    remove_renderered_package(package)
    meta = IContentPackageRenderMetadata(package, None)
    if meta is not None:
        meta.clear()


@component.adapter(IRenderableContentPackage, IContentPackageLocationChanged)
def _content_location_changed(package, event):
    old_root = event.old_root
    if old_root is not None:
        remove_renderered_package(package, old_root)
