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

from nti.contentlibrary_rendering.unpublish import unpublish_package

from nti.contentlibrary_rendering.utils import render_package
from nti.contentlibrary_rendering.utils import remove_renderered_package

from nti.coremetadata.interfaces import IObjectPublishedEvent
from nti.coremetadata.interfaces import IObjectUnpublishedEvent

from nti.ntiids.ntiids import get_provider


@component.adapter(IRenderableContentPackage, IObjectPublishedEvent)
def _content_published(package, event):
    """
    When a renderable content package is published, render it.
    """
    user = get_remote_user()
    provider = get_provider(package.ntiid)
    render_package(package, user, provider)


@component.adapter(IRenderableContentPackage, IObjectUnpublishedEvent)
def _content_unpublished(package, event):
    unpublish_package(package)


@component.adapter(IRenderableContentPackage, IIntIdRemovedEvent)
def _content_removed(package, event):
    remove_renderered_package(package)
