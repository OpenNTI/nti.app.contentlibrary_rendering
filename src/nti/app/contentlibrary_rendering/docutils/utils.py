#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os

from nti.app.contentfile.view_mixins import is_oid_external_link
from nti.app.contentfile.view_mixins import get_file_from_oid_external_link

from nti.app.contentfolder.utils import is_cf_io_href
from nti.app.contentfolder.utils import get_file_from_cf_io_url

from nti.cabinet.filer import transfer_to_native_file

from nti.contentrendering.plastexpackages.ntilatexmacros import ntiincludeannotationgraphics


#: Content package course assets relative directory
COURSE_ASSETS = 'Images/CourseAssets'


def is_dataserver_asset(uri):
    return is_cf_io_href(uri) or is_oid_external_link(uri)


def get_dataserver_asset(uri):
    if is_cf_io_href(uri):
        return get_file_from_cf_io_url(uri)
    return get_file_from_oid_external_link(uri)


def save_to_disk(asset, out_dir=None):
    out_dir = out_dir or os.getcwd()
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    path = os.path.join(out_dir, asset.filename)
    transfer_to_native_file(asset, path)
    return path


def save_to_course_assets(asset, out_dir=None):
    out_dir = out_dir or os.getcwd()
    out_dir = os.path.join(out_dir, COURSE_ASSETS)
    save_to_disk(asset, out_dir)
    result = os.path.join(COURSE_ASSETS, asset.filename)
    return result


def process_rst_figure(self, rst_node, tex_doc):
    result = tex_doc.createElement('figure')

    # attribute settings
    options = dict()
    grphx = ntiincludeannotationgraphics()
    grphx.setAttribute('file', rst_node['uri'])
    grphx.setAttribute('options', options)

    # alternative text settings
    value = rst_node.attributes.get('alt', None)
    if value:  # alttext
        grphx.setAttribute('alttext', value)
        result.setAttribute('title', value)

    # dimension settings
    value = rst_node.attributes.get('scale', None)
    if value:
        options['scale'] = value if value <= 1 else value / 100.0
    else:
        for name in ('height', 'width'):
            value = rst_node.attributes.get(name, None)
            if value:
                try:
                    float(value)  # unitless
                    options[name] = '%spx' % (value)
                except (ValueError):
                    options[name] = value

    # add to set lineage
    result.append(grphx)

    # process image and return
    grphx.process_image()
    return [result, grphx]
