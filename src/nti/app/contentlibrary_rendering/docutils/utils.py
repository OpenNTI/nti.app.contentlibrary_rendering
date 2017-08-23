#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
from urlparse import urlparse

from zope import component

from zope.annotation.interfaces import IAnnotations

from zope.component.hooks import getSite

from nti.app.contentfile.view_mixins import is_oid_external_link
from nti.app.contentfile.view_mixins import get_file_from_oid_external_link

from nti.app.contentfolder.utils import is_cf_io_href
from nti.app.contentfolder.utils import get_file_from_cf_io_url

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.base._compat import text_

from nti.cabinet.filer import transfer_to_native_file

from nti.contentlibrary import NTI

from nti.contentrendering.plastexpackages.ntiexternalgraphics import ntiexternalgraphics

from nti.contentrendering.plastexpackages.ntilatexmacros import ntiincludeannotationgraphics

from nti.contenttypes.presentation import NTI_VIDEO

from nti.ntiids.ntiids import make_ntiid
from nti.ntiids.ntiids import make_specific_safe


#: Content package course assets relative directory
COURSE_ASSETS = 'Images/CourseAssets'


def is_supported_remote_scheme(uri):
    comps = urlparse(uri)
    return comps.scheme in ('http', 'https')


def is_dataserver_asset(uri):
    return is_cf_io_href(uri) or is_oid_external_link(uri)


def get_dataserver_asset(uri):
    if is_cf_io_href(uri):
        return get_file_from_cf_io_url(uri)
    return get_file_from_oid_external_link(uri)


def get_filename(asset):
    out_name = getattr(asset, 'filename', None) \
            or getattr(asset, 'name', None) \
            or str(asset)
    out_name = os.path.split(out_name)[1]
    return out_name


def save_to_disk(asset, out_dir=None):
    out_dir = out_dir or os.getcwd()
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    out_name = get_filename(asset)
    path = os.path.join(out_dir, out_name)
    transfer_to_native_file(asset, path)
    return path


def save_to_course_assets(asset, out_dir=None):
    out_dir = out_dir or os.getcwd()
    out_dir = os.path.join(out_dir, COURSE_ASSETS)
    save_to_disk(asset, out_dir)
    out_name = get_filename(asset)
    result = os.path.join(COURSE_ASSETS, out_name)
    return result


def process_rst_image(rst_node, tex_doc, parent=None):
    options = dict()
    uri = rst_node['uri']
    remote = is_supported_remote_scheme(uri) or is_dataserver_asset(uri)
    if not remote:
        grphx = ntiincludeannotationgraphics()
        grphx.setAttribute('file', uri)
    else:
        grphx = ntiexternalgraphics()
        grphx.setAttribute('url', uri)
    # Must set the source to avoid duplicate mappings
    grphx.argSource = r'%s{%s}' % (grphx.source, uri)
    grphx.setAttribute('options', options)

    # alternative text settings
    value = rst_node.attributes.get('alt', None)
    if value:  # alttext
        grphx.setAttribute('alttext', value)

    # image size
    value = rst_node.attributes.get('size', None)
    if value:
        options['size'] = value

    # stlye & dimension settings
    value = rst_node.attributes.get('style', None)
    if not value:
        value = rst_node.attributes.get('scale', None)
        if value:
            options['scale'] = value if value <= 1 else value / 100.0

        for name in ('height', 'width'):
            value = rst_node.attributes.get(name, None)
            if value:
                options[name] = value
    else:
        options['style'] = value

    # add to set lineage
    if parent is not None:
        parent.append(grphx)
    else:
        grphx.ownerDocument = tex_doc

    # process image and return
    if not remote:
        grphx.process_image()
    else:
        grphx.process_options()
    return grphx


def process_rst_figure(rst_node, tex_doc, figure=None):
    figure = figure or tex_doc.createElement('figure')
    grphx = process_rst_image(rst_node, tex_doc, figure)
    # set alttext on figure
    value = rst_node.attributes.get('alt', None)
    if value:
        figure.setAttribute('title', value)
    return [figure, grphx]


# ntiids


def get_provider():
    policy = component.queryUtility(ISitePolicyUserEventListener)
    result = getattr(policy, 'PROVIDER', None)
    if not result:
        annontations = IAnnotations(getSite(), {})
        result = annontations.get('PROVIDER')
    return result or NTI


def make_asset_ntiid(nttype, uid):
    specific = make_specific_safe(text_(uid).upper())
    provider = get_provider()
    return make_ntiid(nttype=nttype, 
                      provider=provider, 
                      specific=specific)


def make_video_ntiid(uid):
    return make_asset_ntiid(NTI_VIDEO, uid)
