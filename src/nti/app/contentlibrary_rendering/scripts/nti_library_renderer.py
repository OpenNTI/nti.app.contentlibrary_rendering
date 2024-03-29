#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import shutil
import tempfile

from z3c.autoinclude.zcml import includePluginsDirective

from zope import component
from zope import interface

from zope.location.interfaces import IContained

from nti.app.asynchronous.processor import Processor

from nti.asynchronous.interfaces import IReactorStarted
from nti.asynchronous.interfaces import IReactorStopped

from nti.contentlibrary_rendering import QUEUE_NAMES

from nti.contentrendering.utils.chameleon import setupChameleonCache

from nti.dataserver.utils.base_script import create_context

logger = __import__('logging').getLogger(__name__)


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

    def extend_context(self, context):
        includePluginsDirective(context, PP_CONTENT_RENDERING)

    def create_context(self, env_dir, unused_args=None):
        context = create_context(env_dir,
                                 with_library=True,
                                 plugins=True,
                                 slugs=True)
        self.extend_context(context)
        return context

    def conf_packages(self):
        return (self.conf_package, 'nti.contentlibrary', 'nti.asynchronous')

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
