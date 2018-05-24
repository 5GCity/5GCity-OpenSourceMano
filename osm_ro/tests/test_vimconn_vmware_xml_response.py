# -*- coding: utf-8 -*-

##
# Copyright 2016-2017 VMware Inc.
# This file is part of ETSI OSM
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
# contact:  osslegalrouting@vmware.com
##

vdc_xml_response = """<?xml version="1.0" encoding="UTF-8"?>
        <Vdc xmlns="http://www.vmware.com/vcloud/v1.5" status="1" name="Org3-VDC-PVDC1" id="urn:vcloud:vdc:2584137f-6541-4c04-a2a2-e56bfca14c69" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69" type="application/vnd.vmware.vcloud.vdc+xml" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.vmware.com/vcloud/v1.5 http://localhost/api/v1.5/schema/master.xsd">
		<Link rel="up" href="https://localhost/api/org/2cb3dffb-5c51-4355-8406-28553ead28ac" type="application/vnd.vmware.vcloud.org+xml"/>
		<Link rel="down" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69/metadata" type="application/vnd.vmware.vcloud.metadata+xml"/>
		<Link rel="edit" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69" type="application/vnd.vmware.vcloud.vdc+xml"/>
		<Link rel="add" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69/action/uploadVAppTemplate" type="application/vnd.vmware.vcloud.uploadVAppTemplateParams+xml"/>
		<Link rel="add" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69/media" type="application/vnd.vmware.vcloud.media+xml"/>
		<Link rel="add" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69/action/instantiateOvf" type="application/vnd.vmware.vcloud.instantiateOvfParams+xml"/>
		<Link rel="add" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69/action/instantiateVAppTemplate" type="application/vnd.vmware.vcloud.instantiateVAppTemplateParams+xml"/>
		<Link rel="add" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69/action/cloneVApp" type="application/vnd.vmware.vcloud.cloneVAppParams+xml"/>
		<Link rel="add" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69/action/cloneVAppTemplate" type="application/vnd.vmware.vcloud.cloneVAppTemplateParams+xml"/>
		<Link rel="add" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69/action/cloneMedia" type="application/vnd.vmware.vcloud.cloneMediaParams+xml"/>
		<Link rel="add" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69/action/captureVApp" type="application/vnd.vmware.vcloud.captureVAppParams+xml"/>
		<Link rel="add" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69/action/composeVApp" type="application/vnd.vmware.vcloud.composeVAppParams+xml"/>
		<Link rel="add" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69/disk" type="application/vnd.vmware.vcloud.diskCreateParams+xml"/>
		<Link rel="edgeGateways" href="https://localhost/api/admin/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69/edgeGateways" type="application/vnd.vmware.vcloud.query.records+xml"/>
		<Link rel="add" href="https://localhost/api/admin/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69/networks" type="application/vnd.vmware.vcloud.orgVdcNetwork+xml"/>
		<Link rel="orgVdcNetworks" href="https://localhost/api/admin/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69/networks" type="application/vnd.vmware.vcloud.query.records+xml"/>
		<Link rel="alternate" href="https://localhost/api/admin/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69" type="application/vnd.vmware.admin.vdc+xml"/>
		<Description>Org3-VDC-PVDC1</Description>
		<AllocationModel>AllocationVApp</AllocationModel>
		<ComputeCapacity>
		<Cpu>
		<Units>MHz</Units>
		<Allocated>0</Allocated>
		<Limit>0</Limit>
		<Reserved>0</Reserved>
		<Used>2000</Used>
		<Overhead>0</Overhead>
		</Cpu>
		<Memory>
		<Units>MB</Units>
		<Allocated>0</Allocated>
		<Limit>0</Limit>
		<Reserved>0</Reserved>
		<Used>2048</Used>
		<Overhead>71</Overhead>
		</Memory>
		</ComputeCapacity>
		<ResourceEntities>
		<ResourceEntity href="https://localhost/api/vAppTemplate/vappTemplate-2999a787-ca96-4d1c-8b7c-9d0a8bd14bce" name="cirros" type="application/vnd.vmware.vcloud.vAppTemplate+xml"/>
        <ResourceEntity href="https://localhost/api/vAppTemplate/vappTemplate-324649a3-d263-4446-aace-4e2c801a85bd" name="cirros_10" type="application/vnd.vmware.vcloud.vAppTemplate+xml"/>
		<ResourceEntity href="https://localhost/api/vAppTemplate/vappTemplate-8ea35d43-0c72-4267-bac9-42e4a5248c32" name="Test_Cirros" type="application/vnd.vmware.vcloud.vAppTemplate+xml"/>
		<ResourceEntity href="https://localhost/api/vAppTemplate/vappTemplate-9bf292a2-58c4-4d4b-995b-623e88b74226" name="Ubuntu-vm" type="application/vnd.vmware.vcloud.vAppTemplate+xml"/>
		<ResourceEntity href="https://localhost/api/vAppTemplate/vappTemplate-be93140e-da0d-4b8c-8ab4-06d132bf47c0" name="Ubuntu16" type="application/vnd.vmware.vcloud.vAppTemplate+xml"/>
		<ResourceEntity href="https://localhost/api/vApp/vapp-0da5344d-4d65-4362-bac6-e8524c97edb1" name="Inst10.linux1.a-e9f75c31-eadf-4b48-9a5e-d957314530d7" type="application/vnd.vmware.vcloud.vApp+xml"/>
		<ResourceEntity href="https://localhost/api/vApp/vapp-3e0df975-1380-4544-9f25-0683f9eb41f0" name="Inst12.linux1.a-93854e6d-d87c-4f0a-ba10-eaf59d7555bf" type="application/vnd.vmware.vcloud.vApp+xml"/>
		<ResourceEntity href="https://localhost/api/vApp/vapp-6f5848b8-5498-4854-a35e-45cb25b8fdb0" name="Inst11.linux1.a-5ca666e8-e077-4268-aff2-99960af28eb5" type="application/vnd.vmware.vcloud.vApp+xml"/>
		<ResourceEntity href="https://localhost/api/vApp/vapp-76510a06-c949-4bea-baad-629daaccb84a" name="cirros_nsd.cirros_vnfd__1.a-a9c957c4-29a5-4559-a630-00ae028592f7" type="application/vnd.vmware.vcloud.vApp+xml"/>
		</ResourceEntities><AvailableNetworks><Network href="https://localhost/api/network/1627b438-68bf-44be-800c-8f48029761f6" name="default-17c27654-2a45-4713-a799-94cb91de2610" type="application/vnd.vmware.vcloud.network+xml"/>
		<Network href="https://localhost/api/network/190e9e04-a904-412b-877e-92d8e8699abd" name="cirros_nsd.cirros_nsd_vld1-86c861a9-d985-4e31-9c20-21de1e8a619d" type="application/vnd.vmware.vcloud.network+xml"/>
		<Network href="https://localhost/api/network/3838c23e-cb0e-492f-a91f-f3352918ff8b" name="cirros_nsd.cirros_nsd_vld1-75ce0375-b2e6-4b7f-b821-5b395276bcd8" type="application/vnd.vmware.vcloud.network+xml"/>
		<Network href="https://localhost/api/network/5aca5c32-c0a2-4e1b-980e-8fd906a49f4e" name="default-60a54140-66dd-4806-8ca3-069d34530478" type="application/vnd.vmware.vcloud.network+xml"/>
		<Network href="https://localhost/api/network/de854aa2-0b77-4ace-a696-85494a3dc3c4" name="default-971acee6-0298-4085-b107-7601bc8c8712" type="application/vnd.vmware.vcloud.network+xml"/>
		</AvailableNetworks>
		<Capabilities>
		<SupportedHardwareVersions>
		<SupportedHardwareVersion>vmx-04</SupportedHardwareVersion>
		<SupportedHardwareVersion>vmx-07</SupportedHardwareVersion>
		<SupportedHardwareVersion>vmx-08</SupportedHardwareVersion>
		<SupportedHardwareVersion>vmx-09</SupportedHardwareVersion>
		<SupportedHardwareVersion>vmx-10</SupportedHardwareVersion>
		<SupportedHardwareVersion>vmx-11</SupportedHardwareVersion>
		</SupportedHardwareVersions>
		</Capabilities>
		<NicQuota>0</NicQuota>
		<NetworkQuota>1000</NetworkQuota>
		<UsedNetworkCount>0</UsedNetworkCount>
		<VmQuota>0</VmQuota>
		<IsEnabled>true</IsEnabled>
		<VdcStorageProfiles>
		<VdcStorageProfile href="https://localhost/api/vdcStorageProfile/3b82941c-11ed-407e-ada0-42d282fcd425" name="NFS Storage Policy" type="application/vnd.vmware.vcloud.vdcStorageProfile+xml"/>
		<VdcStorageProfile href="https://localhost/api/vdcStorageProfile/950701fb-2b8a-4808-80f1-27d1170a2bfc" name="*" type="application/vnd.vmware.vcloud.vdcStorageProfile+xml"/>
		</VdcStorageProfiles>
        <VCpuInMhz2>1000</VCpuInMhz2>
        </Vdc>"""

network_xml_response = """<?xml version="1.0" encoding="UTF-8"?>
             <OrgVdcNetwork xmlns="http://www.vmware.com/vcloud/v1.5" status="1" name="testing_6XXftDTroat1-03b18565-de01-4154-af51-8dbea42f0d84" id="urn:vcloud:network:5c04dc6d-6096-47c6-b72b-68f19013d491" href="https://localhost/api/network/5c04dc6d-6096-47c6-b72b-68f19013d491" type="application/vnd.vmware.vcloud.orgVdcNetwork+xml" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.vmware.com/vcloud/v1.5 http://localhost/api/v1.5/schema/master.xsd">
             <Link rel="up" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69" type="application/vnd.vmware.vcloud.vdc+xml"/>
             <Link rel="down" href="https://localhost/api/network/5c04dc6d-6096-47c6-b72b-68f19013d491/metadata" type="application/vnd.vmware.vcloud.metadata+xml"/>
             <Link rel="down" href="https://localhost/api/network/5c04dc6d-6096-47c6-b72b-68f19013d491/allocatedAddresses/" type="application/vnd.vmware.vcloud.allocatedNetworkAddress+xml"/>
             <Description>Openmano created</Description>
             <Configuration>
             <IpScopes>
             <IpScope>
             <IsInherited>true</IsInherited>
             <Gateway>12.169.24.23</Gateway>
             <Netmask>255.255.255.0</Netmask>
             <Dns1>12.169.24.102</Dns1>
             <DnsSuffix>corp.local</DnsSuffix>
             <IsEnabled>true</IsEnabled>
             <IpRanges>
             <IpRange>
             <StartAddress>12.169.24.115</StartAddress>
             <EndAddress>12.169.241.150</EndAddress>
             </IpRange>
             </IpRanges>
             </IpScope>
             </IpScopes>
             <FenceMode>bridged</FenceMode>
             <RetainNetInfoAcrossDeployments>false</RetainNetInfoAcrossDeployments>
             </Configuration>
             <IsShared>false</IsShared>
             </OrgVdcNetwork>"""

delete_network_xml_response = """<?xml version="1.0" encoding="UTF-8"?>
            <OrgVdcNetwork xmlns="http://www.vmware.com/vcloud/v1.5" status="1" name="testing_negjXxdlB-7fdcf9f3-de32-4ae6-b9f9-fb725a80a74f" id="urn:vcloud:network:0a55e5d1-43a2-4688-bc92-cb304046bf87" href="https://localhost/api/network/0a55e5d1-43a2-4688-bc92-cb304046bf87" type="application/vnd.vmware.vcloud.orgVdcNetwork+xml" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.vmware.com/vcloud/v1.5 http://localhost/api/v1.5/schema/master.xsd">
			<Link rel="up" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69" type="application/vnd.vmware.vcloud.vdc+xml"/>
			<Link rel="down" href="https://localhost/api/network/0a55e5d1-43a2-4688-bc92-cb304046bf87/metadata" type="application/vnd.vmware.vcloud.metadata+xml"/>
			<Link rel="down" href="https://localhost/api/network/0a55e5d1-43a2-4688-bc92-cb304046bf87/allocatedAddresses/"  type="application/vnd.vmware.vcloud.allocatedNetworkAddress+xml"/>
			<Description>Openmano created</Description>
			<Configuration>
			<IpScopes>
			<IpScope>
			<IsInherited>true</IsInherited>
			<Gateway>12.169.24.23</Gateway>
			<Netmask>255.255.255.0</Netmask>
			<Dns1>12.169.24.102</Dns1>
			<DnsSuffix>corp.local</DnsSuffix>
			<IsEnabled>true</IsEnabled>
			<IpRanges>
			<IpRange>
			<StartAddress>12.169.241.115</StartAddress>
			<EndAddress>12.169.241.150</EndAddress>
			</IpRange></IpRanges></IpScope>
			</IpScopes>
			<FenceMode>bridged</FenceMode>
			<RetainNetInfoAcrossDeployments>false</RetainNetInfoAcrossDeployments>
			</Configuration>
			<IsShared>false</IsShared>
			</OrgVdcNetwork>"""

create_network_xml_response = """<?xml version="1.0" encoding="UTF-8"?>
            <OrgVdcNetwork xmlns="http://www.vmware.com/vcloud/v1.5" name="Test_network-25cb63aa-30e9-4de5-be76-1d6e00a2781a" id="urn:vcloud:network:df1956fa-da04-419e-a6a2-427b6f83788f" href="https://localhost/api/admin/network/df1956fa-da04-419e-a6a2-427b6f83788f" type="application/vnd.vmware.vcloud.orgVdcNetwork+xml" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.vmware.com/vcloud/v1.5 http://localhost/api/v1.5/schema/master.xsd">
            <Link rel="edit" href="https://localhost/api/admin/network/df1956fa-da04-419e-a6a2-427b6f83788f" type="application/vnd.vmware.vcloud.orgVdcNetwork+xml"/>
            <Link rel="remove" href="https://localhost/api/admin/network/df1956fa-da04-419e-a6a2-427b6f83788f"/>
            <Link rel="repair" href="https://localhost/api/admin/network/df1956fa-da04-419e-a6a2-427b6f83788f/action/reset"/>
            <Link rel="up" href="https://localhost/api/admin/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69" type="application/vnd.vmware.admin.vdc+xml"/>
            <Link rel="down" href="https://localhost/api/admin/network/df1956fa-da04-419e-a6a2-427b6f83788f/metadata" type="application/vnd.vmware.vcloud.metadata+xml"/>
            <Link rel="down" href="https://localhost/api/admin/network/df1956fa-da04-419e-a6a2-427b6f83788f/allocatedAddresses/" type="application/vnd.vmware.vcloud.allocatedNetworkAddress+xml"/>
            <Description>Openmano created</Description>
            <Tasks>
                  <Task cancelRequested="false" expiryTime="2017-12-14T02:00:39.865-08:00" operation="Creating Network Test_network-25cb63aa-30e9-4de5-be76-1d6e00a2781a(df1956fa-da04-419e-a6a2-427b6f83788f)" operationName="networkCreateOrgVdcNetwork" serviceNamespace="com.vmware.vcloud" startTime="2017-09-15T02:00:39.865-07:00" status="queued" name="task" id="urn:vcloud:task:0600f592-42ce-4d58-85c0-212c569ba6e6" href="https://localhost/api/task/0600f592-42ce-4d58-85c0-212c569ba6e6" type="application/vnd.vmware.vcloud.task+xml">
                  <Owner href="https://localhost/api/admin/network/df1956fa-da04-419e-a6a2-427b6f83788f" name="Test_network-25cb63aa-30e9-4de5-be76-1d6e00a2781a" type="application/vnd.vmware.admin.network+xml"/>
                  <User href="https://localhost/api/admin/user/f49f28e0-7172-4b17-aaee-d171ce2b60da" name="administrator" type="application/vnd.vmware.admin.user+xml"/>
                  <Organization href="https://localhost/api/org/a93c9db9-7471-3192-8d09-a8f7eeda85f9" name="System" type="application/vnd.vmware.vcloud.org+xml"/>
                  <Details/>
                  </Task>
            </Tasks>
            <Configuration>
            <IpScopes><IpScope>
            <IsInherited>false</IsInherited>
            <Gateway>12.16.113.1</Gateway>
            <Netmask>255.255.255.0</Netmask>
            <Dns1>12.16.113.2</Dns1>
            <IsEnabled>true</IsEnabled>
            <IpRanges><IpRange>
            <StartAddress>12.168.113.3</StartAddress>
            <EndAddress>12.168.113.52</EndAddress>
            </IpRange></IpRanges>
            </IpScope></IpScopes>
            <ParentNetwork href="https://localhost/api/admin/network/19b01b42-c862-4d0f-bcbf-d053e7396fc0" name="" type="application/vnd.vmware.admin.network+xml"/>
            <FenceMode>bridged</FenceMode>
            <RetainNetInfoAcrossDeployments>false</RetainNetInfoAcrossDeployments>
            </Configuration><IsShared>false</IsShared>
            </OrgVdcNetwork>"""

catalog1_xml_response = """<?xml version="1.0" encoding="UTF-8"?>
<Catalog xmlns="http://www.vmware.com/vcloud/v1.5" name="Ubuntu-vm" id="urn:vcloud:catalog:d0a11b12-780e-4681-babb-2b1fd6693f62" href="https://localhost/api/catalog/d0a11b12-780e-4681-babb-2b1fd6693f62" type="application/vnd.vmware.vcloud.catalog+xml" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.vmware.com/vcloud/v1.5 http://localhost/api/v1.5/schema/master.xsd">
<Link rel="up" href="https://localhost/api/org/2cb3dffb-5c51-4355-8406-28553ead28ac" type="application/vnd.vmware.vcloud.org+xml"/>
<Link rel="down" href="https://localhost/api/catalog/d0a11b12-780e-4681-babb-2b1fd6693f62/metadata" type="application/vnd.vmware.vcloud.metadata+xml"/>
<Link rel="add" href="https://localhost/api/catalog/d0a11b12-780e-4681-babb-2b1fd6693f62/catalogItems" type="application/vnd.vmware.vcloud.catalogItem+xml"/>
<Link rel="add" href="https://localhost/api/catalog/d0a11b12-780e-4681-babb-2b1fd6693f62/action/upload" type="application/vnd.vmware.vcloud.media+xml"/>
<Link rel="add" href="https://localhost/api/catalog/d0a11b12-780e-4681-babb-2b1fd6693f62/action/upload" type="application/vnd.vmware.vcloud.uploadVAppTemplateParams+xml"/>
<Link rel="copy" href="https://localhost/api/catalog/d0a11b12-780e-4681-babb-2b1fd6693f62/action/copy" type="application/vnd.vmware.vcloud.copyOrMoveCatalogItemParams+xml"/>
<Link rel="move" href="https://localhost/api/catalog/d0a11b12-780e-4681-babb-2b1fd6693f62/action/move" type="application/vnd.vmware.vcloud.copyOrMoveCatalogItemParams+xml"/>
<Link rel="add" href="https://localhost/api/catalog/d0a11b12-780e-4681-babb-2b1fd6693f62/action/captureVApp" type="application/vnd.vmware.vcloud.captureVAppParams+xml"/>
<Link rel="down" href="https://localhost/api/catalog/d0a11b12-780e-4681-babb-2b1fd6693f62/controlAccess/" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="controlAccess" href="https://localhost/api/catalog/d0a11b12-780e-4681-babb-2b1fd6693f62/action/controlAccess" type="application/vnd.vmware.vcloud.controlAccess+xml"/> <Description>Ubuntu-vm</Description>
<CatalogItems><CatalogItem href="https://localhost/api/catalogItem/04fc0041-8e40-4e37-b072-7dba3e1c6a30" id="04fc0041-8e40-4e37-b072-7dba3e1c6a30" name="Ubuntu-vm" type="application/vnd.vmware.vcloud.catalogItem+xml"/></CatalogItems><IsPublished>false</IsPublished><DateCreated>2017-03-17T03:17:11.293-07:00</DateCreated><VersionNumber>5</VersionNumber>
</Catalog>"""

catalog2_xml_response = """<?xml version="1.0" encoding="UTF-8"?>
<Catalog xmlns="http://www.vmware.com/vcloud/v1.5" name="cirros" id="urn:vcloud:catalog:32ccb082-4a65-41f6-bcd6-38942e8a3829" href="https://localhost/api/catalog/32ccb082-4a65-41f6-bcd6-38942e8a3829" type="application/vnd.vmware.vcloud.catalog+xml" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.vmware.com/vcloud/v1.5 http://localhost/api/v1.5/schema/master.xsd">
<Link rel="up" href="https://localhost/api/org/2cb3dffb-5c51-4355-8406-28553ead28ac" type="application/vnd.vmware.vcloud.org+xml"/>
<Link rel="down" href="https://localhost/api/catalog/32ccb082-4a65-41f6-bcd6-38942e8a3829/metadata" type="application/vnd.vmware.vcloud.metadata+xml"/>
<Link rel="add" href="https://localhost/api/catalog/32ccb082-4a65-41f6-bcd6-38942e8a3829/catalogItems" type="application/vnd.vmware.vcloud.catalogItem+xml"/>
<Link rel="add" href="https://localhost/api/catalog/32ccb082-4a65-41f6-bcd6-38942e8a3829/action/upload" type="application/vnd.vmware.vcloud.media+xml"/>
<Link rel="add" href="https://localhost/api/catalog/32ccb082-4a65-41f6-bcd6-38942e8a3829/action/upload" type="application/vnd.vmware.vcloud.uploadVAppTemplateParams+xml"/>
<Link rel="copy" href="https://localhost/api/catalog/32ccb082-4a65-41f6-bcd6-38942e8a3829/action/copy" type="application/vnd.vmware.vcloud.copyOrMoveCatalogItemParams+xml"/>
<Link rel="move" href="https://localhost/api/catalog/32ccb082-4a65-41f6-bcd6-38942e8a3829/action/move" type="application/vnd.vmware.vcloud.copyOrMoveCatalogItemParams+xml"/>
<Link rel="add" href="https://localhost/api/catalog/32ccb082-4a65-41f6-bcd6-38942e8a3829/action/captureVApp" type="application/vnd.vmware.vcloud.captureVAppParams+xml"/>
<Link rel="down" href="https://localhost/api/catalog/32ccb082-4a65-41f6-bcd6-38942e8a3829/controlAccess/" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="controlAccess" href="https://localhost/api/catalog/32ccb082-4a65-41f6-bcd6-38942e8a3829/action/controlAccess" type="application/vnd.vmware.vcloud.controlAccess+xml"/> <Description>cirros</Description>
<CatalogItems><CatalogItem href="https://localhost/api/catalogItem/98316d41-e38c-40c2-ac28-5462e8aada8c" id="98316d41-e38c-40c2-ac28-5462e8aada8c" name="cirros" type="application/vnd.vmware.vcloud.catalogItem+xml"/></CatalogItems><IsPublished>false</IsPublished><DateCreated>2017-03-08T02:06:07.003-08:00</DateCreated><VersionNumber>5</VersionNumber>
</Catalog>"""

vapp_xml_response = """<?xml version="1.0" encoding="UTF-8"?>
<VApp xmlns="http://www.vmware.com/vcloud/v1.5" xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData" xmlns:vmw="http://www.vmware.com/schema/ovf" xmlns:ovfenv="http://schemas.dmtf.org/ovf/environment/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ovfDescriptorUploaded="true" deployed="true" status="4" name="Test1_vm-69a18104-8413-4cb8-bad7-b5afaec6f9fa" id="urn:vcloud:vapp:4f6a9b49-e92d-4935-87a1-0e4dc9c3a069" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069" type="application/vnd.vmware.vcloud.vApp+xml" xsi:schemaLocation="http://schemas.dmtf.org/ovf/envelope/1 http://schemas.dmtf.org/ovf/envelope/1/dsp8023_1.1.0.xsd http://www.vmware.com/vcloud/v1.5 http://localhost/api/v1.5/schema/master.xsd http://www.vmware.com/schema/ovf http://www.vmware.com/schema/ovf http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2.22.0/CIM_ResourceAllocationSettingData.xsd http://schemas.dmtf.org/ovf/environment/1 http://schemas.dmtf.org/ovf/envelope/1/dsp8027_1.1.0.xsd http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2.22.0/CIM_VirtualSystemSettingData.xsd">
<Link rel="power:powerOff" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/power/action/powerOff"/>
<Link rel="power:reboot" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/power/action/reboot"/>
<Link rel="power:reset" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/power/action/reset"/>
<Link rel="power:shutdown" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/power/action/shutdown"/>
<Link rel="power:suspend" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/power/action/suspend"/>
<Link rel="deploy" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/action/deploy" type="application/vnd.vmware.vcloud.deployVAppParams+xml"/>
<Link rel="undeploy" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/action/undeploy" type="application/vnd.vmware.vcloud.undeployVAppParams+xml"/>
<Link rel="down" href="https://localhost/api/network/9489a59a-0339-4151-9667-f5b90296c36d" name="External-Network-1074" type="application/vnd.vmware.vcloud.vAppNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/379f083b-4057-4724-a128-ed5bc6672591" name="testing_T6nODiW4-68f68d93-0350-4d86-b40b-6e74dedf994d" type="application/vnd.vmware.vcloud.vAppNetwork+xml"/>
<Link rel="down" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/controlAccess/" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="controlAccess" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/action/controlAccess" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="up" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69" type="application/vnd.vmware.vcloud.vdc+xml"/>
<Link rel="edit" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069" type="application/vnd.vmware.vcloud.vApp+xml"/>
<Link rel="down" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/owner" type="application/vnd.vmware.vcloud.owner+xml"/>
<Link rel="down" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/metadata" type="application/vnd.vmware.vcloud.metadata+xml"/>
<Link rel="ovf" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/ovf" type="text/xml"/>
<Link rel="down" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/productSections/" type="application/vnd.vmware.vcloud.productSections+xml"/>
<Link rel="snapshot:create" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/action/createSnapshot" type="application/vnd.vmware.vcloud.createSnapshotParams+xml"/>
<LeaseSettingsSection href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/leaseSettingsSection/" type="application/vnd.vmware.vcloud.leaseSettingsSection+xml" ovf:required="false">
<ovf:Info>Lease settings section</ovf:Info>
<Link rel="edit" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/leaseSettingsSection/" type="application/vnd.vmware.vcloud.leaseSettingsSection+xml"/> <DeploymentLeaseInSeconds>0</DeploymentLeaseInSeconds><StorageLeaseInSeconds>7776000</StorageLeaseInSeconds></LeaseSettingsSection>
<ovf:StartupSection xmlns:vcloud="http://www.vmware.com/vcloud/v1.5" vcloud:type="application/vnd.vmware.vcloud.startupSection+xml" vcloud:href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/startupSection/"><ovf:Info>VApp startup section</ovf:Info>
<ovf:Item ovf:id="Test1_vm-69a18104-8413-4cb8-bad7-b5afaec6f9fa" ovf:order="0" ovf:startAction="powerOn" ovf:startDelay="0" ovf:stopAction="powerOff" ovf:stopDelay="0"/>
<Link rel="edit" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/startupSection/" type="application/vnd.vmware.vcloud.startupSection+xml"/> </ovf:StartupSection><ovf:NetworkSection xmlns:vcloud="http://www.vmware.com/vcloud/v1.5" vcloud:type="application/vnd.vmware.vcloud.networkSection+xml" vcloud:href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/networkSection/"><ovf:Info>The list of logical networks</ovf:Info>
<ovf:Network ovf:name="External-Network-1074"><ovf:Description>External-Network-1074</ovf:Description></ovf:Network>
<ovf:Network ovf:name="testing_T6nODiW4-68f68d93-0350-4d86-b40b-6e74dedf994d"><ovf:Description/></ovf:Network></ovf:NetworkSection>
<NetworkConfigSection href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/networkConfigSection/" type="application/vnd.vmware.vcloud.networkConfigSection+xml" ovf:required="false"><ovf:Info>The configuration parameters for logical networks</ovf:Info>
<Link rel="edit" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/networkConfigSection/"   type="application/vnd.vmware.vcloud.networkConfigSection+xml"/><NetworkConfig networkName="External-Network-1074"><Link rel="repair" href="https://localhost/api/admin/network/9489a59a-0339-4151-9667-f5b90296c36d/action/reset"/>
<Description>External-Network-1074</Description><Configuration><IpScopes><IpScope><IsInherited>false</IsInherited><Gateway>192.168.254.1</Gateway><Netmask>255.255.255.0</Netmask>
<IsEnabled>true</IsEnabled><IpRanges><IpRange><StartAddress>192.168.254.100</StartAddress><EndAddress>192.168.254.199</EndAddress></IpRange></IpRanges></IpScope></IpScopes>
<FenceMode>isolated</FenceMode><RetainNetInfoAcrossDeployments>false</RetainNetInfoAcrossDeployments></Configuration><IsDeployed>true</IsDeployed></NetworkConfig>
<NetworkConfig networkName="testing_T6nODiW4-68f68d93-0350-4d86-b40b-6e74dedf994d">
<Link rel="repair" href="https://localhost/api/admin/network/379f083b-4057-4724-a128-ed5bc6672591/action/reset"/><Description/><Configuration><IpScopes><IpScope><IsInherited>true</IsInherited>
<Gateway>192.169.241.253</Gateway><Netmask>255.255.255.0</Netmask><Dns1>192.169.241.102</Dns1><DnsSuffix>corp.local</DnsSuffix><IsEnabled>true</IsEnabled><IpRanges><IpRange>
<StartAddress>192.169.241.115</StartAddress><EndAddress>192.169.241.150</EndAddress></IpRange></IpRanges></IpScope></IpScopes>
<ParentNetwork href="https://localhost/api/admin/network/d4307ff7-0e34-4d41-aab0-4c231a045088" id="d4307ff7-0e34-4d41-aab0-4c231a045088" name="testing_T6nODiW4-68f68d93-0350-4d86-b40b-6e74dedf994d"/><FenceMode>bridged</FenceMode><RetainNetInfoAcrossDeployments>false</RetainNetInfoAcrossDeployments></Configuration>
<IsDeployed>true</IsDeployed></NetworkConfig></NetworkConfigSection><SnapshotSection href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069/snapshotSection" type="application/vnd.vmware.vcloud.snapshotSection+xml" ovf:required="false"><ovf:Info>Snapshot information section</ovf:Info></SnapshotSection><DateCreated>2017-09-21T01:15:31.627-07:00</DateCreated><Owner type="application/vnd.vmware.vcloud.owner+xml">
<User href="https://localhost/api/admin/user/f7b6beba-96db-4674-b187-675ed1873c8c" name="orgadmin" type="application/vnd.vmware.admin.user+xml"/>
</Owner><InMaintenanceMode>false</InMaintenanceMode><Children>
<Vm needsCustomization="false" nestedHypervisorEnabled="false" deployed="true" status="4" name="Test1_vm-69a18104-8413-4cb8-bad7-b5afaec6f9fa" id="urn:vcloud:vm:47d12505-5968-4e16-95a7-18743edb0c8b" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b" type="application/vnd.vmware.vcloud.vm+xml">
<Link rel="power:powerOff" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/power/action/powerOff"/>
<Link rel="power:reboot" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/power/action/reboot"/>
<Link rel="power:reset" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/power/action/reset"/>
<Link rel="power:shutdown" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/power/action/shutdown"/>
<Link rel="power:suspend" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/power/action/suspend"/>
<Link rel="undeploy" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/action/undeploy" type="application/vnd.vmware.vcloud.undeployVAppParams+xml"/>
<Link rel="edit" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b" type="application/vnd.vmware.vcloud.vm+xml"/>
<Link rel="down" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/metadata" type="application/vnd.vmware.vcloud.metadata+xml"/>
<Link rel="down" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/productSections/" type="application/vnd.vmware.vcloud.productSections+xml"/>
<Link rel="down" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/metrics/current" type="application/vnd.vmware.vcloud.metrics.currentUsageSpec+xml"/>
<Link rel="down" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/metrics/historic" type="application/vnd.vmware.vcloud.metrics.historicUsageSpec+xml"/>
<Link rel="metrics" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/metrics/current" type="application/vnd.vmware.vcloud.metrics.currentUsageSpec+xml"/>
<Link rel="metrics" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/metrics/historic" type="application/vnd.vmware.vcloud.metrics.historicUsageSpec+xml"/>
<Link rel="screen:thumbnail" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/screen"/>
<Link rel="screen:acquireTicket" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/screen/action/acquireTicket"/>
<Link rel="screen:acquireMksTicket" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/screen/action/acquireMksTicket" type="application/vnd.vmware.vcloud.mksTicket+xml"/>
<Link rel="media:insertMedia" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/media/action/insertMedia" type="application/vnd.vmware.vcloud.mediaInsertOrEjectParams+xml"/>
<Link rel="media:ejectMedia" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/media/action/ejectMedia" type="application/vnd.vmware.vcloud.mediaInsertOrEjectParams+xml"/>
<Link rel="disk:attach" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/disk/action/attach" type="application/vnd.vmware.vcloud.diskAttachOrDetachParams+xml"/>
<Link rel="disk:detach" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/disk/action/detach" type="application/vnd.vmware.vcloud.diskAttachOrDetachParams+xml"/>
<Link rel="installVmwareTools" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/action/installVMwareTools"/>
<Link rel="customizeAtNextPowerOn" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/action/customizeAtNextPowerOn"/>
<Link rel="snapshot:create" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/action/createSnapshot" type="application/vnd.vmware.vcloud.createSnapshotParams+xml"/>
<Link rel="reconfigureVm" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/action/reconfigureVm" name="Test1_vm-69a18104-8413-4cb8-bad7-b5afaec6f9fa" type="application/vnd.vmware.vcloud.vm+xml"/>
<Link rel="up" href="https://localhost/api/vApp/vapp-4f6a9b49-e92d-4935-87a1-0e4dc9c3a069" type="application/vnd.vmware.vcloud.vApp+xml"/><Description>Ubuntu-vm</Description>  <ovf:VirtualHardwareSection xmlns:vcloud="http://www.vmware.com/vcloud/v1.5" ovf:transport="" vcloud:type="application/vnd.vmware.vcloud.virtualHardwareSection+xml" vcloud:href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/"><ovf:Info>Virtual hardware requirements</ovf:Info><ovf:System><vssd:ElementName>Virtual Hardware Family</vssd:ElementName><vssd:InstanceID>0</vssd:InstanceID>    <vssd:VirtualSystemIdentifier>Test1_vm-69a18104-8413-4cb8-bad7-b5afaec6f9fa</vssd:VirtualSystemIdentifier><vssd:VirtualSystemType>vmx-11</vssd:VirtualSystemType></ovf:System><ovf:Item>    <rasd:Address>00:50:56:01:12:a2</rasd:Address><rasd:AddressOnParent>0</rasd:AddressOnParent>    <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>    <rasd:Connection vcloud:ipAddressingMode="DHCP" vcloud:ipAddress="12.19.21.20" vcloud:primaryNetworkConnection="true">testing_T6nODiW4-68f68d93-0350-4d86-b40b-6e74dedf994d</rasd:Connection>    <rasd:Description>Vmxnet3 ethernet adapter on "testing_T6nODiW4-68f68d93-0350-4d86-b40b-6e74dedf994d"</rasd:Description>    <rasd:ElementName>Network adapter 0</rasd:ElementName>    <rasd:InstanceID>1</rasd:InstanceID>    <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>    <rasd:ResourceType>10</rasd:ResourceType></ovf:Item><ovf:Item>    <rasd:Address>0</rasd:Address>    <rasd:Description>SCSI Controller</rasd:Description>    <rasd:ElementName>SCSI Controller 0</rasd:ElementName>    <rasd:InstanceID>2</rasd:InstanceID>    <rasd:ResourceSubType>lsilogic</rasd:ResourceSubType>    <rasd:ResourceType>6</rasd:ResourceType></ovf:Item><ovf:Item>    <rasd:AddressOnParent>0</rasd:AddressOnParent>    <rasd:Description>Hard disk</rasd:Description>    <rasd:ElementName>Hard disk 1</rasd:ElementName>    <rasd:HostResource vcloud:storageProfileHref="https://localhost/api/vdcStorageProfile/950701fb-2b8a-4808-80f1-27d1170a2bfc" vcloud:busType="6" vcloud:busSubType="lsilogic" vcloud:capacity="40960" vcloud:storageProfileOverrideVmDefault="false"/>    <rasd:InstanceID>2000</rasd:InstanceID>    <rasd:Parent>2</rasd:Parent>    <rasd:ResourceType>17</rasd:ResourceType>    <rasd:VirtualQuantity>42949672960</rasd:VirtualQuantity>    <rasd:VirtualQuantityUnits>byte</rasd:VirtualQuantityUnits></ovf:Item><ovf:Item>    <rasd:Address>0</rasd:Address>    <rasd:Description>SATA Controller</rasd:Description>    <rasd:ElementName>SATA Controller 0</rasd:ElementName>    <rasd:InstanceID>3</rasd:InstanceID>    <rasd:ResourceSubType>vmware.sata.ahci</rasd:ResourceSubType>    <rasd:ResourceType>20</rasd:ResourceType></ovf:Item><ovf:Item>    <rasd:AddressOnParent>0</rasd:AddressOnParent>    <rasd:AutomaticAllocation>false</rasd:AutomaticAllocation>    <rasd:Description>CD/DVD Drive</rasd:Description>    <rasd:ElementName>CD/DVD Drive 1</rasd:ElementName>    <rasd:HostResource/>    <rasd:InstanceID>16000</rasd:InstanceID>    <rasd:Parent>3</rasd:Parent>    <rasd:ResourceType>15</rasd:ResourceType></ovf:Item><ovf:Item>    <rasd:AddressOnParent>0</rasd:AddressOnParent>    <rasd:AutomaticAllocation>false</rasd:AutomaticAllocation>    <rasd:Description>Floppy Drive</rasd:Description>    <rasd:ElementName>Floppy Drive 1</rasd:ElementName>    <rasd:HostResource/>    <rasd:InstanceID>8000</rasd:InstanceID>    <rasd:ResourceType>14</rasd:ResourceType></ovf:Item><ovf:Item vcloud:type="application/vnd.vmware.vcloud.rasdItem+xml" vcloud:href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/cpu">    <rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>    <rasd:Description>Number of Virtual CPUs</rasd:Description>    <rasd:ElementName>1 virtual CPU(s)</rasd:ElementName>    <rasd:InstanceID>4</rasd:InstanceID>    <rasd:Reservation>0</rasd:Reservation>    <rasd:ResourceType>3</rasd:ResourceType>    <rasd:VirtualQuantity>1</rasd:VirtualQuantity>    <rasd:Weight>0</rasd:Weight>    <vmw:CoresPerSocket ovf:required="false">1</vmw:CoresPerSocket>    <Link rel="edit" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/cpu" type="application/vnd.vmware.vcloud.rasdItem+xml"/></ovf:Item><ovf:Item vcloud:type="application/vnd.vmware.vcloud.rasdItem+xml" vcloud:href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/memory">    <rasd:AllocationUnits>byte * 2^20</rasd:AllocationUnits>    <rasd:Description>Memory Size</rasd:Description>    <rasd:ElementName>1024 MB of memory</rasd:ElementName>    <rasd:InstanceID>5</rasd:InstanceID>    <rasd:Reservation>0</rasd:Reservation>    <rasd:ResourceType>4</rasd:ResourceType>    <rasd:VirtualQuantity>1024</rasd:VirtualQuantity>    <rasd:Weight>0</rasd:Weight>    <Link rel="edit" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/memory" type="application/vnd.vmware.vcloud.rasdItem+xml"/></ovf:Item><Link rel="edit" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/" type="application/vnd.vmware.vcloud.virtualHardwareSection+xml"/><Link rel="down" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/cpu" type="application/vnd.vmware.vcloud.rasdItem+xml"/>
<Link rel="edit" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/cpu" type="application/vnd.vmware.vcloud.rasdItem+xml"/>
<Link rel="down" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/memory" type="application/vnd.vmware.vcloud.rasdItem+xml"/>
<Link rel="edit" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/memory" type="application/vnd.vmware.vcloud.rasdItem+xml"/>
<Link rel="down" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/disks" type="application/vnd.vmware.vcloud.rasdItemsList+xml"/>
<Link rel="edit" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/disks" type="application/vnd.vmware.vcloud.rasdItemsList+xml"/><Link rel="down" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/media" type="application/vnd.vmware.vcloud.rasdItemsList+xml"/><Link rel="down" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/networkCards" type="application/vnd.vmware.vcloud.rasdItemsList+xml"/><Link rel="edit" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/networkCards" type="application/vnd.vmware.vcloud.rasdItemsList+xml"/><Link rel="down" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/serialPorts" type="application/vnd.vmware.vcloud.rasdItemsList+xml"/><Link rel="edit" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/virtualHardwareSection/serialPorts" type="application/vnd.vmware.vcloud.rasdItemsList+xml"/></ovf:VirtualHardwareSection><ovf:OperatingSystemSection xmlns:vcloud="http://www.vmware.com/vcloud/v1.5" ovf:id="94" vcloud:type="application/vnd.vmware.vcloud.operatingSystemSection+xml" vmw:osType="ubuntu64Guest" vcloud:href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/operatingSystemSection/"><ovf:Info>Specifies the operating system installed</ovf:Info><ovf:Description>Ubuntu Linux (64-bit)</ovf:Description><Link rel="edit" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/operatingSystemSection/" type="application/vnd.vmware.vcloud.operatingSystemSection+xml"/></ovf:OperatingSystemSection><NetworkConnectionSection href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/networkConnectionSection/" type="application/vnd.vmware.vcloud.networkConnectionSection+xml" ovf:required="false"><ovf:Info>Specifies the available VM network connections</ovf:Info><PrimaryNetworkConnectionIndex>0</PrimaryNetworkConnectionIndex><NetworkConnection needsCustomization="false" network="testing_T6nODiW4-68f68d93-0350-4d86-b40b-6e74dedf994d">    <NetworkConnectionIndex>0</NetworkConnectionIndex>    <IpAddress>12.19.21.20</IpAddress>    <IsConnected>true</IsConnected>    <MACAddress>00:50:56:01:12:a2</MACAddress>    <IpAddressAllocationMode>DHCP</IpAddressAllocationMode></NetworkConnection><Link rel="edit" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/networkConnectionSection/" type="application/vnd.vmware.vcloud.networkConnectionSection+xml"/></NetworkConnectionSection><GuestCustomizationSection href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/guestCustomizationSection/" type="application/vnd.vmware.vcloud.guestCustomizationSection+xml" ovf:required="false"><ovf:Info>Specifies Guest OS Customization Settings</ovf:Info><Enabled>true</Enabled><ChangeSid>false</ChangeSid><VirtualMachineId>47d12505-5968-4e16-95a7-18743edb0c8b</VirtualMachineId><JoinDomainEnabled>false</JoinDomainEnabled><UseOrgSettings>false</UseOrgSettings><AdminPasswordEnabled>false</AdminPasswordEnabled><AdminPasswordAuto>true</AdminPasswordAuto><AdminAutoLogonEnabled>false</AdminAutoLogonEnabled><AdminAutoLogonCount>0</AdminAutoLogonCount><ResetPasswordRequired>false</ResetPasswordRequired><ComputerName>Ubuntu-vm-001</ComputerName><Link rel="edit" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/guestCustomizationSection/" type="application/vnd.vmware.vcloud.guestCustomizationSection+xml"/></GuestCustomizationSection><RuntimeInfoSection xmlns:vcloud="http://www.vmware.com/vcloud/v1.5" vcloud:type="application/vnd.vmware.vcloud.virtualHardwareSection+xml" vcloud:href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/runtimeInfoSection"><ovf:Info>Specifies Runtime info</ovf:Info><VMWareTools version="2147483647"/></RuntimeInfoSection><SnapshotSection href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/snapshotSection" type="application/vnd.vmware.vcloud.snapshotSection+xml" ovf:required="false"><ovf:Info>Snapshot information section</ovf:Info></SnapshotSection><DateCreated>2017-09-21T01:15:53.863-07:00</DateCreated><VAppScopedLocalId>Ubuntu-vm</VAppScopedLocalId><ovfenv:Environment xmlns:ns11="http://www.vmware.com/schema/ovfenv" ovfenv:id="" ns11:vCenterId="vm-7833"><ovfenv:PlatformSection>    <ovfenv:Kind>VMware ESXi</ovfenv:Kind>    <ovfenv:Version>6.0.0</ovfenv:Version>    <ovfenv:Vendor>VMware, Inc.</ovfenv:Vendor>    <ovfenv:Locale>en</ovfenv:Locale></ovfenv:PlatformSection><ovfenv:PropertySection>    <ovfenv:Property ovfenv:key="vCloud_UseSysPrep" ovfenv:value="None"/>    <ovfenv:Property ovfenv:key="vCloud_bitMask" ovfenv:value="1"/>    <ovfenv:Property ovfenv:key="vCloud_bootproto_0" ovfenv:value="dhcp"/>    <ovfenv:Property ovfenv:key="vCloud_computerName" ovfenv:value="Ubuntu-vm-001"/>    <ovfenv:Property ovfenv:key="vCloud_macaddr_0" ovfenv:value="00:50:56:01:12:a2"/>    <ovfenv:Property ovfenv:key="vCloud_markerid" ovfenv:value="c743cbe8-136e-4cf8-9e42-b291646b8058"/>    <ovfenv:Property ovfenv:key="vCloud_numnics" ovfenv:value="1"/>    <ovfenv:Property ovfenv:key="vCloud_primaryNic" ovfenv:value="0"/>    <ovfenv:Property ovfenv:key="vCloud_reconfigToken" ovfenv:value="246124151"/>    <ovfenv:Property ovfenv:key="vCloud_resetPassword" ovfenv:value="0"/></ovfenv:PropertySection><ve:EthernetAdapterSection xmlns:ve="http://www.vmware.com/schema/ovfenv" xmlns="http://schemas.dmtf.org/ovf/environment/1" xmlns:oe="http://schemas.dmtf.org/ovf/environment/1">    <ve:Adapter ve:mac="00:50:56:01:12:a2" ve:network="DPG-MGMT-3151" ve:unitNumber="7"/></ve:EthernetAdapterSection></ovfenv:Environment><VmCapabilities href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/vmCapabilities/" type="application/vnd.vmware.vcloud.vmCapabilitiesSection+xml"><Link rel="edit" href="https://localhost/api/vApp/vm-47d12505-5968-4e16-95a7-18743edb0c8b/vmCapabilities/" type="application/vnd.vmware.vcloud.vmCapabilitiesSection+xml"/><MemoryHotAddEnabled>false</MemoryHotAddEnabled><CpuHotAddEnabled>false</CpuHotAddEnabled></VmCapabilities><StorageProfile href="https://localhost/api/vdcStorageProfile/950701fb-2b8a-4808-80f1-27d1170a2bfc" name="*" type="application/vnd.vmware.vcloud.vdcStorageProfile+xml"/></Vm></Children></VApp>"""

poweroff_task_xml = """<?xml version="1.0" encoding="UTF-8"?>
                <Task xmlns="http://www.vmware.com/vcloud/v1.5" cancelRequested="false" expiryTime="2017-12-22T23:18:23.040-08:00" operation="Powering Off Virtual Application Test1_vm-f370dafc-4aad-4415-bad9-68509dda67c9(f26ebf0a-f675-4622-83a6-64c6401769ac)" operationName="vappPowerOff" serviceNamespace="com.vmware.vcloud" startTime="2017-09-23T23:18:23.040-07:00" status="queued" name="task" id="urn:vcloud:task:26975b6e-310e-4ed9-914e-ba7051eaabcb" href="https://localhost/api/task/26975b6e-310e-4ed9-914e-ba7051eaabcb" type="application/vnd.vmware.vcloud.task+xml" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.vmware.com/vcloud/v1.5 http://localhost/api/v1.5/schema/master.xsd">
		<Owner href="https://localhost/api/vApp/vapp-f26ebf0a-f675-4622-83a6-64c6401769ac" name="Test1_vm-f370dafc-4aad-4415-bad9-68509dda67c9" type="application/vnd.vmware.vcloud.vApp+xml"/>
		<User href="https://localhost/api/admin/user/f7b6beba-96db-4674-b187-675ed1873c8c" name="orgadmin" type="application/vnd.vmware.admin.user+xml"/>
		<Organization href="https://localhost/api/org/2cb3dffb-5c51-4355-8406-28553ead28ac" name="Org3" type="application/vnd.vmware.vcloud.org+xml"/>
		<Details/>
		</Task>"""

org_xml_response = """<Org xmlns="http://www.vmware.com/vcloud/v1.5" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" name="Org3" id="urn:vcloud:org:2cb3dffb-5c51-4355-8406-28553ead28ac" href="https://localhost/api/org/2cb3dffb-5c51-4355-8406-28553ead28ac" type="application/vnd.vmware.vcloud.org+xml" xsi:schemaLocation="http://www.vmware.com/vcloud/v1.5 http://localhost/api/v1.5/schema/master.xsd">
<Link rel="down" href="https://localhost/api/vdc/216648ae-1b91-412b-b821-e4c301ff27d2" name="osm" type="application/vnd.vmware.vcloud.vdc+xml"/>
<Link rel="down" href="https://localhost/api/vdc/2584137f-6541-4c04-a2a2-e56bfca14c69" name="Org3-VDC-PVDC1" type="application/vnd.vmware.vcloud.vdc+xml"/>
<Link rel="down" href="https://localhost/api/vdc/414fdda9-3556-478c-a496-2deeec39cd30" name="osm1" type="application/vnd.vmware.vcloud.vdc+xml"/>
<Link rel="down" href="https://localhost/api/tasksList/2cb3dffb-5c51-4355-8406-28553ead28ac" type="application/vnd.vmware.vcloud.tasksList+xml"/>
<Link rel="down" href="https://localhost/api/catalog/4b94b67e-c2c6-49ec-b46c-3f35ba45ca4a" name="cirros034" type="application/vnd.vmware.vcloud.catalog+xml"/>
<Link rel="down" href="https://localhost/api/catalog/4b94b67e-c2c6-49ec-b46c-3f35ba45ca4a/controlAccess/" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="controlAccess" href="https://localhost/api/catalog/4b94b67e-c2c6-49ec-b46c-3f35ba45ca4a/action/controlAccess" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="down" href="https://localhost/api/catalog/34925a30-0f4a-4018-9759-0d6799063b51" name="Ubuntu_1nic" type="application/vnd.vmware.vcloud.catalog+xml"/>
<Link rel="down" href="https://localhost/api/catalog/34925a30-0f4a-4018-9759-0d6799063b51/controlAccess/" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="controlAccess" href="https://localhost/api/catalog/34925a30-0f4a-4018-9759-0d6799063b51/action/controlAccess" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="down" href="https://localhost/api/catalog/d3fa3df2-b311-4571-9138-4c66541d7f46" name="cirros_10" type="application/vnd.vmware.vcloud.catalog+xml"/>
<Link rel="down" href="https://localhost/api/catalog/d3fa3df2-b311-4571-9138-4c66541d7f46/controlAccess/" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="controlAccess" href="https://localhost/api/catalog/d3fa3df2-b311-4571-9138-4c66541d7f46/action/controlAccess" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="down" href="https://localhost/api/catalog/d0eb0b02-718d-42e0-b889-56575000b52d" name="Test_Cirros" type="application/vnd.vmware.vcloud.catalog+xml"/>
<Link rel="down" href="https://localhost/api/catalog/d0eb0b02-718d-42e0-b889-56575000b52d/controlAccess/" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="controlAccess" href="https://localhost/api/catalog/d0eb0b02-718d-42e0-b889-56575000b52d/action/controlAccess" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="down" href="https://localhost/api/catalog/c3b56180-f980-4256-9109-a93168d73ff2" name="de4ffcf2ad21f1a5d0714d6b868e2645" type="application/vnd.vmware.vcloud.catalog+xml"/>
<Link rel="down" href="https://localhost/api/catalog/c3b56180-f980-4256-9109-a93168d73ff2/controlAccess/" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="controlAccess" href="https://localhost/api/catalog/c3b56180-f980-4256-9109-a93168d73ff2/action/controlAccess" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="down" href="https://localhost/api/catalog/b139ed82-7ca4-49fb-9882-5f841f59c890" name="Ubuntu_plugtest-1" type="application/vnd.vmware.vcloud.catalog+xml"/>
<Link rel="down" href="https://localhost/api/catalog/b139ed82-7ca4-49fb-9882-5f841f59c890/controlAccess/" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="controlAccess" href="https://localhost/api/catalog/b139ed82-7ca4-49fb-9882-5f841f59c890/action/controlAccess" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="down" href="https://localhost/api/catalog/e8d953db-8dc9-46d5-9cab-329774cd2ad9" name="Ubuntu_no_nic" type="application/vnd.vmware.vcloud.catalog+xml"/>
<Link rel="down" href="https://localhost/api/catalog/e8d953db-8dc9-46d5-9cab-329774cd2ad9/controlAccess/" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="controlAccess" href="https://localhost/api/catalog/e8d953db-8dc9-46d5-9cab-329774cd2ad9/action/controlAccess" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="down" href="https://localhost/api/catalog/b31e6973-86d2-404b-a522-b16846d099dc" name="Ubuntu_Cat" type="application/vnd.vmware.vcloud.catalog+xml"/>
<Link rel="down" href="https://localhost/api/catalog/b31e6973-86d2-404b-a522-b16846d099dc/controlAccess/" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="down" href="https://localhost/api/catalog/d64b2617-ea4b-4b90-910b-102c99dd2031" name="Ubuntu16" type="application/vnd.vmware.vcloud.catalog+xml"/>
<Link rel="down" href="https://localhost/api/catalog/d64b2617-ea4b-4b90-910b-102c99dd2031/controlAccess/" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="controlAccess" href="https://localhost/api/catalog/d64b2617-ea4b-4b90-910b-102c99dd2031/action/controlAccess" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="add" href="https://localhost/api/admin/org/2cb3dffb-5c51-4355-8406-28553ead28ac/catalogs" type="application/vnd.vmware.admin.catalog+xml"/>
<Link rel="down" href="https://localhost/api/network/090ffa68-9be6-4d74-af45-9a071544a633" name="default.cirros_ns.cirros_nsd_vld1-73a7d683-af17-49ff-95d3-72f8feb25537" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/17f3a12f-16f8-44a1-99e9-9a0122a7ac41" name="default.ass.management-3979591d-ea4e-4254-b4c4-4052107e4aca" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/326aee79-4f5c-439c-8ead-1bbfa42d2e51" name="default.Testvm11.management-fe46ba91-3b36-4964-9ad2-e91b475b3d23" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/420c24c7-89e9-49e5-ba6d-d21bfb9af94b" name="cirros_nsd_vld1-ea8aec47-0a6c-4fdb-814f-7a743e31407a" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/42cba4fd-7baa-4f53-bda0-b36dada672d0" name="default.cirros_ns.cirros_nsd_vld1-44dff01a-2bdb-4096-a916-7e9826bfa401" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/4ae9fec5-7ed0-4d5e-b0f3-f5289bdf6471" name="default.cirros_ns.cirros_nsd_vld1-9f547589-37b7-4d7d-8890-8d3dd479ff5b" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/4b2ecfa9-6a70-4fe4-9d79-b3f74df91e85" name="default.cirros_ns.cirros_nsd_vld1-43852bce-6109-4949-b63a-deec9d7daab2" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/693f72af-ae42-42e5-956e-25723628bf26" name="default.cirros_ns.cirros_nsd_vld1-8cd70d26-ba81-4a04-aa82-67a994b3e21c" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/6d9fbd4c-f0b9-4033-a13f-a7c8990b01de" name="default.vcd.management-f05b9ad3-7480-4ee6-ab8d-92b1f3c0b265" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/6e3e9f57-cee4-433a-883b-0bbe9760e99d" name="default" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/7787cdd7-9577-4966-ba72-8fbbff5d2553" name="default.cirros_ns.cirros_nsd_vld1-ab1f2288-ff59-488c-af02-c8d5e34e0847" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/7fa723e3-cd6c-4680-9522-e644eb31a188" name="default.cirros_ns.cirros_nsd_vld1-285865bb-736c-4b3d-8618-d755928daf5c" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/9030a222-4562-43a0-abc6-aa60c7c1aae0" name="default.cirros_ns.cirros_nsd_vld1-57248151-de72-4313-a84f-b090d8c3feb8" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/a4bd508c-1325-41b0-8c25-61cb7b83cde7" name="default.cirros_ns.cirros_nsd_vld1-491dfb8d-6b4b-41ab-b3e8-a5148e110bba" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/a719292f-0a7f-4e03-a346-183f23f3e60c" name="default.cirros_ns.cirros_nsd_vld1-7ba57204-eed1-4dc8-8698-60a71bbae715" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/a73574ef-16d4-4357-adbf-a0997eb5eb75" name="default.cirros_ns.cirros_nsd_vld1-4430f367-3fc8-4367-9bf1-96dbc244abe6" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/a94e9ba0-e959-47d6-87c0-70e8cb1b485a" name="default.cirros_ns.cirros_nsd_vld1-c56c51c5-e5a8-44fe-9d36-1f2cbd9a7137" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/ab88a587-ff82-4fa7-8225-c0e3eddbf6e6" name="cirros_nsd_vld1-0ed4b7e9-dd56-4f8b-b92f-829b9de95f66" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/b141d722-c96b-4ac5-90da-3d407d376431" name="cirros_nsd_vld1-ad2ebea3-7a0b-4995-91bb-c16bc6fd4b0e" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/c4d61fd6-4d1e-446c-949f-9eb42e0ccc63" name="default.cirros_ns.cirros_nsd_vld1-021a0669-1833-4a0b-a782-30ceed2cca7a" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/cd466f6f-fdc5-404a-9136-320aaa9e3c16" name="default.cirros_ns.cirros_nsd_vld1-22e6962e-6488-47ad-bfad-41bc599abfcd" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/cde04227-8f87-4956-b1f1-9f1be1241b8b" name="default.cirros_ns.cirros_nsd_vld1-629da038-a216-48c5-9ae2-aa4d5dea057c" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/e9812bec-ded8-423d-9807-354adc5720aa" name="default.cirros_ns.cirros_nsd_vld1-ba7fcc4f-fa76-49b1-8fa0-2b0791141fdd" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/eec8ef17-e379-4e40-a743-4ecec6afe616" name="cirros_nsd_vld1-aa9832d6-7d7a-4ac9-be56-cd171063818b" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/ef16d51c-3a54-4eea-bc15-9aa1e92b140f" name="default.cirros_ns.cirros_nsd_vld1-fe7170ad-0b0a-491d-b585-4de31e758ad7" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/f1554f21-4a7b-40be-9a34-a1b640c13398" name="default.Test21.cirros_nsd_vld1-c8f2b860-6794-4c8e-9a5b-3f107f23bbc4" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/fcbbf40a-6578-4054-b496-f10504b94b21" name="default.cirros_ns.cirros_nsd_vld1-a3021c0f-a0fe-413d-9067-cb9182e1f614" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/1fd6421e-929a-4576-bc19-a0c48aea1969" name="default" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/41b8a539-6927-4ec4-a411-aedae8129c45" name="test001.vld2-name-e34e32fd-6d3f-4d24-9d29-e8dab46e515a" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/437258c7-a221-48cd-b889-d24b2fc15087" name="Mgmt-Network-3151" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/bfd56159-9178-4021-a5d8-9ec050569b0c" name="test001.net_internal_name-34602686-3619-4356-98e9-27f6e13e84ad" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/08a0276e-d0fb-4223-92ae-003857ccd38f" name="pytest-09/20/17-05:26:01-cirros_nsd.cirros_nsd_vld1-d6688412-e82a-4cf7-aa77-400beb70dbbf" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/294f2cba-9a81-49c5-bb73-fdaa6644c6ec" name="pytest-09/20/17-03:47:31-cirros_nsd.cirros_nsd_vld1-bd7e8e04-d075-4851-b550-0cf9737c7c8d" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/network/d660e25b-8049-4e8f-a4b8-6811465197d7" name="Ns1.mgmt-dee74b34-51a5-4caa-aafe-d0c896e53828" type="application/vnd.vmware.vcloud.orgNetwork+xml"/>
<Link rel="down" href="https://localhost/api/supportedSystemsInfo/" type="application/vnd.vmware.vcloud.supportedSystemsInfo+xml"/>
<Link rel="down" href="https://localhost/api/org/2cb3dffb-5c51-4355-8406-28553ead28ac/metadata" type="application/vnd.vmware.vcloud.metadata+xml"/>
<Link rel="down" href="https://localhost/api/org/2cb3dffb-5c51-4355-8406-28553ead28ac/hybrid" type="application/vnd.vmware.vcloud.hybridOrg+xml"/>
<Link rel="alternate" href="https://localhost/api/admin/org/2cb3dffb-5c51-4355-8406-28553ead28ac" type="application/vnd.vmware.admin.organization+xml"/>
<Link rel="down" href="https://localhost/api/vdcTemplates" type="application/vnd.vmware.admin.vdcTemplates+xml"/>
<Link rel="instantiate" href="https://localhost/api/org/2cb3dffb-5c51-4355-8406-28553ead28ac/action/instantiate" type="application/vnd.vmware.vcloud.instantiateVdcTemplateParams+xml"/>
<Description/><FullName>Organization 3</FullName>
</Org>
"""

delete_catalog_xml_response = """<?xml version="1.0" encoding="UTF-8"?>\n<Catalog xmlns="http://www.vmware.com/vcloud/v1.5" name="80d8488f67ba1de98b7f485fba6abbd2" id="urn:vcloud:catalog:f3bf3733-465b-419f-b675-52f91d18edbb" href="https://localhost/api/catalog/f3bf3733-465b-419f-b675-52f91d18edbb" type="application/vnd.vmware.vcloud.catalog+xml" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.vmware.com/vcloud/v1.5 http://localhost/api/v1.5/schema/master.xsd">
<Link rel="up" href="https://localhost/api/org/2cb3dffb-5c51-4355-8406-28553ead28ac" type="application/vnd.vmware.vcloud.org+xml"/>
<Link rel="down" href="https://localhost/api/catalog/f3bf3733-465b-419f-b675-52f91d18edbb/metadata" type="application/vnd.vmware.vcloud.metadata+xml"/>
<Link rel="add" href="https://localhost/api/catalog/f3bf3733-465b-419f-b675-52f91d18edbb/catalogItems" type="application/vnd.vmware.vcloud.catalogItem+xml"/>
<Link rel="add" href="https://localhost/api/catalog/f3bf3733-465b-419f-b675-52f91d18edbb/action/upload" type="application/vnd.vmware.vcloud.media+xml"/>
<Link rel="add" href="https://localhost/api/catalog/f3bf3733-465b-419f-b675-52f91d18edbb/action/upload" type="application/vnd.vmware.vcloud.uploadVAppTemplateParams+xml"/>
<Link rel="copy" href="https://localhost/api/catalog/f3bf3733-465b-419f-b675-52f91d18edbb/action/copy" type="application/vnd.vmware.vcloud.copyOrMoveCatalogItemParams+xml"/>
<Link rel="move" href="https://localhost/api/catalog/f3bf3733-465b-419f-b675-52f91d18edbb/action/move" type="application/vnd.vmware.vcloud.copyOrMoveCatalogItemParams+xml"/>
<Link rel="add" href="https://localhost/api/catalog/f3bf3733-465b-419f-b675-52f91d18edbb/action/captureVApp" type="application/vnd.vmware.vcloud.captureVAppParams+xml"/>
<Link rel="down" href="https://localhost/api/catalog/f3bf3733-465b-419f-b675-52f91d18edbb/controlAccess/" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Link rel="controlAccess" href="https://localhost/api/catalog/f3bf3733-465b-419f-b675-52f91d18edbb/action/controlAccess" type="application/vnd.vmware.vcloud.controlAccess+xml"/>
<Description>80d8488f67ba1de98b7f485fba6abbd2</Description>
<CatalogItems>
    <CatalogItem href="https://localhost/api/catalogItem/8a984fdd-d2cb-4d58-a739-2ea12560aded" id="8a984fdd-d2cb-4d58-a739-2ea12560aded" name="80d8488f67ba1de98b7f485fba6abbd2" type="application/vnd.vmware.vcloud.catalogItem+xml"/>
</CatalogItems>
<IsPublished>
    false
</IsPublished>
<DateCreated>2017-09-24T02:30:23.623-07:00</DateCreated>
<VersionNumber>2</VersionNumber>
</Catalog>"""

delete_catalog_item_xml_response = """<?xml version="1.0" encoding="UTF-8"?>
<CatalogItem xmlns="http://www.vmware.com/vcloud/v1.5" size="0" name="80d8488f67ba1de98b7f485fba6abbd2" id="urn:vcloud:catalogitem:8a984fdd-d2cb-4d58-a739-2ea12560aded" href="https://localhost/api/catalogItem/8a984fdd-d2cb-4d58-a739-2ea12560aded" type="application/vnd.vmware.vcloud.catalogItem+xml" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.vmware.com/vcloud/v1.5 http://localhost/api/v1.5/schema/master.xsd">
<Link rel="up" href="https://localhost/api/catalog/f3bf3733-465b-419f-b675-52f91d18edbb" type="application/vnd.vmware.vcloud.catalog+xml"/>
<Link rel="down" href="https://localhost/api/catalogItem/8a984fdd-d2cb-4d58-a739-2ea12560aded/metadata" type="application/vnd.vmware.vcloud.metadata+xml"/>
<Link rel="edit" href="https://localhost/api/catalogItem/8a984fdd-d2cb-4d58-a739-2ea12560aded" type="application/vnd.vmware.vcloud.catalogItem+xml"/>
<Link rel="remove" href="https://localhost/api/catalogItem/8a984fdd-d2cb-4d58-a739-2ea12560aded"/>    <Description>medial_file_name vApp Template</Description>
<Entity href="https://localhost/api/vAppTemplate/vappTemplate-2731194b-637a-45f5-8e6d-dc65690302f7" name="80d8488f67ba1de98b7f485fba6abbd2" type="application/vnd.vmware.vcloud.vAppTemplate+xml"/>   <DateCreated>2017-09-24T02:30:26.380-07:00</DateCreated>
<VersionNumber>1</VersionNumber>
</CatalogItem>"""

undeploy_task_xml = """<Task xmlns="http://www.vmware.com/vcloud/v1.5" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" cancelRequested="false" expiryTime="2018-07-17T23:53:10.781-07:00" operation="Stopping Virtual Application Test1_vm-5e6dbb30-41ea-4290-951d-6ce2a7412d46(86d9dd50-9c07-4fc5-84ce-aefb5de7b8ed)" operationName="vappUndeployPowerOff" serviceNamespace="com.vmware.vcloud" startTime="2018-04-18T23:53:10.781-07:00" status="queued" name="task" id="urn:vcloud:task:5ca0a79f-c025-47b9-9f20-b6a04fd67ea3" href="https://localhost/api/task/5ca0a79f-c025-47b9-9f20-b6a04fd67ea3" type="application/vnd.vmware.vcloud.task+xml" xsi:schemaLocation="http://www.vmware.com/vcloud/v1.5 http://localhost/api/v1.5/schema/master.xsd">
<Owner href="https://localhost/api/vApp/vapp-86d9dd50-9c07-4fc5-84ce-aefb5de7b8ed" name="Test1_vm-5e6dbb30-41ea-4290-951d-6ce2a7412d46" type="application/vnd.vmware.vcloud.vApp+xml"/>
<User href="https://localhost/api/admin/user/f7b6beba-96db-4674-b187-675ed1873c8c" name="orgadmin" type="application/vnd.vmware.admin.user+xml"/>
<Organization href="https://localhost/api/org/2cb3dffb-5c51-4355-8406-28553ead28ac" name="Org3" type="application/vnd.vmware.vcloud.org+xml"/>
<Details/>
</Task>
"""

delete_task_xml = """<Task xmlns="http://www.vmware.com/vcloud/v1.5" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" cancelRequested="false" expiryTime="2018-07-17T23:54:11.696-07:00" operation="Deleting Virtual Application Test1_vm-5e6dbb30-41ea-4290-951d-6ce2a7412d46(86d9dd50-9c07-4fc5-84ce-aefb5de7b8ed)" operationName="vdcDeleteVapp" serviceNamespace="com.vmware.vcloud" startTime="2018-04-18T23:54:11.696-07:00" status="queued" name="task" id="urn:vcloud:task:f0399f4e-ddd5-4050-959f-5970ba0a63e6" href="https://localhost/api/task/f0399f4e-ddd5-4050-959f-5970ba0a63e6" type="application/vnd.vmware.vcloud.task+xml" xsi:schemaLocation="http://www.vmware.com/vcloud/v1.5 http://localhost/api/v1.5/schema/master.xsd">
<Owner href="https://localhost/api/vApp/vapp-86d9dd50-9c07-4fc5-84ce-aefb5de7b8ed" name="Test1_vm-5e6dbb30-41ea-4290-951d-6ce2a7412d46" type="application/vnd.vmware.vcloud.vApp+xml"/>
<User href="https://localhost/api/admin/user/f7b6beba-96db-4674-b187-675ed1873c8c" name="orgadmin" type="application/vnd.vmware.admin.user+xml"/>
<Organization href="https://localhost/api/org/2cb3dffb-5c51-4355-8406-28553ead28ac" name="Org3" type="application/vnd.vmware.vcloud.org+xml"/>
<Details/>
</Task>"""

status_task_xml = """<Task xmlns="http://www.vmware.com/vcloud/v1.5" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" cancelRequested="false" endTime="2018-04-19T01:24:46.643-07:00" expiryTime="2018-07-18T01:24:39.363-07:00" operation="Powered Off Virtual Application Test1_vm-fa13aee3-fb79-456f-8ce9-17f029ec4324(e9765c7a-b0de-4663-9db9-028bf0031f4d)" operationName="vappPowerOff" serviceNamespace="com.vmware.vcloud" startTime="2018-04-19T01:24:39.363-07:00" status="success" name="task" id="urn:vcloud:task:17ebe394-b419-4612-ab55-cad3000d780a" href="https://localhost/api/task/17ebe394-b419-4612-ab55-cad3000d780a" type="application/vnd.vmware.vcloud.task+xml" xsi:schemaLocation="http://www.vmware.com/vcloud/v1.5 http://localhost/api/v1.5/schema/master.xsd">
<Owner href="https://localhost/api/vApp/vapp-e9765c7a-b0de-4663-9db9-028bf0031f4d" name="Test1_vm-fa13aee3-fb79-456f-8ce9-17f029ec4324" type="application/vnd.vmware.vcloud.vApp+xml"/>
<User href="https://localhost/api/admin/user/f7b6beba-96db-4674-b187-675ed1873c8c" name="orgadmin" type="application/vnd.vmware.admin.user+xml"/>
<Organization href="https://localhost/api/org/2cb3dffb-5c51-4355-8406-28553ead28ac" name="Org3" type="application/vnd.vmware.vcloud.org+xml"/>
<Details/>
</Task>
"""

vm_xml_response = """<?xml version="1.0" encoding="UTF-8"?>
<Vm xmlns="http://www.vmware.com/vcloud/v1.5" xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData" xmlns:vmw="http://www.vmware.com/schema/ovf" xmlns:ovfenv="http://schemas.dmtf.org/ovf/environment/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" needsCustomization="false" nestedHypervisorEnabled="false" deployed="true" status="4" name="Ubuntu_no_nic" id="urn:vcloud:vm:53a529b2-10d8-4d56-a7ad-8182acdbe71c" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c" type="application/vnd.vmware.vcloud.vm+xml" xsi:schemaLocation="http://schemas.dmtf.org/ovf/envelope/1 http://schemas.dmtf.org/ovf/envelope/1/dsp8023_1.1.0.xsd http://www.vmware.com/vcloud/v1.5 http://localhost/api/v1.5/schema/master.xsd http://www.vmware.com/schema/ovf http://www.vmware.com/schema/ovf http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2.22.0/CIM_ResourceAllocationSettingData.xsd http://schemas.dmtf.org/ovf/environment/1 http://schemas.dmtf.org/ovf/envelope/1/dsp8027_1.1.0.xsd http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2.22.0/CIM_VirtualSystemSettingData.xsd">
<Link rel="power:powerOff" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/power/action/powerOff"/>
<Link rel="power:reboot" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/power/action/reboot"/>    <Link rel="power:reset" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/power/action/reset"/>
<Link rel="power:shutdown" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/power/action/shutdown"/>
<Link rel="power:suspend" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/power/action/suspend"/> <Link rel="undeploy" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/action/undeploy" type="application/vnd.vmware.vcloud.undeployVAppParams+xml"/>
<Link rel="edit" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c" type="application/vnd.vmware.vcloud.vm+xml"/>
<Link rel="down" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/metadata" type="application/vnd.vmware.vcloud.metadata+xml"/>
<Link rel="down" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/productSections/" type="application/vnd.vmware.vcloud.productSections+xml"/>
<Link rel="down" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/metrics/current" type="application/vnd.vmware.vcloud.metrics.currentUsageSpec+xml"/>
<Link rel="down" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/metrics/historic" type="application/vnd.vmware.vcloud.metrics.historicUsageSpec+xml"/>
<Link rel="metrics" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/metrics/current" type="application/vnd.vmware.vcloud.metrics.currentUsageSpec+xml"/>
<Link rel="metrics" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/metrics/historic" type="application/vnd.vmware.vcloud.metrics.historicUsageSpec+xml"/>
<Link rel="screen:thumbnail" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/screen"/>
<Link rel="screen:acquireTicket" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/screen/action/acquireTicket"/>
<Link rel="screen:acquireMksTicket" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/screen/action/acquireMksTicket" type="application/vnd.vmware.vcloud.mksTicket+xml"/>
<Link rel="media:insertMedia" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/media/action/insertMedia" type="application/vnd.vmware.vcloud.mediaInsertOrEjectParams+xml"/>
<Link rel="media:ejectMedia" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/media/action/ejectMedia" type="application/vnd.vmware.vcloud.mediaInsertOrEjectParams+xml"/>
<Link rel="disk:attach" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/disk/action/attach" type="application/vnd.vmware.vcloud.diskAttachOrDetachParams+xml"/>
<Link rel="disk:detach" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/disk/action/detach" type="application/vnd.vmware.vcloud.diskAttachOrDetachParams+xml"/>
<Link rel="installVmwareTools" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/action/installVMwareTools"/>
<Link rel="customizeAtNextPowerOn" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/action/customizeAtNextPowerOn"/>
<Link rel="snapshot:create" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/action/createSnapshot" type="application/vnd.vmware.vcloud.createSnapshotParams+xml"/>
<Link rel="reconfigureVm" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/action/reconfigureVm" name="Ubuntu_no_nic" type="application/vnd.vmware.vcloud.vm+xml"/>
<Link rel="up" href="https://localhost/api/vApp/vapp-5a5ca3da-3826-4fe4-83c5-c018ad1765fa" type="application/vnd.vmware.vcloud.vApp+xml"/>
<Description/>
<ovf:VirtualHardwareSection xmlns:vcloud="http://www.vmware.com/vcloud/v1.5" ovf:transport="" vcloud:type="application/vnd.vmware.vcloud.virtualHardwareSection+xml" vcloud:href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/">
<ovf:Info>Virtual hardware requirements</ovf:Info>
<ovf:System>
<vssd:ElementName>Virtual Hardware Family</vssd:ElementName>
<vssd:InstanceID>0</vssd:InstanceID>
<vssd:VirtualSystemIdentifier>Ubuntu_no_nic</vssd:VirtualSystemIdentifier>
<vssd:VirtualSystemType>vmx-11</vssd:VirtualSystemType>
</ovf:System><ovf:Item>
<rasd:Address>00:50:56:01:14:1a</rasd:Address>
<rasd:AddressOnParent>0</rasd:AddressOnParent>
<rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
<rasd:Connection vcloud:ipAddressingMode="DHCP" vcloud:ipAddress="172.16.27.72" vcloud:primaryNetworkConnection="true">testing_6SNBKa9pz62P-63e13553-ebf9-4518-a33d-6ea922a6d2ce</rasd:Connection>
<rasd:Description>Vmxnet3 ethernet adapter on "testing_6SNBKa9pz62P-63e13553-ebf9-4518-a33d-6ea922a6d2ce"
</rasd:Description><rasd:ElementName>Network adapter 0</rasd:ElementName>
<rasd:InstanceID>1</rasd:InstanceID>
<rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
<rasd:ResourceType>10</rasd:ResourceType></ovf:Item><ovf:Item>
<rasd:Address>0</rasd:Address><rasd:Description>SCSI Controller</rasd:Description>
<rasd:ElementName>SCSI Controller 0</rasd:ElementName>
<rasd:InstanceID>2</rasd:InstanceID>
<rasd:ResourceSubType>lsilogic</rasd:ResourceSubType>
<rasd:ResourceType>6</rasd:ResourceType></ovf:Item><ovf:Item>
<rasd:AddressOnParent>0</rasd:AddressOnParent>
<rasd:Description>Hard disk</rasd:Description>
<rasd:ElementName>Hard disk 1</rasd:ElementName>
<rasd:HostResource vcloud:storageProfileHref="https://localhost/api/vdcStorageProfile/950701fb-2b8a-4808-80f1-27d1170a2bfc" vcloud:busType="6" vcloud:busSubType="lsilogic" vcloud:capacity="10240" vcloud:storageProfileOverrideVmDefault="false"/>      <rasd:InstanceID>2000</rasd:InstanceID>
<rasd:Parent>2</rasd:Parent><rasd:ResourceType>17</rasd:ResourceType>
<rasd:VirtualQuantity>10737418240</rasd:VirtualQuantity>
<rasd:VirtualQuantityUnits>byte</rasd:VirtualQuantityUnits>
</ovf:Item><ovf:Item><rasd:Address>1</rasd:Address>
<rasd:Description>IDE Controller</rasd:Description>
<rasd:ElementName>IDE Controller 1</rasd:ElementName>
<rasd:InstanceID>3</rasd:InstanceID>
<rasd:ResourceType>5</rasd:ResourceType>
</ovf:Item><ovf:Item><rasd:AddressOnParent>0</rasd:AddressOnParent>
<rasd:AutomaticAllocation>false</rasd:AutomaticAllocation>
<rasd:Description>CD/DVD Drive</rasd:Description>
<rasd:ElementName>CD/DVD Drive 1</rasd:ElementName><rasd:HostResource/>
<rasd:InstanceID>3002</rasd:InstanceID>
<rasd:Parent>3</rasd:Parent>
<rasd:ResourceType>15</rasd:ResourceType></ovf:Item><ovf:Item>
<rasd:AddressOnParent>0</rasd:AddressOnParent>
<rasd:AutomaticAllocation>false</rasd:AutomaticAllocation>
<rasd:Description>Floppy Drive</rasd:Description>
<rasd:ElementName>Floppy Drive 1</rasd:ElementName>
<rasd:HostResource/><rasd:InstanceID>8000</rasd:InstanceID>
<rasd:ResourceType>14</rasd:ResourceType>
</ovf:Item>
<ovf:Item vcloud:type="application/vnd.vmware.vcloud.rasdItem+xml" vcloud:href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/cpu">
<rasd:AllocationUnits>hertz * 10^6</rasd:AllocationUnits>
<rasd:Description>Number of Virtual CPUs</rasd:Description>
<rasd:ElementName>1 virtual CPU(s)</rasd:ElementName>
<rasd:InstanceID>4</rasd:InstanceID>
<rasd:Reservation>0</rasd:Reservation>
<rasd:ResourceType>3</rasd:ResourceType>
<rasd:VirtualQuantity>1</rasd:VirtualQuantity>
<rasd:Weight>0</rasd:Weight>
<vmw:CoresPerSocket ovf:required="false">1</vmw:CoresPerSocket>
<Link rel="edit" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/cpu" type="application/vnd.vmware.vcloud.rasdItem+xml"/></ovf:Item>
<ovf:Item vcloud:type="application/vnd.vmware.vcloud.rasdItem+xml" vcloud:href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/memory">
<rasd:AllocationUnits>byte * 2^20</rasd:AllocationUnits>
<rasd:Description>Memory Size</rasd:Description>
<rasd:ElementName>1024 MB of memory</rasd:ElementName>
<rasd:InstanceID>5</rasd:InstanceID>
<rasd:Reservation>0</rasd:Reservation>
<rasd:ResourceType>4</rasd:ResourceType>
<rasd:VirtualQuantity>1024</rasd:VirtualQuantity>
<rasd:Weight>0</rasd:Weight>
<Link rel="edit" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/memory" type="application/vnd.vmware.vcloud.rasdItem+xml"/>
        </ovf:Item>
        <Link rel="edit" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/" type="application/vnd.vmware.vcloud.virtualHardwareSection+xml"/>
        <Link rel="down" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/cpu" type="application/vnd.vmware.vcloud.rasdItem+xml"/>
        <Link rel="edit" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/cpu" type="application/vnd.vmware.vcloud.rasdItem+xml"/>
        <Link rel="down" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/memory" type="application/vnd.vmware.vcloud.rasdItem+xml"/>
        <Link rel="edit" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/memory" type="application/vnd.vmware.vcloud.rasdItem+xml"/>
        <Link rel="down" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/disks" type="application/vnd.vmware.vcloud.rasdItemsList+xml"/>
        <Link rel="edit" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/disks" type="application/vnd.vmware.vcloud.rasdItemsList+xml"/>
        <Link rel="down" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/media" type="application/vnd.vmware.vcloud.rasdItemsList+xml"/>
        <Link rel="down" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/networkCards" type="application/vnd.vmware.vcloud.rasdItemsList+xml"/>
        <Link rel="edit" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/networkCards" type="application/vnd.vmware.vcloud.rasdItemsList+xml"/>
        <Link rel="down" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/serialPorts" type="application/vnd.vmware.vcloud.rasdItemsList+xml"/>
        <Link rel="edit" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/virtualHardwareSection/serialPorts" type="application/vnd.vmware.vcloud.rasdItemsList+xml"/>
    </ovf:VirtualHardwareSection>
    <ovf:OperatingSystemSection xmlns:vcloud="http://www.vmware.com/vcloud/v1.5" ovf:id="94" vcloud:type="application/vnd.vmware.vcloud.operatingSystemSection+xml" vmw:osType="ubuntu64Guest" vcloud:href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/operatingSystemSection/">
        <ovf:Info>Specifies the operating system installed</ovf:Info>
        <ovf:Description>Ubuntu Linux (64-bit)</ovf:Description>
        <Link rel="edit" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/operatingSystemSection/" type="application/vnd.vmware.vcloud.operatingSystemSection+xml"/>
    </ovf:OperatingSystemSection>
    <NetworkConnectionSection href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/networkConnectionSection/" type="application/vnd.vmware.vcloud.networkConnectionSection+xml" ovf:required="false">
        <ovf:Info>Specifies the available VM network connections</ovf:Info>
        <PrimaryNetworkConnectionIndex>0</PrimaryNetworkConnectionIndex>
        <NetworkConnection needsCustomization="false" network="testing_6SNBKa9pz62P-63e13553-ebf9-4518-a33d-6ea922a6d2ce">
            <NetworkConnectionIndex>0</NetworkConnectionIndex>
            <IpAddress>172.16.27.72</IpAddress>
            <IsConnected>true</IsConnected>
            <MACAddress>00:50:56:01:14:1a</MACAddress>
            <IpAddressAllocationMode>DHCP</IpAddressAllocationMode>
            <NetworkAdapterType>VMXNET3</NetworkAdapterType>
        </NetworkConnection>
        <Link rel="edit" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/networkConnectionSection/" type="application/vnd.vmware.vcloud.networkConnectionSection+xml"/>
    </NetworkConnectionSection>  
    <NetworkConnectionSection href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/networkConnectionSection/" type="application/vnd.vmware.vcloud.networkConnectionSection+xml" ovf:required="false">
        <ovf:Info>Specifies the available VM network connections</ovf:Info>
        <PrimaryNetworkConnectionIndex>0</PrimaryNetworkConnectionIndex>
        <NetworkConnection needsCustomization="false" network="testing_6SNBKa9pz62P-63e13553-ebf9-4518-a33d-6ea922a6d2ce">
            <NetworkConnectionIndex>0</NetworkConnectionIndex>
            <IpAddress>172.16.27.72</IpAddress>
            <IsConnected>true</IsConnected>
            <MACAddress>00:50:56:01:14:1a</MACAddress>
            <IpAddressAllocationMode>DHCP</IpAddressAllocationMode>
        </NetworkConnection>
        <Link rel="edit" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/networkConnectionSection/" type="application/vnd.vmware.vcloud.networkConnectionSection+xml"/>
    </NetworkConnectionSection>
    <GuestCustomizationSection href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/guestCustomizationSection/" type="application/vnd.vmware.vcloud.guestCustomizationSection+xml" ovf:required="false">
        <ovf:Info>Specifies Guest OS Customization Settings</ovf:Info>
        <Enabled>true</Enabled>
        <ChangeSid>false</ChangeSid>
        <VirtualMachineId>53a529b2-10d8-4d56-a7ad-8182acdbe71c</VirtualMachineId>
        <JoinDomainEnabled>false</JoinDomainEnabled>
        <UseOrgSettings>false</UseOrgSettings>
        <AdminPasswordEnabled>false</AdminPasswordEnabled>
        <AdminPasswordAuto>true</AdminPasswordAuto>
        <AdminAutoLogonEnabled>false</AdminAutoLogonEnabled>
        <AdminAutoLogonCount>0</AdminAutoLogonCount>
        <ResetPasswordRequired>false</ResetPasswordRequired>
        <ComputerName>Ubuntunonic-001</ComputerName>
        <Link rel="edit" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/guestCustomizationSection/" type="application/vnd.vmware.vcloud.guestCustomizationSection+xml"/>
    </GuestCustomizationSection>
    <RuntimeInfoSection xmlns:vcloud="http://www.vmware.com/vcloud/v1.5" vcloud:type="application/vnd.vmware.vcloud.virtualHardwareSection+xml" vcloud:href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/runtimeInfoSection">
        <ovf:Info>Specifies Runtime info</ovf:Info>
        <VMWareTools version="2147483647"/>
    </RuntimeInfoSection>
    <SnapshotSection href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/snapshotSection" type="application/vnd.vmware.vcloud.snapshotSection+xml" ovf:required="false">
        <ovf:Info>Snapshot information section</ovf:Info>
    </SnapshotSection>
    <DateCreated>2018-04-19T04:19:28.150-07:00</DateCreated>
    <VAppScopedLocalId>Ubuntu_no_nic</VAppScopedLocalId>
    <ovfenv:Environment xmlns:ns11="http://www.vmware.com/schema/ovfenv" ovfenv:id="" ns11:vCenterId="vm-8971">
        <ovfenv:PlatformSection>
<ovfenv:Kind>VMware ESXi</ovfenv:Kind>
<ovfenv:Version>6.0.0</ovfenv:Version>
<ovfenv:Vendor>VMware, Inc.</ovfenv:Vendor>
<ovfenv:Locale>en</ovfenv:Locale>
        </ovfenv:PlatformSection>
        <ovfenv:PropertySection>
<ovfenv:Property ovfenv:key="vCloud_UseSysPrep" ovfenv:value="None"/>
<ovfenv:Property ovfenv:key="vCloud_bitMask" ovfenv:value="1"/>
<ovfenv:Property ovfenv:key="vCloud_bootproto_0" ovfenv:value="dhcp"/>
<ovfenv:Property ovfenv:key="vCloud_computerName" ovfenv:value="Ubuntunonic-001"/>
<ovfenv:Property ovfenv:key="vCloud_macaddr_0" ovfenv:value="00:50:56:01:14:1a"/>
<ovfenv:Property ovfenv:key="vCloud_markerid" ovfenv:value="ec8b90ea-cb5d-43b4-8910-91380ff29d97"/>
<ovfenv:Property ovfenv:key="vCloud_numnics" ovfenv:value="1"/>
<ovfenv:Property ovfenv:key="vCloud_primaryNic" ovfenv:value="0"/>
<ovfenv:Property ovfenv:key="vCloud_reconfigToken" ovfenv:value="132681259"/>
<ovfenv:Property ovfenv:key="vCloud_resetPassword" ovfenv:value="0"/>
        </ovfenv:PropertySection>
        <ve:EthernetAdapterSection xmlns:ve="http://www.vmware.com/schema/ovfenv" xmlns="http://schemas.dmtf.org/ovf/environment/1" xmlns:oe="http://schemas.dmtf.org/ovf/environment/1">
<ve:Adapter ve:mac="00:50:56:01:14:1a" ve:network="DPG-MGMT-3151" ve:unitNumber="7"/>
   
        </ve:EthernetAdapterSection>
    </ovfenv:Environment>
    <VmCapabilities href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/vmCapabilities/" type="application/vnd.vmware.vcloud.vmCapabilitiesSection+xml">
        <Link rel="edit" href="https://localhost/api/vApp/vm-53a529b2-10d8-4d56-a7ad-8182acdbe71c/vmCapabilities/" type="application/vnd.vmware.vcloud.vmCapabilitiesSection+xml"/>
        <MemoryHotAddEnabled>false</MemoryHotAddEnabled>
        <CpuHotAddEnabled>false</CpuHotAddEnabled>
    </VmCapabilities>
    <StorageProfile href="https://localhost/api/vdcStorageProfile/950701fb-2b8a-4808-80f1-27d1170a2bfc" name="*" type="application/vnd.vmware.vcloud.vdcStorageProfile+xml"/>
</Vm>"""
