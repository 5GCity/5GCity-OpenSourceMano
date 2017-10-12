..
       # Copyright 2017 Intel Research and Development Ireland Limited
       # *************************************************************
       # This file is part of OSM Monitoring module
       # All Rights Reserved to Intel Corporation
       #
       # Licensed under the Apache License, Version 2.0 (the "License"); you may
       # not use this file except in compliance with the License. You may obtain
       # a copy of the License at
       #
       #         http://www.apache.org/licenses/LICENSE-2.0
       #
       # Unless required by applicable law or agreed to in writing, software
       # distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
       # WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
       # License for the specific language governing permissions and limitations
       # under the License.
       #
       # For those usages not covered by the Apache License, Version 2.0 please
       # contact: prithiv.mohan@intel.com or adrian.hoban@intel.com

OSM MON Module
****************

MON is a monitoring module for OSM. This module leverages the monitoring
tool of the supported VIMs through MON's native plugin to send and receive
metrics and alarms for a VNF.

Components
**********

MON module has the following components:

 - MON Core, which includes Message Bus and Models
 - Plugin drivers for various VIMs

The MON module communication is classified as

 - External to MON(requests to MON from SO)
 - Internal to MON(responses to MON from plugins)

Supported Plugins
******************

Supported VIMs are OpenStack, VMWare, AWS for now.MON can send/receive metrics
and alarms from the following plugins in this release.

 - Gnocchi, Aodh (OpenStack)
 - vrOps (VMWare)
 - CloudWatch (AWS)

Developers
**********

  - Prithiv Mohan, Intel Research and Development Ltd, Ireland
  - Helena McGough, Intel Research and Development Ltd, Ireland
  - Sachin Bhangare, VMWare, India
  - Wajeeha Hamid, XFlow Research, Pakistan

Maintainers
***********

 - Adrian Hoban, Intel Research and Development Ltd, Ireland

Contributions
*************

For information on how to contribute to OSM MON module, please get in touch with
the developer or the maintainer.

Any new code must follow the development guidelines detailed in the Dev Guidelines
in the OSM Wiki and pass all tests.

Dev Guidelines can be found at:

    [https://osm.etsi.org/wikipub/index.php/Workflow_with_OSM_tools]
