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

from nti.app.authentication import get_remote_user

from nti.contentlibrary.interfaces import IRenderableContentPackage

from nti.contentlibrary_rendering.utils import render_package
from nti.contentlibrary_rendering.utils import render_modified_package

from nti.coremetadata.interfaces import IObjectPublishedEvent
from nti.coremetadata.interfaces import IObjectUnpublishedEvent

from nti.externalization.interfaces import IObjectModifiedFromExternalEvent


@component.adapter(IRenderableContentPackage, IObjectPublishedEvent)
def _content_published(package, event):
    """
    When a renderable content package is published, render it.
    """
    user = get_remote_user()
    render_package(package, user)


@component.adapter(IRenderableContentPackage, IObjectModifiedFromExternalEvent)
def _content_updated(package, event):
    """
    When a persistent content library is modified, update it.
    """
    user = get_remote_user()
    # TODO: Check fields before re-rendering? New event.
    render_modified_package(package, user)


@component.adapter(IRenderableContentPackage, IObjectUnpublishedEvent)
def _content_unpublished(package, event):
    """
    When a persistent content library is unpublished, push
    it into our processing factory
    """
    # TODO: implement
