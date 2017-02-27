#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os

from zope import interface

from nti.app.contentlibrary_rendering.docutils.utils import is_dataserver_asset
from nti.app.contentlibrary_rendering.docutils.utils import get_dataserver_asset
from nti.app.contentlibrary_rendering.docutils.utils import save_to_course_assets
from nti.app.contentlibrary_rendering.docutils.utils import is_supported_remote_scheme

from nti.base._compat import unicode_

from nti.contentlibrary_rendering.docutils.translators import TranslatorMixin

from nti.contentlibrary_rendering.docutils.interfaces import IRSTToPlastexNodeTranslator

from nti.contentrendering.plastexpackages.nticard import nticard
from nti.contentrendering.plastexpackages.nticard import process_image_data
from nti.contentrendering.plastexpackages.nticard import process_remote_image
from nti.contentrendering.plastexpackages.nticard import incoming_sources_as_plain_text


def get_asset(href):
    return get_dataserver_asset(href)


def is_href_a_dataserver_asset(href):
    return is_dataserver_asset(href)


def is_image_a_dataserver_asset(image):
    return is_dataserver_asset(image)


@interface.implementer(IRSTToPlastexNodeTranslator)
class NTICardToPlastexNodeTranslator(TranslatorMixin):

    __name__ = "nticard"

    def process_reference(self, rst_node, nticard):
        original = href = rst_node['href']
        if is_href_a_dataserver_asset(href):
            # download asset and validate
            asset = get_asset(href)
            if asset is None:
                raise ValueError(
                    'Error in "%s" directive: asset "%" is missing'
                    % (self.__name__, href))
            # save to local disk
            href = save_to_course_assets(asset)
        # set href to auto-populate field
        nticard.href = href
        nticard.setAttribute('href', href)
        nticard.setAttribute('nti-requirements', None)
        # populate data from remote or local
        if not nticard.proces_local_href():
            nticard.auto_populate()
        # restore orinal href since dataserve r
        # may serve content
        nticard.href = original
        nticard.setAttribute('href', original)
        # clean up
        if original != href:
            os.remove(href)

    def process_image(self, rst_node, nticard):
        image = rst_node['image']
        if is_image_a_dataserver_asset(image):
            # download asset and validate
            asset = get_asset(image)
            if asset is None:
                raise ValueError(
                    'Error in "%s" directive: asset "%" is missing'
                    % (self.__name__, image))
            # save to local disk
            local = save_to_course_assets(asset)
            # get image info
            with open(local, "rb") as fp:
                process_image_data(nticard,
                                   url=image,
                                   data=fp.read())
            # clean up
            os.remove(local)
        else:
            if not is_supported_remote_scheme(image):
                raise ValueError(
                    'Error in "%s" directive: "%s" is not a supported uri'
                    % (self.__name__, image))
            process_remote_image(nticard, image)
            
    def do_translate(self, rst_node, tex_doc, tex_parent):
        # create and set ownership early
        result = nticard()
        result.ownerDocument = tex_doc

        # process reference/href content
        self.process_reference(rst_node, result)

        # populate missing properties
        if not result.title:
            result.title = rst_node.attributes['title']
        if not result.creator:
            result.creator = rst_node.attributes['creator']
        result.id = rst_node.attributes['label']

        # process image
        if rst_node['image']:
            self.process_image(rst_node, result)

        # process caption /description
        if rst_node.children:
            par = rst_node.children[0]
            text = unicode_(par.astext())
            description = incoming_sources_as_plain_text([text])
            result.description = description

        # target ntiid
        result.process_target_ntiid()
        return result
