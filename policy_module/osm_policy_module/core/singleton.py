# -*- coding: utf-8 -*-

# Copyright 2018 Whitestack, LLC
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Whitestack, LLC

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at

#         http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# For those usages not covered by the Apache License, Version 2.0 please
# contact: bdiaz@whitestack.com or glavado@whitestack.com
##"""Simple singleton class."""

from __future__ import unicode_literals


class Singleton(object):
    """Simple singleton class."""

    def __init__(self, decorated):
        """Initialize singleton instance."""
        self._decorated = decorated

    def instance(self):
        """Return singleton instance."""
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance
