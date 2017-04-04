#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import shutil
import tempfile

from zope import component
from zope import interface

from zope.location.interfaces import IContained

from z3c.autoinclude.zcml import includePluginsDirective

from nti.async.interfaces import IReactorStarted
from nti.async.interfaces import IReactorStopped

from nti.async.utils.processor import Processor

from nti.contentlibrary_rendering import QUEUE_NAMES

from nti.contentrendering.utils.chameleon import setupChameleonCache

from nti.dataserver.utils.base_script import create_context


@interface.implementer(IContained)
class PluginPoint(object):

    __parent__ = None

    def __init__(self, name):
        self.__name__ = name

PP_CONTENT_RENDERING = PluginPoint('nti.contentrendering')


@component.adapter(IReactorStarted)
def reactor_started(context):
    cache_dir = tempfile.mkdtemp(prefix="chameleon_cache_")
    context.cache_dir = os.environ['CHAMELEON_CACHE'] = cache_dir
    setupChameleonCache(True, cache_dir)


@component.adapter(IReactorStopped)
def reactor_stopped(context):
    try:
        shutil.rmtree(context.cache_dir, ignore_errors=True)
    except AttributeError:
        pass


class Constructor(Processor):

    def set_log_formatter(self, args):
        super(Constructor, self).set_log_formatter(args)

    def extend_context(self, context):
        includePluginsDirective(context, PP_CONTENT_RENDERING)

    def create_context(self, env_dir, args=None):
        context = create_context(env_dir,
                                 with_library=True,
                                 plugins=True,
                                 slugs=True,
                                 slugs_files=("*content_render.zcml", "*features.zcml"))
        self.extend_context(context)
        return context

    def conf_packages(self):
        return (self.conf_package, 'nti.contentlibrary', 'nti.async')

    def process_args(self, args):
        setattr(args, 'redis', True)
        setattr(args, 'library', True)
        setattr(args, 'priority', True)
        setattr(args, 'trx_retries', 9)
        setattr(args, 'queue_names', QUEUE_NAMES)
        component.getGlobalSiteManager().registerHandler(reactor_started)
        component.getGlobalSiteManager().registerHandler(reactor_stopped)
        Processor.process_args(self, args)


def main():
    return Constructor()()

if __name__ == '__main__':
    main()
