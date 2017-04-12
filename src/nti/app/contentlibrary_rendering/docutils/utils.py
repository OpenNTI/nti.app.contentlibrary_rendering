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

from zope.security.management import system_user

from nti.app.contentfile.view_mixins import is_oid_external_link
from nti.app.contentfile.view_mixins import get_file_from_oid_external_link

from nti.app.contentfolder.utils import is_cf_io_href
from nti.app.contentfolder.utils import get_file_from_cf_io_url

from nti.cabinet.filer import transfer_to_native_file

from nti.contentrendering.plastexpackages.ntiexternalgraphics import ntiexternalgraphics

from nti.contentrendering.plastexpackages.ntilatexmacros import ntiincludeannotationgraphics

from nti.coremetadata.utils import current_principal

from nti.dataserver.authorization import ACT_READ

from nti.dataserver.authorization_acl import has_permission


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


def has_access(context, permission=ACT_READ):
    principal = current_principal(False)
    if principal is None or principal.id == system_user.id:
        return True
    return has_permission(permission, context, principal.id)


def process_rst_image(rst_node, tex_doc, parent=None):
    uri = rst_node['uri']
    options = dict()
    if not is_supported_remote_scheme(uri):
        grphx = ntiincludeannotationgraphics()
        grphx.setAttribute('file', uri)
    else:
        grphx = ntiexternalgraphics()
        grphx.setAttribute('url', uri)
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
    if not is_supported_remote_scheme(uri):
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
