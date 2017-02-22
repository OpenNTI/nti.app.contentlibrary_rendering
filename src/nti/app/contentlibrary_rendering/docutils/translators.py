#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from docutils.nodes import TextElement

from nti.base._compat import unicode_

from nti.contentlibrary_rendering.docutils.translators import TranslatorMixin

from nti.contentlibrary_rendering.docutils.interfaces import IRSTToPlastexNodeTranslator

from nti.contentrendering.plastexpackages.graphicx import includegraphics

from nti.contentrendering.plastexpackages.ntilatexmacros import nticard
from nti.contentrendering.plastexpackages.ntilatexmacros import incoming_sources_as_plain_text


@interface.implementer(IRSTToPlastexNodeTranslator)
class NTICardToPlastexNodeTranslator(TranslatorMixin):

    __name__ = "nticard"

    def do_translate(self, rst_node, tex_doc, tex_parent):
        result = nticard()
        # save href as property and attribute
        result.href = rst_node['href']
        result.setAttribute('href', rst_node['href'])
        result.setAttribute('nti-requirements', None)

        # check if the href points to a local file
        if not result.proces_local_href():
            result.auto_populate()

        # populae missing properties
        if not result.title:
            result.title = rst_node.attributes['title']
        if not result.creator:
            result.title = rst_node.attributes['creator']
        result.id = rst_node.attributes['label']

        # process image
        if result.image is None and rst_node['image']:
            image = includegraphics()
            image.setAttribute('file', rst_node['image'])
            image.process_image()
            result.append(image)  # Add it for BWC
            result.image = image

        # process caption /description
        if rst_node.children:
            texts = []
            par = rst_node.children[0]
            texts.append(unicode_(par.as_text()))
            for node in par.children or ():
                if isinstance(node, TextElement):
                    texts.append(unicode_(par.as_text()))

            description = incoming_sources_as_plain_text(texts)
            result.description = description

        # process label
        
        return result
