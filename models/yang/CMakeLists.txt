# 
#   Copyright 2016 RIFT.IO Inc
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# Author(s): Anil Gunturu
# Creation Date: 10/15/2014
# 

# NOTE: These files will be used by the new MANO subsystem
set(source_yang_files
  ietf-l2-topology.yang
  ietf-network-topology.yang
  ietf-network.yang
  nsd.yang rw-nsd.yang
  nsr.yang rw-nsr.yang
  pnfd.yang
  rw-topology.yang
  vlr.yang rw-vlr.yang
  vnfd.yang rw-vnfd.yang
  vnfr.yang rw-vnfr.yang
  )

rift_add_yang_target(
  TARGET mano-types_yang
  YANG_FILES
    mano-types.yang
  COMPONENT ${PKG_LONG_NAME}
  )

rift_add_yang_target(
  TARGET mano_yang
  YANG_FILES ${source_yang_files}
  GIR_PATHS ${CMAKE_CURRENT_BINARY_DIR}
  COMPONENT ${PKG_LONG_NAME}
  LIBRARIES
    rwmanifest_yang_gen
    rwschema_yang_gen
    rwcloud_yang_gen
    rwconfig_agent_yang_gen
    mano-types_yang_gen
  DEPENDS
    rwcloud_yang
    rwconfig_agent_yang
  )
