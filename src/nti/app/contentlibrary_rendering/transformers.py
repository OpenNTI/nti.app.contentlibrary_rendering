#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from plasTeX import TeXDocument

from plasTeX.Logging import getLogger
logger = getLogger(__name__)

from zope import interface

from nti.contentlibrary_rendering.interfaces import IRSTToPlastexDocumentTranslator

def _convert_node(node, tex_doc):
    if node.tagname == 'document':
        result = tex_doc.createElement(node.tagname)
        # This should always have a title right...?
        title = tex_doc.createTextNode(node.attributes['title'])
        # The document root (and sections?) will need a title
        # element.
        result.setAttribute('title', title)
    elif node.tagname == '#text':
        result = tex_doc.createTextNode(node.astext())
    elif node.tagname == 'section':
        # If we have sections, we'll need titles per section.
        result = None
        #result = tex_doc.createElement(node.tagname)
    elif node.tagname in ('image', 'math'):
        # FIXME:
        result = None
    elif node.tagname == 'paragraph':
        result = tex_doc.createElement('par')
    elif node.tagname == 'subtitle':
        # XXX: Do we want a new section here?
        result = tex_doc.createElement('section')
        names = node.attributes.get( 'names' )
        if names:
            title = names[0]
        else:
            title = node.astext()
        title = tex_doc.createTextNode(title)
        result.setAttribute('title', title)
    else:
        result = tex_doc.createElement(node.tagname)

    if node.tagname == 'title':
        title_text = tex_doc.createTextNode(node.astext())
        result.append( title_text )
    return result

@interface.implementer(IRSTToPlastexDocumentTranslator)
class RSTToPlastexDocumentTranslator(object):
    """
    Transforms an RST textual source into a plasTeX dom.
    """

    def _handle_node(self, rst_node, tex_parent, tex_doc):
        tex_node = _convert_node(rst_node, tex_doc)
        if tex_node is not None:
            tex_parent.append(tex_node)
        # If no-op, keep parsing but do so for our tex_parent.
        # XXX: Is this what we want?
        if tex_node is None:
            tex_node = tex_parent
        return tex_node

    def build_nodes(self, rst_parent, tex_parent, tex_doc):
        tex_node = self._handle_node(rst_parent, tex_parent, tex_doc)
        for rst_child in rst_parent.children or ():
            self.build_nodes(rst_child, tex_node, tex_doc)

    def translate(self, rst_document, tex_doc=None):
        # XXX: By default, we skip any preamble and start directly in the
        # default. docutils stores the title info in the preamble.
        document = TeXDocument() if tex_doc is None else tex_doc
        self.build_nodes(rst_document, document, document)
        return document
