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

from docutils import nodes

from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives

from nti.app.contentlibrary_rendering.docutils.nodes import nticard


class NTICard(Directive):

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {'label': directives.unchanged,
                   'creator': directives.unchanged}

    def run(self):
        reference = directives.uri(self.arguments[0])
        self.options['uri'] = reference
        self.options['creator'] = self.options.get('creator') or 'system'
        if not self.options.get('label'):
            self.options['label'] = os.path.split(reference)[1]
        nticard_node = nticard(self.block_text, **self.options)
        if self.content:
            node = nodes.Element()  # anonymous container for parsing
            self.state.nested_parse(self.content, self.content_offset, node)
            first_node = node[0]
            if isinstance(first_node, nodes.paragraph):
                caption = nodes.caption(first_node.rawsource, '',
                                        *first_node.children)
                caption.source = first_node.source
                caption.line = first_node.line
                nticard_node += caption
            elif isinstance(first_node, nodes.comment) or len(first_node) == 0:
                raise self.error(
                    'NTICard caption must be a paragraph.',
                    nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno)

            if len(node) > 1:
                raise self.error(
                    'NTICard does not accept mulitple caption paragraphs',
                    nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno)
        return [nticard_node]


def register_directives():
    directives.register_directive("nticard", NTICard)
register_directives()

from nti.contentlibrary_rendering.docutils.interfaces import IDirectivesModule
interface.moduleProvides(IDirectivesModule)
