#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import has_key
from hamcrest import assert_that

from nti.app.contentlibrary_rendering.tests import ContentlibraryRenderingLayerTest

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans


class TestFunctionalInstall(ContentlibraryRenderingLayerTest):

    @WithMockDSTrans
    def test_installed(self):
        conn = mock_dataserver.current_transaction
        root = conn.root()
        generations = root['zope.generations']
        assert_that(generations, has_key('nti.dataserver-app-contentlibrary-rendering'))
