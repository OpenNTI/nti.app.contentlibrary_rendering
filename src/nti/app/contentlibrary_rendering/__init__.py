#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.app.contentlibrary import LIBRARY_ADAPTER

#: Fetch the latest render job
VIEW_QUERY_JOB = 'QueryRenderJob'

#: Render jobs
VIEW_RENDER_JOBS = 'RenderJobs'

#: Fetch the error of a library render job
VIEW_LIB_JOB_ERROR = 'RenderJobError'

#: Fetch the status of a library render job
VIEW_LIB_JOB_STATUS = 'RenderJobStatus'

#: The amount of time for which we will hold the lock during location
LOCK_TIMEOUT = 5 * 60  # 5 minutes
