..
       # Copyright 2017 Intel Research and Development Ireland Limited
       # *************************************************************
       # This file is part of OSM Monitoring module
       # All Rights Reserved to Intel Corporation
       #
       # Licensed under the Apache License, Version 2.0 (the "License"); you
       # may not use this file except in compliance with the License. You may
       # obtain a copy of the License at
       #
       #         http://www.apache.org/licenses/LICENSE-2.0
       #
       # Unless required by applicable law or agreed to in writing, software
       # distributed under the License is distributed on an "AS IS" BASIS,
       # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
       # implied. See the License for the specific language governing
       # permissions and limitations under the License.
       #
       # For those usages not covered by the Apache License, Version 2.0 please
       # contact: helena.mcgough@intel.com or adrian.hoban@intel.com

OpenStack Plugin Guide
**********************
The OSM MON module provides support for two different OpenStack plugins that
provide monitoring functionality. The Gnocchi plugin implements metric
functionality, whilst the Aodh plugin supports alarming functionality.

Gnocchi
-------
Gnocchi is a timeseries, metrics and resources database, which allows you to
store and access the information and history of resources and their metrics.

For more information on Gnocchi please refer to the source code/documentation:

    ::

        https://github.com/gnocchixyz/gnocchi

For plugin specific instructions and configuration options please refer to the
following guide:
: `<doc/plugins/OpenStack/gnocchi_plugin_guide.rst>`

Aodh
----
Aodh is OpenStack's alarming project, it enables alarms to be created based on
Gnocchi metrics. Rules can be defined for these metrics to create these alarms.

For more information on this project please refer to the source
code/documentation:

    ::

        https://github.com/openstack/aodh

For plugin specific instructions and configuration options please refer to the
following guide:
: `<doc/plugins/OpenStack/aodh_plugin_guide.rst>`
