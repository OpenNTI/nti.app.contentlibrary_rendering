#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from urlparse import urlparse

from zope import interface

from nti.app.contentlibrary_rendering.docutils.utils import is_dataserver_asset
from nti.app.contentlibrary_rendering.docutils.utils import get_dataserver_asset
from nti.app.contentlibrary_rendering.docutils.utils import save_to_course_assets

from nti.base._compat import unicode_

from nti.contentlibrary_rendering.docutils.translators import TranslatorMixin

from nti.contentlibrary_rendering.docutils.interfaces import IRSTToPlastexNodeTranslator

from nti.contentrendering.plastexpackages.graphicx import includegraphics

from nti.contentrendering.plastexpackages.ntilatexmacros import nticard
from nti.contentrendering.plastexpackages.ntilatexmacros import incoming_sources_as_plain_text

from nti.externalization.proxy import removeAllProxies

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
        href = rst_node['href']
        if is_href_a_dataserver_asset(href):
            asset = get_asset(href)
            if asset is None:
                raise ValueError(
                    'Error in "%s" directive: asset "%" is missing'
                    % (self.__name__, href))
            href = save_to_course_assets(asset)
        nticard.href = href
        nticard.setAttribute('href', href)
        nticard.setAttribute('nti-requirements', None)
        # check if the href points to a local file
        if not nticard.proces_local_href():
            nticard.auto_populate()

    def process_image(self, rst_node, nticard):
        image = rst_node['image']
        if image:
            if is_image_a_dataserver_asset(image):
                asset = get_asset(image)
                if asset is None:
                    raise ValueError(
                        'Error in "%s" directive: asset "%" is missing'
                        % (self.__name__, image))
                image = save_to_course_assets(asset)

                result = includegraphics()
                result.setAttribute('file', image)
                result.setAttribute('options', None)
                nticard.append(result)  # Add it for BWC
                nticard.image = result
                result.process_image()
            else:
                comps = urlparse(image)
                if comps.scheme not in ('http', 'https', 'file'):
                    raise ValueError(
                        'Error in "%s" directive: "%s" is not a supported uri'
                        % (self.name, image))

    def do_translate(self, rst_node, tex_doc, tex_parent):
        # create and set ownership early
        result = nticard()
        result.ownerDocument = removeAllProxies(tex_doc)

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
