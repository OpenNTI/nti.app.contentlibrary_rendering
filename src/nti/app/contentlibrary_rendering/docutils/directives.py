#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
from urlparse import urlparse

from zope import interface

from docutils import nodes

from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives

from nti.app.contentlibrary_rendering.docutils.nodes import nticard

from nti.app.contentlibrary_rendering.docutils.utils import is_dataserver_asset


class NTICard(Directive):

    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {'label': directives.unchanged,
                   'title': directives.unchanged,
                   'image': directives.unchanged,
                   'creator': directives.unchanged}

    def run(self):
        reference = directives.uri(self.arguments[0])
        if not is_dataserver_asset(reference):
            comps = urlparse(reference)
            if comps.scheme not in ('http', 'https'):
                raise self.error(
                    'Error in "%s" directive: "%s" is not a supported uri'
                    % (self.name, reference))

        # set values for options
        self.options['href'] = reference
        if not self.options.get('creator'):
            self.options['creator'] = 'system'
        if not self.options.get('label'):
            label = os.path.split(reference)[1]
            self.options['label'] = 'nticard_%s' % label
        if not self.options.get('title'):
            self.options['title'] = self.options['label']

        # create node
        image = directives.uri(self.options.get('image') or u'')
        nticard_node = nticard(self.block_text, **self.options)
        nticard_node['image'] = image
        nticard_node['href'] = reference

        # process caption
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
                    'nticard caption must be a paragraph.',
                    nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno)

            if len(node) > 1:
                raise self.error(
                    'nticard does not accept mulitple caption paragraphs',
                    nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno)
        return [nticard_node]


def register_directives():
    directives.register_directive("nticard", NTICard)
register_directives()

from nti.contentlibrary_rendering.docutils.interfaces import IDirectivesModule
interface.moduleProvides(IDirectivesModule)
