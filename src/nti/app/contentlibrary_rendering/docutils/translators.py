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

from nti.app.contentlibrary_rendering.docutils.utils import process_rst_image
from nti.app.contentlibrary_rendering.docutils.utils import is_dataserver_asset
from nti.app.contentlibrary_rendering.docutils.utils import get_dataserver_asset
from nti.app.contentlibrary_rendering.docutils.utils import save_to_course_assets
from nti.app.contentlibrary_rendering.docutils.utils import is_supported_remote_scheme

from nti.assessment.interfaces import IQPoll
from nti.assessment.interfaces import IQSurvey
from nti.assessment.interfaces import IQuestion
from nti.assessment.interfaces import IQAssignment
from nti.assessment.interfaces import IQEvaluation
from nti.assessment.interfaces import IQuestionSet

from nti.base._compat import text_

from nti.contentlibrary_rendering.docutils.translators import TranslatorMixin

from nti.contentlibrary_rendering.docutils.interfaces import IRSTToPlastexNodeTranslator

from nti.contentrendering.plastexpackages.nticard import nticard
from nti.contentrendering.plastexpackages.nticard import process_image_data
from nti.contentrendering.plastexpackages.nticard import process_remote_image
from nti.contentrendering.plastexpackages.nticard import incoming_sources_as_plain_text

from nti.contentrendering.plastexpackages.ntimedia import ntivideo
from nti.contentrendering.plastexpackages.ntimedia import ntivideoref

from nti.contentrendering_assessment.ntiassessment import napollref
from nti.contentrendering_assessment.ntiassessment import nasurveyref
from nti.contentrendering_assessment.ntiassessment import naquestionref
from nti.contentrendering_assessment.ntiassessment import naassesmentref
from nti.contentrendering_assessment.ntiassessment import naassignmentref
from nti.contentrendering_assessment.ntiassessment import naquestionsetref

from nti.contenttypes.presentation.interfaces import INTIVideo

from nti.ntiids.ntiids import find_object_with_ntiid


# image


@interface.implementer(IRSTToPlastexNodeTranslator)
class ImageToPlastexNodeTranslator(TranslatorMixin):

    __name__ = "image"

    def process_resource(self, rst_node):
        uri = rst_node['uri']
        if not is_supported_remote_scheme(uri):
            if not os.path.exists(uri):
                raise ValueError(
                    'Error in "%s" directive: asset "%" is missing'
                    % (self.__name__, uri))
            # save locally
            with open(uri, "rb") as fp:
                uri = save_to_course_assets(fp)
            rst_node['uri'] = uri
        return rst_node

    def do_translate(self, rst_node, tex_doc, tex_parent):
        result = process_rst_image(self.process_resource(rst_node), tex_doc)
        return result


# nticard


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
            text = text_(par.astext())
            description = incoming_sources_as_plain_text([text])
            result.description = description

        # target ntiid
        result.process_target_ntiid()
        return result


# ntivideo


@interface.implementer(IRSTToPlastexNodeTranslator)
class NTIVideoToPlastexNodeTranslator(TranslatorMixin):

    __name__ = "ntivideo"

    def do_translate(self, rst_node, tex_doc, tex_parent):
        result = ntivideo()
        result.ownerDocument = tex_doc
        source = ntivideo.ntivideosource()
        source.attributes.update({
            'id': rst_node['id'],
            'service': rst_node['service']
        })
        result.append(source)
        source.process_options()

        result.label = rst_node.attributes['label']
        result.title = rst_node.attributes['title']
        result.creator = rst_node.attributes['creator']
        result.id = 'video_%s' % tex_doc.px_inc_media_counter()

        # process caption /description
        if rst_node.children:
            par = rst_node.children[0]
            text = text_(par.astext())
            description = incoming_sources_as_plain_text([text])
            result.description = description
        else:
            text = text_(result.title)
            description = incoming_sources_as_plain_text([text])
        result.description = description
        return result


@interface.implementer(IRSTToPlastexNodeTranslator)
class NTIVideoRefToPlastexNodeTranslator(TranslatorMixin):

    __name__ = "ntivideoref"

    def do_translate(self, rst_node, tex_doc, tex_parent):
        ntiid = rst_node['ntiid']
        video = find_object_with_ntiid(ntiid)
        if not INTIVideo.providedBy(video):
            raise ValueError(
                'Error in "%s" directive: video with ntiid "%" is missing'
                % (self.__name__, ntiid))

        result = ntivideoref()
        result.media = video
        result.poster = None
        result.to_render = False
        result.visibility = rst_node.attributes['visibility']
        return result


# Assessments


@interface.implementer(IRSTToPlastexNodeTranslator)
class NAAssessmentRefToPlastexNodeTranslator(TranslatorMixin):

    __name__ = "naassessmentref"

    provided = IQEvaluation
    factory = naassesmentref

    def do_translate(self, rst_node, tex_doc, tex_parent):
        ntiid = rst_node['ntiid']
        item = find_object_with_ntiid(ntiid)
        if not self._provided.providedBy(item):
            raise ValueError(
                'Error in "%s" directive: evaluation with ntiid "%" is missing'
                % (self.__name__, ntiid))

        result = self.factory()
        result.assesment = item
        result.to_render = False
        return result


@interface.implementer(IRSTToPlastexNodeTranslator)
class NAQuestionRefToPlastexNodeTranslator(NAAssessmentRefToPlastexNodeTranslator):

    __name__ = "naquestionref"

    provided = IQuestion
    factory = naquestionref


@interface.implementer(IRSTToPlastexNodeTranslator)
class NAQuestionSetRefToPlastexNodeTranslator(NAAssessmentRefToPlastexNodeTranslator):

    __name__ = "naquestionsetref"

    provided = IQuestionSet
    factory = naquestionsetref


@interface.implementer(IRSTToPlastexNodeTranslator)
class NAAssignmentRefToPlastexNodeTranslator(NAAssessmentRefToPlastexNodeTranslator):

    __name__ = "naassignmentref"

    provided = IQAssignment
    factory = naassignmentref


@interface.implementer(IRSTToPlastexNodeTranslator)
class NAPollRefToPlastexNodeTranslator(NAAssessmentRefToPlastexNodeTranslator):

    __name__ = "napollref"

    provided = IQPoll
    factory = napollref


@interface.implementer(IRSTToPlastexNodeTranslator)
class NASurveyRefToPlastexNodeTranslator(NAAssessmentRefToPlastexNodeTranslator):

    __name__ = "nasurveyref"

    provided = IQSurvey
    factory = nasurveyref
