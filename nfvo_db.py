# -*- coding: utf-8 -*-

##
# Copyright 2015 Telefónica Investigación y Desarrollo, S.A.U.
# This file is part of openmano
# All Rights Reserved.
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
# contact with: nfvlabs@tid.es
##

'''
NFVO DB engine. It implements all the methods to interact with the Openmano Database
'''
__author__="Alfonso Tierno, Gerardo Garcia, Pablo Montes"
__date__ ="$28-aug-2014 10:05:01$"

import db_base
import MySQLdb as mdb
import json
#import yaml
import time


tables_with_createdat_field=["datacenters","instance_nets","instance_scenarios","instance_vms","instance_vnfs",
                           "interfaces","nets","nfvo_tenants","scenarios","sce_interfaces","sce_nets",
                           "sce_vnfs","tenants_datacenters","datacenter_tenants","vms","vnfs"]

class nfvo_db(db_base.db_base):
    def __init__(self, host=None, user=None, passwd=None, database=None, log_name='openmano.db', log_level="ERROR"):
        db_base.db_base.__init__(self, host, user, passwd, database, log_name, log_level)
        db_base.db_base.tables_with_created_field=tables_with_createdat_field
        return


    def new_vnf_as_a_whole(self,nfvo_tenant,vnf_name,vnf_descriptor,VNFCDict):
        self.logger.debug("Adding new vnf to the NFVO database")
        tries = 2
        while tries:
            created_time = time.time()
            try:
                with self.con:
            
                    myVNFDict = {}
                    myVNFDict["name"] = vnf_name
                    myVNFDict["descriptor"] = vnf_descriptor['vnf'].get('descriptor')
                    myVNFDict["public"] = vnf_descriptor['vnf'].get('public', "false")
                    myVNFDict["description"] = vnf_descriptor['vnf']['description']
                    myVNFDict["class"] = vnf_descriptor['vnf'].get('class',"MISC")
                    myVNFDict["tenant_id"] = vnf_descriptor['vnf'].get("tenant_id")
                    
                    vnf_id = self._new_row_internal('vnfs', myVNFDict, add_uuid=True, root_uuid=None, created_time=created_time)
                    #print "Adding new vms to the NFVO database"
                    #For each vm, we must create the appropriate vm in the NFVO database.
                    vmDict = {}
                    for _,vm in VNFCDict.iteritems():
                        #This code could make the name of the vms grow and grow.
                        #If we agree to follow this convention, we should check with a regex that the vnfc name is not including yet the vnf name  
                        #vm['name'] = "%s-%s" % (vnf_name,vm['name'])
                        #print "VM name: %s. Description: %s" % (vm['name'], vm['description'])
                        vm["vnf_id"] = vnf_id
                        created_time += 0.00001
                        vm_id = self._new_row_internal('vms', vm, add_uuid=True, root_uuid=vnf_id, created_time=created_time) 
                        #print "Internal vm id in NFVO DB: %s" % vm_id
                        vmDict[vm['name']] = vm_id
                
                    #Collect the data interfaces of each VM/VNFC under the 'numas' field
                    dataifacesDict = {}
                    for vm in vnf_descriptor['vnf']['VNFC']:
                        dataifacesDict[vm['name']] = {}
                        for numa in vm.get('numas', []):
                            for dataiface in numa.get('interfaces',[]):
                                db_base._convert_bandwidth(dataiface)
                                dataifacesDict[vm['name']][dataiface['name']] = {}
                                dataifacesDict[vm['name']][dataiface['name']]['vpci'] = dataiface['vpci']
                                dataifacesDict[vm['name']][dataiface['name']]['bw'] = dataiface['bandwidth']
                                dataifacesDict[vm['name']][dataiface['name']]['model'] = "PF" if dataiface['dedicated']=="yes" else ("VF"  if dataiface['dedicated']=="no" else "VFnotShared")
    
                    #Collect the bridge interfaces of each VM/VNFC under the 'bridge-ifaces' field
                    bridgeInterfacesDict = {}
                    for vm in vnf_descriptor['vnf']['VNFC']:
                        if 'bridge-ifaces' in  vm:
                            bridgeInterfacesDict[vm['name']] = {}
                            for bridgeiface in vm['bridge-ifaces']:
                                db_base._convert_bandwidth(bridgeiface)
                                bridgeInterfacesDict[vm['name']][bridgeiface['name']] = {}
                                bridgeInterfacesDict[vm['name']][bridgeiface['name']]['vpci'] = bridgeiface.get('vpci',None)
                                bridgeInterfacesDict[vm['name']][bridgeiface['name']]['mac'] = bridgeiface.get('mac_address',None)
                                bridgeInterfacesDict[vm['name']][bridgeiface['name']]['bw'] = bridgeiface.get('bandwidth', None)
                                bridgeInterfacesDict[vm['name']][bridgeiface['name']]['model'] = bridgeiface.get('model', None)
                    
                    #For each internal connection, we add it to the interfaceDict and we  create the appropriate net in the NFVO database.
                    #print "Adding new nets (VNF internal nets) to the NFVO database (if any)"
                    internalconnList = []
                    if 'internal-connections' in vnf_descriptor['vnf']:
                        for net in vnf_descriptor['vnf']['internal-connections']:
                            #print "Net name: %s. Description: %s" % (net['name'], net['description'])
                            
                            myNetDict = {}
                            myNetDict["name"] = net['name']
                            myNetDict["description"] = net['description']
                            myNetDict["type"] = net['type']
                            myNetDict["vnf_id"] = vnf_id
                            
                            created_time += 0.00001
                            net_id = self._new_row_internal('nets', myNetDict, add_uuid=True, root_uuid=vnf_id, created_time=created_time)
                                
                            for element in net['elements']:
                                ifaceItem = {}
                                #ifaceItem["internal_name"] = "%s-%s-%s" % (net['name'],element['VNFC'], element['local_iface_name'])  
                                ifaceItem["internal_name"] = element['local_iface_name']
                                #ifaceItem["vm_id"] = vmDict["%s-%s" % (vnf_name,element['VNFC'])]
                                ifaceItem["vm_id"] = vmDict[element['VNFC']]
                                ifaceItem["net_id"] = net_id
                                ifaceItem["type"] = net['type']
                                if ifaceItem ["type"] == "data":
                                    ifaceItem["vpci"] =  dataifacesDict[ element['VNFC'] ][ element['local_iface_name'] ]['vpci'] 
                                    ifaceItem["bw"] =    dataifacesDict[ element['VNFC'] ][ element['local_iface_name'] ]['bw']
                                    ifaceItem["model"] = dataifacesDict[ element['VNFC'] ][ element['local_iface_name'] ]['model']
                                else:
                                    ifaceItem["vpci"] =  bridgeInterfacesDict[ element['VNFC'] ][ element['local_iface_name'] ]['vpci']
                                    ifaceItem["mac"] =  bridgeInterfacesDict[ element['VNFC'] ][ element['local_iface_name'] ]['mac_address']
                                    ifaceItem["bw"] =    bridgeInterfacesDict[ element['VNFC'] ][ element['local_iface_name'] ]['bw']
                                    ifaceItem["model"] = bridgeInterfacesDict[ element['VNFC'] ][ element['local_iface_name'] ]['model']
                                internalconnList.append(ifaceItem)
                            #print "Internal net id in NFVO DB: %s" % net_id
                    
                    #print "Adding internal interfaces to the NFVO database (if any)"
                    for iface in internalconnList:
                        print "Iface name: %s" % iface['internal_name']
                        created_time += 0.00001
                        iface_id = self._new_row_internal('interfaces', iface, add_uuid=True, root_uuid=vnf_id, created_time=created_time)
                        #print "Iface id in NFVO DB: %s" % iface_id
                    
                    #print "Adding external interfaces to the NFVO database"
                    for iface in vnf_descriptor['vnf']['external-connections']:
                        myIfaceDict = {}
                        #myIfaceDict["internal_name"] = "%s-%s-%s" % (vnf_name,iface['VNFC'], iface['local_iface_name'])  
                        myIfaceDict["internal_name"] = iface['local_iface_name']
                        #myIfaceDict["vm_id"] = vmDict["%s-%s" % (vnf_name,iface['VNFC'])]
                        myIfaceDict["vm_id"] = vmDict[iface['VNFC']]
                        myIfaceDict["external_name"] = iface['name']
                        myIfaceDict["type"] = iface['type']
                        if iface["type"] == "data":
                            myIfaceDict["vpci"]  = dataifacesDict[ iface['VNFC'] ][ iface['local_iface_name'] ]['vpci']
                            myIfaceDict["bw"]    = dataifacesDict[ iface['VNFC'] ][ iface['local_iface_name'] ]['bw']
                            myIfaceDict["model"] = dataifacesDict[ iface['VNFC'] ][ iface['local_iface_name'] ]['model']
                        else:
                            myIfaceDict["vpci"]  = bridgeInterfacesDict[ iface['VNFC'] ][ iface['local_iface_name'] ]['vpci']
                            myIfaceDict["bw"]    = bridgeInterfacesDict[ iface['VNFC'] ][ iface['local_iface_name'] ]['bw']
                            myIfaceDict["model"] = bridgeInterfacesDict[ iface['VNFC'] ][ iface['local_iface_name'] ]['model']
                            myIfaceDict["mac"] = bridgeInterfacesDict[ iface['VNFC'] ][ iface['local_iface_name'] ]['mac']
                        print "Iface name: %s" % iface['name']
                        created_time += 0.00001
                        iface_id = self._new_row_internal('interfaces', myIfaceDict, add_uuid=True, root_uuid=vnf_id, created_time=created_time)
                        #print "Iface id in NFVO DB: %s" % iface_id
                    
                    return vnf_id
                
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries)
            tries -= 1
        

    def new_scenario(self, scenario_dict):
        tries = 2
        while tries:
            created_time = time.time()
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    tenant_id = scenario_dict.get('tenant_id')
                    #scenario
                    INSERT_={'tenant_id': tenant_id,
                             'name': scenario_dict['name'],
                             'description': scenario_dict['description'],
                             'public': scenario_dict.get('public', "false")}
                    
                    scenario_uuid =  self._new_row_internal('scenarios', INSERT_, add_uuid=True, root_uuid=None, created_time=created_time)
                    #sce_nets
                    for net in scenario_dict['nets'].values():
                        net_dict={'scenario_id': scenario_uuid}
                        net_dict["name"] = net["name"]
                        net_dict["type"] = net["type"]
                        net_dict["description"] = net.get("description")
                        net_dict["external"] = net.get("external", False)
                        if "graph" in net:
                            #net["graph"]=yaml.safe_dump(net["graph"],default_flow_style=True,width=256)
                            #TODO, must be json because of the GUI, change to yaml
                            net_dict["graph"]=json.dumps(net["graph"])
                        created_time += 0.00001
                        net_uuid =  self._new_row_internal('sce_nets', net_dict, add_uuid=True, root_uuid=scenario_uuid, created_time=created_time)
                        net['uuid']=net_uuid
                    #sce_vnfs
                    for k,vnf in scenario_dict['vnfs'].items():
                        INSERT_={'scenario_id': scenario_uuid,
                                'name': k,
                                'vnf_id': vnf['uuid'],
                                #'description': scenario_dict['name']
                                'description': vnf['description']
                            }
                        if "graph" in vnf:
                            #INSERT_["graph"]=yaml.safe_dump(vnf["graph"],default_flow_style=True,width=256)
                            #TODO, must be json because of the GUI, change to yaml
                            INSERT_["graph"]=json.dumps(vnf["graph"])
                        created_time += 0.00001
                        scn_vnf_uuid =  self._new_row_internal('sce_vnfs', INSERT_, add_uuid=True, root_uuid=scenario_uuid, created_time=created_time)
                        vnf['scn_vnf_uuid']=scn_vnf_uuid
                        #sce_interfaces
                        for iface in vnf['ifaces'].values():
                            #print 'iface', iface
                            if 'net_key' not in iface:
                                continue
                            iface['net_id'] = scenario_dict['nets'][ iface['net_key'] ]['uuid']
                            INSERT_={'sce_vnf_id': scn_vnf_uuid,
                                'sce_net_id': iface['net_id'],
                                'interface_id':  iface[ 'uuid' ]
                            }
                            created_time += 0.00001
                            iface_uuid =  self._new_row_internal('sce_interfaces', INSERT_, add_uuid=True, root_uuid=scenario_uuid, created_time=created_time)
                            
                    return scenario_uuid
                    
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries)
            tries -= 1

    def edit_scenario(self, scenario_dict):
        tries = 2
        while tries:
            modified_time = time.time()
            item_changed=0
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    #check that scenario exist
                    tenant_id = scenario_dict.get('tenant_id')
                    scenario_uuid = scenario_dict['uuid']
                    
                    where_text = "uuid='{}'".format(scenario_uuid)
                    if not tenant_id and tenant_id != "any":
                        where_text += " AND (tenant_id='{}' OR public='True')".format(tenant_id)
                    cmd = "SELECT * FROM scenarios WHERE "+ where_text
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
                    self.cur.fetchall()
                    if self.cur.rowcount==0:
                        raise db_base.db_base_Exception("No scenario found with this criteria " + where_text, db_base.HTTP_Bad_Request)
                    elif self.cur.rowcount>1:
                        raise db_base.db_base_Exception("More than one scenario found with this criteria " + where_text, db_base.HTTP_Bad_Request)

                    #scenario
                    nodes = {}
                    topology = scenario_dict.pop("topology", None)
                    if topology != None and "nodes" in topology:
                        nodes = topology.get("nodes",{})
                    UPDATE_ = {}
                    if "name" in scenario_dict:        UPDATE_["name"] = scenario_dict["name"]
                    if "description" in scenario_dict: UPDATE_["description"] = scenario_dict["description"]
                    if len(UPDATE_)>0:
                        WHERE_={'tenant_id': tenant_id, 'uuid': scenario_uuid}
                        item_changed += self._update_rows('scenarios', UPDATE_, WHERE_, modified_time=modified_time)
                    #sce_nets
                    for node_id, node in nodes.items():
                        if "graph" in node:
                            #node["graph"] = yaml.safe_dump(node["graph"],default_flow_style=True,width=256)
                            #TODO, must be json because of the GUI, change to yaml
                            node["graph"] = json.dumps(node["graph"])
                        WHERE_={'scenario_id': scenario_uuid, 'uuid': node_id}
                        #Try to change at sce_nets(version 0 API backward compatibility and sce_vnfs)
                        item_changed += self._update_rows('sce_nets', node, WHERE_)
                        item_changed += self._update_rows('sce_vnfs', node, WHERE_, modified_time=modified_time)
                    return item_changed
                    
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries)
            tries -= 1

#     def get_instance_scenario(self, instance_scenario_id, tenant_id=None):
#         '''Obtain the scenario instance information, filtering by one or serveral of the tenant, uuid or name
#         instance_scenario_id is the uuid or the name if it is not a valid uuid format
#         Only one scenario isntance must mutch the filtering or an error is returned
#         ''' 
#         print "1******************************************************************"
#         try:
#             with self.con:
#                 self.cur = self.con.cursor(mdb.cursors.DictCursor)
#                 #scenario table
#                 where_list=[]
#                 if tenant_id is not None: where_list.append( "tenant_id='" + tenant_id +"'" )
#                 if db_base._check_valid_uuid(instance_scenario_id):
#                     where_list.append( "uuid='" + instance_scenario_id +"'" )
#                 else:
#                     where_list.append( "name='" + instance_scenario_id +"'" )
#                 where_text = " AND ".join(where_list)
#                 self.cur.execute("SELECT * FROM instance_scenarios WHERE "+ where_text)
#                 rows = self.cur.fetchall()
#                 if self.cur.rowcount==0:
#                     return -HTTP_Bad_Request, "No scenario instance found with this criteria " + where_text
#                 elif self.cur.rowcount>1:
#                     return -HTTP_Bad_Request, "More than one scenario instance found with this criteria " + where_text
#                 instance_scenario_dict = rows[0]
#                 
#                 #instance_vnfs
#                 self.cur.execute("SELECT uuid,vnf_id FROM instance_vnfs WHERE instance_scenario_id='"+ instance_scenario_dict['uuid'] + "'")
#                 instance_scenario_dict['instance_vnfs'] = self.cur.fetchall()
#                 for vnf in instance_scenario_dict['instance_vnfs']:
#                     #instance_vms
#                     self.cur.execute("SELECT uuid, vim_vm_id "+
#                                 "FROM instance_vms  "+
#                                 "WHERE instance_vnf_id='" + vnf['uuid'] +"'"  
#                                 )
#                     vnf['instance_vms'] = self.cur.fetchall()
#                 #instance_nets
#                 self.cur.execute("SELECT uuid, vim_net_id FROM instance_nets WHERE instance_scenario_id='"+ instance_scenario_dict['uuid'] + "'")
#                 instance_scenario_dict['instance_nets'] = self.cur.fetchall()
#                 
#                 #instance_interfaces
#                 self.cur.execute("SELECT uuid, vim_interface_id, instance_vm_id, instance_net_id FROM instance_interfaces WHERE instance_scenario_id='"+ instance_scenario_dict['uuid'] + "'")
#                 instance_scenario_dict['instance_interfaces'] = self.cur.fetchall()
#                 
#                 db_base._convert_datetime2str(instance_scenario_dict)
#                 db_base._convert_str2boolean(instance_scenario_dict, ('public','shared','external') )
#                 print "2******************************************************************"
#                 return 1, instance_scenario_dict
#         except (mdb.Error, AttributeError) as e:
#             print "nfvo_db.get_instance_scenario DB Exception %d: %s" % (e.args[0], e.args[1])
#             return self._format_error(e)

    def get_scenario(self, scenario_id, tenant_id=None, datacenter_id=None):
        '''Obtain the scenario information, filtering by one or serveral of the tenant, uuid or name
        scenario_id is the uuid or the name if it is not a valid uuid format
        if datacenter_id is provided, it supply aditional vim_id fields with the matching vim uuid 
        Only one scenario must mutch the filtering or an error is returned
        ''' 
        tries = 2
        while tries:
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    where_text = "uuid='{}'".format(scenario_id)
                    if not tenant_id and tenant_id != "any":
                        where_text += " AND (tenant_id='{}' OR public='True')".format(tenant_id)
                    cmd = "SELECT * FROM scenarios WHERE " + where_text
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
                    rows = self.cur.fetchall()
                    if self.cur.rowcount==0:
                        raise db_base.db_base_Exception("No scenario found with this criteria " + where_text, db_base.HTTP_Bad_Request)
                    elif self.cur.rowcount>1:
                        raise db_base.db_base_Exception("More than one scenario found with this criteria " + where_text, db_base.HTTP_Bad_Request)
                    scenario_dict = rows[0]
                    #sce_vnfs
                    cmd = "SELECT uuid,name,vnf_id,description FROM sce_vnfs WHERE scenario_id='{}' ORDER BY created_at".format(scenario_dict['uuid'])
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
                    scenario_dict['vnfs'] = self.cur.fetchall()
                    for vnf in scenario_dict['vnfs']:
                        #sce_interfaces
                        cmd = "SELECT uuid,sce_net_id,interface_id FROM sce_interfaces WHERE sce_vnf_id='{}' ORDER BY created_at".format(vnf['uuid'])
                        self.logger.debug(cmd)
                        self.cur.execute(cmd)
                        vnf['interfaces'] = self.cur.fetchall()
                        #vms
                        cmd = "SELECT vms.uuid as uuid, flavor_id, image_id, vms.name as name, vms.description as description " \
                                " FROM vnfs join vms on vnfs.uuid=vms.vnf_id " \
                                " WHERE vnfs.uuid='" + vnf['vnf_id'] +"'"  \
                                " ORDER BY vms.created_at"
                        self.logger.debug(cmd)
                        self.cur.execute(cmd)
                        vnf['vms'] = self.cur.fetchall()
                        for vm in vnf['vms']:
                            if datacenter_id!=None:
                                cmd = "SELECT vim_id FROM datacenters_images WHERE image_id='{}' AND datacenter_id='{}'".format(vm['image_id'],datacenter_id)
                                self.logger.debug(cmd)
                                self.cur.execute(cmd) 
                                if self.cur.rowcount==1:
                                    vim_image_dict = self.cur.fetchone()
                                    vm['vim_image_id']=vim_image_dict['vim_id']
                                cmd = "SELECT vim_id FROM datacenters_flavors WHERE flavor_id='{}' AND datacenter_id='{}'".format(vm['flavor_id'],datacenter_id)
                                self.logger.debug(cmd)
                                self.cur.execute(cmd) 
                                if self.cur.rowcount==1:
                                    vim_flavor_dict = self.cur.fetchone()
                                    vm['vim_flavor_id']=vim_flavor_dict['vim_id']
                                
                            #interfaces
                            cmd = "SELECT uuid,internal_name,external_name,net_id,type,vpci,mac,bw,model" \
                                    " FROM interfaces" \
                                    " WHERE vm_id='{}'" \
                                    " ORDER BY created_at".format(vm['uuid'])
                            self.logger.debug(cmd)
                            self.cur.execute(cmd)
                            vm['interfaces'] = self.cur.fetchall()
                        #nets    every net of a vms
                        cmd = "SELECT uuid,name,type,description FROM nets WHERE vnf_id='{}'".format(vnf['vnf_id'])  
                        self.logger.debug(cmd)
                        self.cur.execute(cmd)
                        vnf['nets'] = self.cur.fetchall()
                    #sce_nets
                    cmd = "SELECT uuid,name,type,external,description" \
                          " FROM sce_nets  WHERE scenario_id='{}'" \
                          " ORDER BY created_at ".format(scenario_dict['uuid'])
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
                    scenario_dict['nets'] = self.cur.fetchall()
                    #datacenter_nets
                    for net in scenario_dict['nets']:
                        if str(net['external']) == 'false':
                            continue
                        WHERE_=" WHERE name='{}'".format(net['name'])
                        if datacenter_id!=None:
                            WHERE_ += " AND datacenter_id='{}'".format(datacenter_id)
                        cmd = "SELECT vim_net_id FROM datacenter_nets" + WHERE_
                        self.logger.debug(cmd)
                        self.cur.execute(cmd) 
                        d_net = self.cur.fetchone()
                        if d_net==None or datacenter_id==None:
                            #print "nfvo_db.get_scenario() WARNING external net %s not found"  % net['name']
                            net['vim_id']=None
                        else:
                            net['vim_id']=d_net['vim_net_id']
                    
                    db_base._convert_datetime2str(scenario_dict)
                    db_base._convert_str2boolean(scenario_dict, ('public','shared','external') )
                    return scenario_dict
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries)
            tries -= 1


    def delete_scenario(self, scenario_id, tenant_id=None):
        '''Deletes a scenario, filtering by one or several of the tenant, uuid or name
        scenario_id is the uuid or the name if it is not a valid uuid format
        Only one scenario must mutch the filtering or an error is returned
        ''' 
        tries = 2
        while tries:
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
    
                    #scenario table
                    where_text = "uuid='{}'".format(scenario_id)
                    if not tenant_id and tenant_id != "any":
                        where_text += " AND (tenant_id='{}' OR public='True')".format(tenant_id)
                    cmd = "SELECT * FROM scenarios WHERE "+ where_text
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
                    rows = self.cur.fetchall()
                    if self.cur.rowcount==0:
                        raise db_base.db_base_Exception("No scenario found where " + where_text, db_base.HTTP_Bad_Request)
                    elif self.cur.rowcount>1:
                        raise db_base.db_base_Exception("More than one scenario found where " + where_text, db_base.HTTP_Bad_Request)
                    scenario_uuid = rows[0]["uuid"]
                    scenario_name = rows[0]["name"]
                    
                    #sce_vnfs
                    cmd = "DELETE FROM scenarios WHERE uuid='{}'".format(scenario_uuid)
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
    
                    return scenario_uuid + " " + scenario_name
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries, "delete", "instances running")
            tries -= 1

    def new_instance_scenario_as_a_whole(self,tenant_id,instance_scenario_name,instance_scenario_description,scenarioDict):
        tries = 2
        while tries:
            created_time = time.time()
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    #instance_scenarios
                    datacenter_tenant_id = scenarioDict['datacenter_tenant_id']
                    datacenter_id = scenarioDict['datacenter_id']
                    INSERT_={'tenant_id': tenant_id,
                        'datacenter_tenant_id': datacenter_tenant_id,
                        'name': instance_scenario_name,
                        'description': instance_scenario_description,
                        'scenario_id' : scenarioDict['uuid'],
                        'datacenter_id': datacenter_id
                    }
                    instance_uuid = self._new_row_internal('instance_scenarios', INSERT_, add_uuid=True, root_uuid=None, created_time=created_time)
                    
                    net_scene2instance={}
                    #instance_nets   #nets interVNF
                    for net in scenarioDict['nets']:
                        INSERT_={'vim_net_id': net['vim_id'], 'external': net['external'], 'instance_scenario_id':instance_uuid } #,  'type': net['type']
                        INSERT_['datacenter_id'] = net.get('datacenter_id', datacenter_id) 
                        INSERT_['datacenter_tenant_id'] = net.get('datacenter_tenant_id', datacenter_tenant_id)
                        if net.get("uuid"):
                            INSERT_['sce_net_id'] = net['uuid']
                        created_time += 0.00001
                        instance_net_uuid =  self._new_row_internal('instance_nets', INSERT_, True, instance_uuid, created_time)
                        net_scene2instance[ net['uuid'] ] = instance_net_uuid
                        net['uuid'] = instance_net_uuid  #overwrite scnario uuid by instance uuid
                    
                    #instance_vnfs
                    for vnf in scenarioDict['vnfs']:
                        INSERT_={'instance_scenario_id': instance_uuid,  'vnf_id': vnf['vnf_id']  }
                        INSERT_['datacenter_id'] = vnf.get('datacenter_id', datacenter_id) 
                        INSERT_['datacenter_tenant_id'] = vnf.get('datacenter_tenant_id', datacenter_tenant_id)
                        if vnf.get("uuid"):
                            INSERT_['sce_vnf_id'] = vnf['uuid']
                        created_time += 0.00001
                        instance_vnf_uuid =  self._new_row_internal('instance_vnfs', INSERT_, True, instance_uuid, created_time)
                        vnf['uuid'] = instance_vnf_uuid  #overwrite scnario uuid by instance uuid
                        
                        #instance_nets   #nets intraVNF
                        for net in vnf['nets']:
                            INSERT_={'vim_net_id': net['vim_id'], 'external': 'false', 'instance_scenario_id':instance_uuid  } #,  'type': net['type']
                            INSERT_['datacenter_id'] = net.get('datacenter_id', datacenter_id) 
                            INSERT_['datacenter_tenant_id'] = net.get('datacenter_tenant_id', datacenter_tenant_id)
                            if net.get("uuid"):
                                INSERT_['net_id'] = net['uuid']
                            created_time += 0.00001
                            instance_net_uuid =  self._new_row_internal('instance_nets', INSERT_, True, instance_uuid, created_time)
                            net_scene2instance[ net['uuid'] ] = instance_net_uuid
                            net['uuid'] = instance_net_uuid  #overwrite scnario uuid by instance uuid
                        
                        #instance_vms
                        for vm in vnf['vms']:
                            INSERT_={'instance_vnf_id': instance_vnf_uuid,  'vm_id': vm['uuid'], 'vim_vm_id': vm['vim_id']  }
                            created_time += 0.00001
                            instance_vm_uuid =  self._new_row_internal('instance_vms', INSERT_, True, instance_uuid, created_time)
                            vm['uuid'] = instance_vm_uuid  #overwrite scnario uuid by instance uuid
                            
                            #instance_interfaces
                            for interface in vm['interfaces']:
                                net_id = interface.get('net_id', None)
                                if net_id is None:
                                    #check if is connected to a inter VNFs net
                                    for iface in vnf['interfaces']:
                                        if iface['interface_id'] == interface['uuid']:
                                            net_id = iface.get('sce_net_id', None)
                                            break
                                if net_id is None:
                                    continue
                                interface_type='external' if interface['external_name'] is not None else 'internal'
                                INSERT_={'instance_vm_id': instance_vm_uuid,  'instance_net_id': net_scene2instance[net_id],
                                    'interface_id': interface['uuid'], 'vim_interface_id': interface.get('vim_id'), 'type':  interface_type  }
                                #created_time += 0.00001
                                interface_uuid =  self._new_row_internal('instance_interfaces', INSERT_, True, instance_uuid) #, created_time)
                                interface['uuid'] = interface_uuid  #overwrite scnario uuid by instance uuid
                return instance_uuid
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries)
            tries -= 1

    def get_instance_scenario(self, instance_id, tenant_id=None, verbose=False):
        '''Obtain the instance information, filtering by one or several of the tenant, uuid or name
        instance_id is the uuid or the name if it is not a valid uuid format
        Only one instance must mutch the filtering or an error is returned
        ''' 
        tries = 2
        while tries:
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
                    #instance table
                    where_list=[]
                    if tenant_id is not None: where_list.append( "inst.tenant_id='" + tenant_id +"'" )
                    if db_base._check_valid_uuid(instance_id):
                        where_list.append( "inst.uuid='" + instance_id +"'" )
                    else:
                        where_list.append( "inst.name='" + instance_id +"'" )
                    where_text = " AND ".join(where_list)
                    cmd = "SELECT inst.uuid as uuid,inst.name as name,inst.scenario_id as scenario_id, datacenter_id" +\
                                " ,datacenter_tenant_id, s.name as scenario_name,inst.tenant_id as tenant_id" + \
                                " ,inst.description as description,inst.created_at as created_at" +\
                            " FROM instance_scenarios as inst join scenarios as s on inst.scenario_id=s.uuid"+\
                            " WHERE " + where_text
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
                    rows = self.cur.fetchall()
                    
                    if self.cur.rowcount==0:
                        raise db_base.db_base_Exception("No instance found where " + where_text, db_base.HTTP_Not_Found)
                    elif self.cur.rowcount>1:
                        raise db_base.db_base_Exception("More than one instance found where " + where_text, db_base.HTTP_Bad_Request)
                    instance_dict = rows[0]
                    
                    #instance_vnfs
                    cmd = "SELECT iv.uuid as uuid,sv.vnf_id as vnf_id,sv.name as vnf_name, sce_vnf_id, datacenter_id, datacenter_tenant_id"\
                            " FROM instance_vnfs as iv join sce_vnfs as sv on iv.sce_vnf_id=sv.uuid" \
                            " WHERE iv.instance_scenario_id='{}'" \
                            " ORDER BY iv.created_at ".format(instance_dict['uuid'])
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
                    instance_dict['vnfs'] = self.cur.fetchall()
                    for vnf in instance_dict['vnfs']:
                        vnf_manage_iface_list=[]
                        #instance vms
                        cmd = "SELECT iv.uuid as uuid, vim_vm_id, status, error_msg, vim_info, iv.created_at as created_at, name "\
                                " FROM instance_vms as iv join vms on iv.vm_id=vms.uuid "\
                                " WHERE instance_vnf_id='{}' ORDER BY iv.created_at".format(vnf['uuid'])
                        self.logger.debug(cmd)
                        self.cur.execute(cmd)
                        vnf['vms'] = self.cur.fetchall()
                        for vm in vnf['vms']:
                            vm_manage_iface_list=[]
                            #instance_interfaces
                            cmd = "SELECT vim_interface_id, instance_net_id, internal_name,external_name, mac_address, ii.ip_address as ip_address, vim_info, i.type as type "\
                                    " FROM instance_interfaces as ii join interfaces as i on ii.interface_id=i.uuid "\
                                    " WHERE instance_vm_id='{}' ORDER BY created_at".format(vm['uuid'])
                            self.logger.debug(cmd)
                            self.cur.execute(cmd )
                            vm['interfaces'] = self.cur.fetchall()
                            for iface in vm['interfaces']:
                                if iface["type"] == "mgmt" and iface["ip_address"]:
                                    vnf_manage_iface_list.append(iface["ip_address"])
                                    vm_manage_iface_list.append(iface["ip_address"])
                                if not verbose:
                                    del iface["type"]
                            if vm_manage_iface_list: vm["ip_address"] = ",".join(vm_manage_iface_list)
                        if vnf_manage_iface_list: vnf["ip_address"] = ",".join(vnf_manage_iface_list)
                        
                    #instance_nets
                    #select_text = "instance_nets.uuid as uuid,sce_nets.name as net_name,instance_nets.vim_net_id as net_id,instance_nets.status as status,instance_nets.external as external" 
                    #from_text = "instance_nets join instance_scenarios on instance_nets.instance_scenario_id=instance_scenarios.uuid " + \
                    #            "join sce_nets on instance_scenarios.scenario_id=sce_nets.scenario_id"
                    #where_text = "instance_nets.instance_scenario_id='"+ instance_dict['uuid'] + "'"
                    cmd = "SELECT uuid,vim_net_id,status,error_msg,vim_info,external, sce_net_id, net_id as vnf_net_id, datacenter_id, datacenter_tenant_id"\
                            " FROM instance_nets" \
                            " WHERE instance_scenario_id='{}' ORDER BY created_at".format(instance_dict['uuid'])
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
                    instance_dict['nets'] = self.cur.fetchall()
                    
                    db_base._convert_datetime2str(instance_dict)
                    db_base._convert_str2boolean(instance_dict, ('public','shared','external') )
                    return instance_dict
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries)
            tries -= 1
        
    def delete_instance_scenario(self, instance_id, tenant_id=None):
        '''Deletes a instance_Scenario, filtering by one or serveral of the tenant, uuid or name
        instance_id is the uuid or the name if it is not a valid uuid format
        Only one instance_scenario must mutch the filtering or an error is returned
        ''' 
        tries = 2
        while tries:
            try:
                with self.con:
                    self.cur = self.con.cursor(mdb.cursors.DictCursor)
    
                    #instance table
                    where_list=[]
                    if tenant_id is not None: where_list.append( "tenant_id='" + tenant_id +"'" )
                    if db_base._check_valid_uuid(instance_id):
                        where_list.append( "uuid='" + instance_id +"'" )
                    else:
                        where_list.append( "name='" + instance_id +"'" )
                    where_text = " AND ".join(where_list)
                    cmd = "SELECT * FROM instance_scenarios WHERE "+ where_text
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
                    rows = self.cur.fetchall()
                    
                    if self.cur.rowcount==0:
                        raise db_base.db_base_Exception("No instance found where " + where_text, db_base.HTTP_Bad_Request)
                    elif self.cur.rowcount>1:
                        raise db_base.db_base_Exception("More than one instance found where " + where_text, db_base.HTTP_Bad_Request)
                    instance_uuid = rows[0]["uuid"]
                    instance_name = rows[0]["name"]
                    
                    #sce_vnfs
                    cmd = "DELETE FROM instance_scenarios WHERE uuid='{}'".format(instance_uuid)
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
    
                    return instance_uuid + " " + instance_name
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries, "delete", "No dependences can avoid deleting!!!!")
            tries -= 1
    
    def new_instance_scenario(self, instance_scenario_dict, tenant_id):
        #return self.new_row('vnfs', vnf_dict, None, tenant_id, True, True)
        return self._new_row_internal('instance_scenarios', instance_scenario_dict, tenant_id, add_uuid=True, root_uuid=None, log=True)

    def update_instance_scenario(self, instance_scenario_dict):
        #TODO:
        return

    def new_instance_vnf(self, instance_vnf_dict, tenant_id, instance_scenario_id = None):
        #return self.new_row('vms', vm_dict, tenant_id, True, True)
        return self._new_row_internal('instance_vnfs', instance_vnf_dict, tenant_id, add_uuid=True, root_uuid=instance_scenario_id, log=True)

    def update_instance_vnf(self, instance_vnf_dict):
        #TODO:
        return
    
    def delete_instance_vnf(self, instance_vnf_id):
        #TODO:
        return

    def new_instance_vm(self, instance_vm_dict, tenant_id, instance_scenario_id = None):
        #return self.new_row('vms', vm_dict, tenant_id, True, True)
        return self._new_row_internal('instance_vms', instance_vm_dict, tenant_id, add_uuid=True, root_uuid=instance_scenario_id, log=True)

    def update_instance_vm(self, instance_vm_dict):
        #TODO:
        return
    
    def delete_instance_vm(self, instance_vm_id):
        #TODO:
        return

    def new_instance_net(self, instance_net_dict, tenant_id, instance_scenario_id = None):
        return self._new_row_internal('instance_nets', instance_net_dict, tenant_id, add_uuid=True, root_uuid=instance_scenario_id, log=True)
    
    def update_instance_net(self, instance_net_dict):
        #TODO:
        return

    def delete_instance_net(self, instance_net_id):
        #TODO:
        return
    
    def new_instance_interface(self, instance_interface_dict, tenant_id, instance_scenario_id = None):
        return self._new_row_internal('instance_interfaces', instance_interface_dict, tenant_id, add_uuid=True, root_uuid=instance_scenario_id, log=True)

    def update_instance_interface(self, instance_interface_dict):
        #TODO:
        return

    def delete_instance_interface(self, instance_interface_dict):
        #TODO:
        return

    def update_datacenter_nets(self, datacenter_id, new_net_list=[]):
        ''' Removes the old and adds the new net list at datacenter list for one datacenter.
        Attribute 
            datacenter_id: uuid of the datacenter to act upon
            table: table where to insert
            new_net_list: the new values to be inserted. If empty it only deletes the existing nets
        Return: (Inserted items, Deleted items) if OK, (-Error, text) if error
        '''
        tries = 2
        while tries:
            created_time = time.time()
            try:
                with self.con:
                    self.cur = self.con.cursor()
                    cmd="DELETE FROM datacenter_nets WHERE datacenter_id='{}'".format(datacenter_id)
                    self.logger.debug(cmd)
                    self.cur.execute(cmd)
                    deleted = self.cur.rowcount
                    inserted = 0
                    for new_net in new_net_list:
                        created_time += 0.00001
                        self._new_row_internal('datacenter_nets', new_net, add_uuid=True, created_time=created_time)
                        inserted += 1
                    return inserted, deleted
            except (mdb.Error, AttributeError) as e:
                self._format_error(e, tries)
            tries -= 1

        
