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

from docutils import nodes as docutils_nodes

from docutils.parsers.rst import directives

from docutils.parsers.rst.directives.images import Figure

from nti.app.contentfile.view_mixins import is_oid_external_link
from nti.app.contentfile.view_mixins import get_file_from_oid_external_link

from nti.app.contentfolder.utils import is_cf_io_href
from nti.app.contentfolder.utils import get_file_from_cf_io_url

from nti.app.contentlibrary_rendering.docutils import nodes

from nti.cabinet.filer import transfer_to_native_file

COURSE_ASSETS = 'Images/CourseAssets'


def is_course_asset(uri):
    return is_cf_io_href(uri) or is_oid_external_link(uri)


def get_course_asset(uri):
    if is_cf_io_href(uri):
        return get_file_from_cf_io_url(uri)
    return get_file_from_oid_external_link(uri)


def save_to_disk(asset, out_dir=None):
    out_dir = out_dir or os.getcwd()
    name = os.path.join(COURSE_ASSETS, asset.filename)
    path = os.path.join(out_dir, name)
    transfer_to_native_file(asset, path)
    return name


class CourseAsset(Figure):

    option_spec = dict(Figure.option_spec)
    option_spec.pop('target', None)

    def run(self):
        reference = directives.uri(self.arguments[0]) or u''
        if not reference or not is_course_asset(reference):
            raise self.error(
                'Error in "%s" directive: "%s" is not a valid href value for '
                'a course asset.' % (self.name, reference))

        figwidth = self.options.pop('figwidth', None)
        if figwidth == 'image':
            raise self.error(
                'Error in "%s" directive: image is not a valid value for '
                'the "figwidth" option.' % self.name)

        asset = get_course_asset(reference)
        if asset is None:
            raise self.error(
                'Error in "%s" directive: course asset "%" is missing'
                % (self.name, reference))

        (figure_node,) = Figure.run(self)
        if isinstance(figure_node, docutils_nodes.system_message):
            return [figure_node]

        course_asset_node = nodes.course_asset('', figure_node)
        # when this directive runs the we assume the directory to save the resource
        # has been set
        course_asset_node['uri'] = save_to_disk(asset)
        return [course_asset_node]


def register_directives():
    directives.register_directive("course-asset", CourseAsset)

from nti.contentlibrary_rendering.docutils.interfaces import IDirectivesModule
interface.moduleProvides(IDirectivesModule)
