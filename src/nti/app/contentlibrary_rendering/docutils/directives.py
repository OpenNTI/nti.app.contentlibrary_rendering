#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os

from zope import interface

from docutils import nodes

from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives

from nti.app.contentlibrary_rendering.docutils.nodes import nticard
from nti.app.contentlibrary_rendering.docutils.nodes import ntivideo
from nti.app.contentlibrary_rendering.docutils.nodes import napollref
from nti.app.contentlibrary_rendering.docutils.nodes import nasurveyref
from nti.app.contentlibrary_rendering.docutils.nodes import ntivideoref
from nti.app.contentlibrary_rendering.docutils.nodes import naquestionref
from nti.app.contentlibrary_rendering.docutils.nodes import naassessmentref
from nti.app.contentlibrary_rendering.docutils.nodes import naassignmentref
from nti.app.contentlibrary_rendering.docutils.nodes import naquestionsetref

from nti.app.contentlibrary_rendering.docutils.utils import is_dataserver_asset
from nti.app.contentlibrary_rendering.docutils.utils import is_supported_remote_scheme

from nti.base._compat import text_

from nti.ntiids.ntiids import is_valid_ntiid_string


class TitleCaptionMixin(object):

    def process(self, asset_node, options):
        if not self.content:
            return
        node = nodes.Element()  # anonymous container for parsing
        self.state.nested_parse(self.content, self.content_offset, node)
        # title
        first_node = node[0]
        if isinstance(first_node, nodes.paragraph):
            title = text_(first_node.astext())
            options['title'] = title
        elif isinstance(first_node, nodes.comment) or len(first_node) == 0:
            raise self.error(
                'node title must be a paragraph.',
                nodes.literal_block(self.block_text, self.block_text),
                line=self.lineno)
        # caption
        caption_node = node[1] if len(node) > 1 else None
        if caption_node is not None:
            if isinstance(caption_node, nodes.paragraph):
                caption = nodes.caption(caption_node.rawsource, '',
                                        *caption_node.children)
                caption.source = caption_node.source
                caption.line = caption_node.line
                asset_node += caption
            elif isinstance(caption_node, nodes.comment) or len(caption_node) == 0:
                raise self.error(
                    'node caption must be a paragraph.',
                    nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno)
        if len(node) > 2:
            raise self.error(
                'node does not accept multiple caption paragraphs',
                nodes.literal_block(self.block_text, self.block_text),
                line=self.lineno)


class NTICard(Directive, TitleCaptionMixin):

    has_content = True
    required_arguments = 1
    optional_arguments = 4
    final_argument_whitespace = True
    option_spec = {
        'uid': directives.unchanged,
        'label': directives.unchanged,
        'title': directives.unchanged,
        'image': directives.unchanged,
        'creator': directives.unchanged
    }

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

        # create node
        nticard_node = nticard(self.block_text, **self.options)
        nticard_node['href'] = reference

        # save image href
        image = directives.uri(self.options.get('image') or u'')
        nticard_node['image'] = image

        # process caption/title
        self.process(nticard_node, self.options)
        if not self.options.get('title'):
            self.options['title'] = self.options['label']
        nticard_node['title'] = self.options['title']
        return [nticard_node]


class NTIVideo(Directive, TitleCaptionMixin):

    has_content = True
    optional_arguments = 3
    final_argument_whitespace = True
    option_spec = {
        'uid': directives.unchanged,
        'label': directives.unchanged,
        'title': directives.unchanged,
        'creator': directives.unchanged
    }

    supported_services = ('html5', 'kaltura', 'vimeo', 'youtube')

    def run(self):
        if not self.arguments:
            raise self.error('A video URL must be supplied.')
        service = directives.choice(self.arguments[0], self.supported_services)
        video_id = directives.unchanged_required(self.arguments[1])

        creator = self.options.get('creator') or 'system'
        self.options['creator'] = creator

        label = self.options.get('label') or video_id
        self.options['label'] = label

        # create node
        ntivideo_node = ntivideo(self.block_text, **self.options)
        ntivideo_node['service'] = service
        ntivideo_node['id'] = video_id

        # process caption/title
        self.process(ntivideo_node, self.options)
        if not self.options.get('title'):
            self.options['title'] = (service + ':' + video_id)
        ntivideo_node['title'] = self.options['title']
        # Need to wrap video in par node for anchoring.
        par_node = nodes.paragraph('')
        par_node.append(ntivideo_node)
        return [par_node]


class NTIVideoRef(Directive):

    has_content = False
    required_arguments = 1
    optional_arguments = 1
    option_spec = {'visibility': directives.unchanged}

    def run(self):
        ntiid = directives.unchanged_required(self.arguments[0])
        if not is_valid_ntiid_string(ntiid):
            raise self.error(
                'Error in "%s" directive: "%s" is not a valid NTIID'
                % (self.name, ntiid))
        visibility = self.options.get('visibility') or 'everyone'
        self.options['visibility'] = visibility
        node = ntivideoref(self.block_text, **self.options)
        node['ntiid'] = ntiid
        return [node]


class NTIAssessmentRef(Directive):
    
    has_content = False
    required_arguments = 1
    optional_arguments = 1
    
    factory = naassessmentref

    def run(self):
        ntiid = directives.unchanged_required(self.arguments[0])
        if not is_valid_ntiid_string(ntiid):
            raise self.error(
                'Error in "%s" directive: "%s" is not a valid NTIID'
                % (self.name, ntiid))
        node = self.factory(self.block_text, **self.options)
        node['ntiid'] = ntiid
        return [node]


class NAAssignmentRef(NTIAssessmentRef):
    factory = naassignmentref


class NAQuestionSetRef(NTIAssessmentRef):
    factory = naquestionsetref


class NAQuestionRef(NTIAssessmentRef):
    factory = naquestionref


class NAPollRef(NTIAssessmentRef):
    factory = napollref


class NASurveyRef(NTIAssessmentRef):
    factory = nasurveyref


def register_directives():
    # media
    directives.register_directive("nticard", NTICard)
    directives.register_directive("ntivideo", NTIVideo)
    directives.register_directive("ntivideoref", NTIVideoRef)
    # assessments
    directives.register_directive("napollref", NAPollRef)
    directives.register_directive("nasurveyref", NASurveyRef)
    directives.register_directive("naquestionref", NAQuestionRef)
    directives.register_directive("naassignmentref", NAAssignmentRef)
    directives.register_directive("naquestionsetref", NAQuestionSetRef)
register_directives()


from nti.contentlibrary_rendering.docutils.interfaces import IDirectivesModule
interface.moduleProvides(IDirectivesModule)
