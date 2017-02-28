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
from nti.app.contentlibrary_rendering.docutils.nodes import ntivideo
from nti.app.contentlibrary_rendering.docutils.nodes import ntivideoref

from nti.app.contentlibrary_rendering.docutils.utils import is_dataserver_asset
from nti.app.contentlibrary_rendering.docutils.utils import is_supported_remote_scheme

from nti.ntiids.ntiids import is_valid_ntiid_string


class NTICard(Directive):

    has_content = True
    required_arguments = 1
    optional_arguments = 4
    final_argument_whitespace = True
    option_spec = {'label': directives.unchanged,
                   'title': directives.unchanged,
                   'image': directives.unchanged,
                   'creator': directives.unchanged}

    def run(self):
        # validate reference/href value
        reference = directives.uri(self.arguments[0])
        if      not is_dataserver_asset(reference) \
            and not is_supported_remote_scheme(reference):
            raise self.error(
                'Error in "%s" directive: "%s" is not a supported uri'
                % (self.name, reference))

        # set default values for options
        self.options['href'] = reference
        self.options['creator'] = self.options.get('creator') or 'system'
        if not self.options.get('label'):
            label = os.path.split(reference)[1]
            self.options['label'] = 'nticard_%s' % label
        if not self.options.get('title'):
            self.options['title'] = self.options['label']

        # create node
        nticard_node = nticard(self.block_text, **self.options)
        nticard_node['href'] = reference

        # save image href
        image = directives.uri(self.options.get('image') or u'')
        nticard_node['image'] = image

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


class NTIVideo(Directive):

    has_content = True
    required_arguments = 2
    optional_arguments = 3
    final_argument_whitespace = True
    option_spec = {'label': directives.unchanged,
                   'title': directives.unchanged,
                   'creator': directives.unchanged}

    supported_services = ('html5', 'kaltura', 'vimeo', 'youtube')

    def run(self):
        service = directives.choice(self.arguments[0], self.supported_services)
        video_id = directives.unchanged_required(self.arguments[1])

        title = self.options.get('title') or (service + ':' + video_id)
        self.options['title'] = title

        creator = self.options.get('creator') or 'system'
        self.options['creator'] = creator

        label = self.options.get('label') or video_id
        self.options['label'] = label

        # create node
        ntivideo_node = ntivideo(self.block_text, **self.options)
        ntivideo_node['service'] = service
        ntivideo_node['id'] = video_id
            
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
                ntivideo_node += caption
            elif isinstance(first_node, nodes.comment) or len(first_node) == 0:
                raise self.error(
                    'ntivideo caption must be a paragraph.',
                    nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno)

            if len(node) > 1:
                raise self.error(
                    'ntivideo does not accept mulitple caption paragraphs',
                    nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno)
        return [ntivideo_node]


class NTIVideoRef(Directive):

    has_content = False
    required_arguments = 1

    def run(self):
        ntiid = directives.unchanged_required(self.arguments[0])
        if not is_valid_ntiid_string(ntiid):
            raise self.error(
                'Error in "%s" directive: "%s" is not a valid NTIID'
                % (self.name, ntiid))
        node = ntivideoref('', **self.options)
        node['ntiid'] = ntiid
        return [node]


def register_directives():
    directives.register_directive("nticard", NTICard)
    directives.register_directive("ntivideo", NTIVideo)
    directives.register_directive("ntivideoref", NTIVideoRef)
register_directives()


from nti.contentlibrary_rendering.docutils.interfaces import IDirectivesModule
interface.moduleProvides(IDirectivesModule)
