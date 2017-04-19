from io import BytesIO 
import pycurl
import json
import pprint
import uuid
from prettytable import PrettyTable
import time

class OsmAPI():
    def __init__(self,host,upload_port=8443):
        if host is None:
            raise Exception('missing host specifier')
         
        self._user='admin'
        self._password='admin'
        self._host=host
        self._upload_port=upload_port
        self._url = 'https://{}/'.format(self._host)
        self._upload_url = 'https://{}:{}/'.format(self._host.split(':')[0],self._upload_port)

    def get_curl_cmd(self,url):
        curl_cmd = pycurl.Curl()
        curl_cmd.setopt(pycurl.HTTPGET,1)
        curl_cmd.setopt(pycurl.URL, self._url + url )
        curl_cmd.setopt(pycurl.SSL_VERIFYPEER,0)
        curl_cmd.setopt(pycurl.SSL_VERIFYHOST,0)
        curl_cmd.setopt(pycurl.USERPWD, '{}:{}'.format(self._user,self._password))
        curl_cmd.setopt(pycurl.HTTPHEADER, ['Accept: application/vnd.yand.data+json','Content-Type": "application/vnd.yang.data+json'])
        return curl_cmd

    def get_curl_upload_cmd(self,filename):
        curl_cmd = pycurl.Curl()
        curl_cmd.setopt(pycurl.HTTPPOST,[(('package',(pycurl.FORM_FILE,filename)))])
        curl_cmd.setopt(pycurl.URL, self._upload_url + 'composer/upload?api_server=https://localhost&upload_server=https://' + self._host.split(':')[0])
        curl_cmd.setopt(pycurl.SSL_VERIFYPEER,0)
        curl_cmd.setopt(pycurl.SSL_VERIFYHOST,0)
        curl_cmd.setopt(pycurl.USERPWD, '{}:{}'.format(self._user,self._password))
        return curl_cmd

    def get_ns_opdata(self,id):
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('api/operational/ns-instance-opdata/nsr/{}?deep'.format(id))
        curl_cmd.setopt(pycurl.HTTPGET,1)
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)
        curl_cmd.perform() 
        curl_cmd.close()
        if data.getvalue():
           return json.loads(data.getvalue().decode())
        return None 

    def get_ns_catalog(self):
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('api/running/nsd-catalog/nsd')
        curl_cmd.setopt(pycurl.HTTPGET,1)
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)
        curl_cmd.perform() 
        curl_cmd.close()
        if data.getvalue():
          resp = json.loads(data.getvalue().decode())
          return resp
        return {'nsd:nsd': []}

    def get_config_agents(self):
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('api/config/config-agent')
        curl_cmd.setopt(pycurl.HTTPGET,1)
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)
        curl_cmd.perform() 
        curl_cmd.close()
        if data.getvalue():
          resp = json.loads(data.getvalue().decode())
          if 'rw-config-agent:config-agent' in resp:
            return resp['rw-config-agent:config-agent']['account']
        return list()

    def delete_config_agent(self,name):
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('api/config/config-agent/account/'+name)
        curl_cmd.setopt(pycurl.CUSTOMREQUEST, "DELETE")
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)
        curl_cmd.perform() 
        curl_cmd.close()
        resp = json.loads(data.getvalue().decode())
        pprint.pprint(resp)

    def add_config_agent(self,name,account_type,server,user,secret):
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('api/config/config-agent')
        curl_cmd.setopt(pycurl.POST,1)
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)

        postdata={}
        postdata['account'] = list()

        account={}
        account['name'] = name
        account['account-type'] = account_type
        account['juju'] = {}
        account['juju']['user'] = user 
        account['juju']['secret'] = secret
        account['juju']['ip-address'] = server
        postdata['account'].append(account)

        jsondata=json.dumps(postdata)
        curl_cmd.setopt(pycurl.POSTFIELDS,jsondata)
        curl_cmd.perform() 
        curl_cmd.close()
        resp = json.loads(data.getvalue().decode())
        pprint.pprint(resp)

    def get_ns_instance_list(self):
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('api/running/ns-instance-config')
        curl_cmd.setopt(pycurl.HTTPGET,1)
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)
        curl_cmd.perform() 
        curl_cmd.close()
        resp = json.loads(data.getvalue().decode())
        return resp['nsr:ns-instance-config']

    def get_vnf_catalog(self):
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('api/running/vnfd-catalog/vnfd')
        curl_cmd.setopt(pycurl.HTTPGET,1)
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)
        curl_cmd.perform() 
        curl_cmd.close()
        if data.getvalue():
          resp = json.loads(data.getvalue().decode())
          return resp
        return {'vnfd:vnfd': []}

    def get_vcs_info(self):
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('api/operational/vcs/info')
        curl_cmd.setopt(pycurl.HTTPGET,1)
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)
        curl_cmd.perform() 
        curl_cmd.close()
        if data.getvalue():
          resp = json.loads(data.getvalue().decode())
          return resp['rw-base:info']['components']['component_info']
        return list()

    def get_vnfr_catalog(self):
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('v1/api/operational/vnfr-catalog/vnfr')
        curl_cmd.setopt(pycurl.HTTPGET,1)
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)
        curl_cmd.perform() 
        curl_cmd.close()
        if data.getvalue():
          resp = json.loads(data.getvalue().decode())
          return resp
        return None 

    def get_vnf(self,vnf_name):
        vnfs=self.get_vnfr_catalog()
        for vnf in vnfs['vnfr:vnfr']:
            if vnf_name == vnf['name']:
                return vnf
        return None

    def get_vnf_monitoring(self,vnf_name):
        vnf=self.get_vnf(vnf_name)
        if vnf is not None:
            if 'monitoring-param' in vnf:
                return vnf['monitoring-param'] 
        return None

    def get_ns_monitoring(self,ns_name):
        ns=self.get_ns(ns_name)
        if ns is None:
            raise Exception('cannot find ns {}'.format(ns_name)) 

        vnfs=self.get_vnfr_catalog()
        if vnfs is None:
            return None
        mon_list={}
        for vnf in vnfs['vnfr:vnfr']:
            if ns['id'] == vnf['nsr-id-ref']:
                if 'monitoring-param' in vnf:
                    mon_list[vnf['name']] = vnf['monitoring-param']

        return mon_list 

    def list_key_pair(self):
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('v1/api/config/key-pair?deep')
        curl_cmd.setopt(pycurl.HTTPGET,1)
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)
        curl_cmd.perform() 
        curl_cmd.close()
        resp = json.loads(data.getvalue().decode())
        if 'nsr:key-pair' in resp:
            return resp['nsr:key-pair']
        return list()

    def list_ns_catalog(self):
        resp = self.get_ns_catalog()
        table=PrettyTable(['nsd name','id'])
        for ns in resp['nsd:nsd']:
            table.add_row([ns['name'],ns['id']])
        table.align='l'
        print(table)

    def list_ns_instance(self):
        resp = self.get_ns_instance_list()
        table=PrettyTable(['ns instance name','id','catalog name','operational status','config status'])
        if 'nsr' in resp:
            for ns in resp['nsr']:
                nsopdata=self.get_ns_opdata(ns['id'])
                nsr=nsopdata['nsr:nsr']
                table.add_row([nsr['name-ref'],nsr['ns-instance-config-ref'],nsr['nsd-name-ref'],nsr['operational-status'],nsr['config-status']])
        table.align='l'
        print(table)

    def get_nsd(self,name):
        resp = self.get_ns_catalog()
        for ns in resp['nsd:nsd']:
           if name == ns['name']:
               return ns
        return None 

    def get_vnfd(self,name):
        resp = self.get_vnf_catalog()
        for vnf in resp['vnfd:vnfd']:
           if name == vnf['name']:
               return vnf 
        return None 

    def get_ns(self,name):
        resp=self.get_ns_instance_list()
        for ns in resp['nsr']:
           if name == ns['name']:
               return ns
        return None 
    
    def instantiate_ns(self,nsd_name,nsr_name,account,vim_network_prefix=None,ssh_keys=None,description='default description',admin_status='ENABLED'):
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('api/config/ns-instance-config/nsr')
        curl_cmd.setopt(pycurl.POST,1)
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)

        postdata={}
        postdata['nsr'] = list()
        nsr={}
        nsr['id']=str(uuid.uuid1())

        nsd=self.get_nsd(nsd_name)
        if nsd is None:
            raise Exception('cannot find nsd {}'.format(nsd_name)) 
        
        datacenter=self.get_datacenter(account)
        if datacenter is None:
            raise Exception('cannot find datacenter account {}'.format(account)) 

        nsr['nsd']=nsd
        nsr['name']=nsr_name
        nsr['short-name']=nsr_name
        nsr['description']=description
        nsr['admin-status']=admin_status
        nsr['om-datacenter']=datacenter['uuid']

        if ssh_keys is not None:
            # ssh_keys is comma separate list
            ssh_keys_format=[]
            for key in ssh_keys.split(','):
                ssh_keys_format.append({'key-pair-ref':key})

            nsr['ssh-authorized-key']=ssh_keys_format

        if vim_network_prefix is not None:
            for index,vld in enumerate(nsr['nsd']['vld']):
                network_name = vld['name']
                nsr['nsd']['vld'][index]['vim-network-name'] = '{}-{}'.format(vim_network_prefix,network_name)

        postdata['nsr'].append(nsr)
        jsondata=json.dumps(postdata)
        curl_cmd.setopt(pycurl.POSTFIELDS,jsondata)
        curl_cmd.perform() 
        curl_cmd.close()
        resp = json.loads(data.getvalue().decode())
        pprint.pprint(resp)

    def delete_nsd(self,nsd_name):
        nsd=self.get_nsd(nsd_name)
        if nsd is None:
            raise Exception('cannot find nsd {}'.format(nsd_name)) 
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('api/running/nsd-catalog/nsd/'+nsd['id'])
        curl_cmd.setopt(pycurl.CUSTOMREQUEST, "DELETE")
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)
        curl_cmd.perform() 
        curl_cmd.close()
        resp = json.loads(data.getvalue().decode())
        pprint.pprint(resp)

    def delete_vnfd(self,vnfd_name):
        vnfd=self.get_vnfd(vnfd_name)
        if vnfd is None:
            raise Exception('cannot find vnfd {}'.format(vnfd_name)) 
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('api/running/vnfd-catalog/vnfd/'+vnfd['id'])
        curl_cmd.setopt(pycurl.CUSTOMREQUEST, "DELETE")
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)
        curl_cmd.perform() 
        curl_cmd.close()
        resp = json.loads(data.getvalue().decode())
        pprint.pprint(resp)

    def terminate_ns(self,ns_name):
        ns=self.get_ns(ns_name)
        if ns is None:
            raise Exception('cannot find ns {}'.format(ns_name)) 
  
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('api/config/ns-instance-config/nsr/'+ns['id'])
        curl_cmd.setopt(pycurl.CUSTOMREQUEST, "DELETE")
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)
        curl_cmd.perform() 
        curl_cmd.close()
        resp = json.loads(data.getvalue().decode())
        pprint.pprint(resp)

    def upload_package(self,filename):
        data = BytesIO()
        curl_cmd=self.get_curl_upload_cmd(filename)
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)
        curl_cmd.perform() 
        curl_cmd.close()
        resp = json.loads(data.getvalue().decode())
        pprint.pprint(resp)
      
    def add_vim_account(self,name,user_name,secret,auth_url,tenant,mgmt_network,float_ip_pool,account_type='openstack'):
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('api/config/cloud')
        curl_cmd.setopt(pycurl.POST,1)
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)
        vim_account={}
        vim_account['account']={}

        vim_account['account']['name'] = name
        vim_account['account']['account-type'] = account_type
        vim_account['account'][account_type] = {}
        vim_account['account'][account_type]['key'] = user_name
        vim_account['account'][account_type]['secret'] = secret
        vim_account['account'][account_type]['auth_url'] = auth_url
        vim_account['account'][account_type]['tenant'] = tenant
        vim_account['account'][account_type]['mgmt-network'] = mgmt_network
        vim_account['account'][account_type]['floating-ip-pool'] = float_ip_pool

        jsondata=json.dumps(vim_account)
        curl_cmd.setopt(pycurl.POSTFIELDS,jsondata)
        curl_cmd.perform() 
        curl_cmd.close()
        resp = json.loads(data.getvalue().decode())
        pprint.pprint(resp)

    def list_vim_accounts(self):
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('v1/api/operational/datacenters')
        curl_cmd.setopt(pycurl.HTTPGET,1)
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)
        curl_cmd.perform() 
        curl_cmd.close()
        resp = json.loads(data.getvalue().decode())
        datacenters=resp['rw-launchpad:datacenters']
        if 'ro-accounts' in datacenters:
            return datacenters['ro-accounts']
        return list()

    def get_datacenter(self,name):
        data = BytesIO()
        curl_cmd=self.get_curl_cmd('v1/api/operational/datacenters')
        curl_cmd.setopt(pycurl.HTTPGET,1)
        curl_cmd.setopt(pycurl.WRITEFUNCTION, data.write)
        curl_cmd.perform() 
        curl_cmd.close()
        resp = json.loads(data.getvalue().decode())
        datacenters=resp['rw-launchpad:datacenters']
        if 'ro-accounts' in datacenters:
            for roaccount in datacenters['ro-accounts']:
                if not 'datacenters' in roaccount:
                    continue
                for datacenter in roaccount['datacenters']:
                    if datacenter['name'] == name:
                        return datacenter
        return None

    def show_ns(self,ns_name):
        resp = self.get_ns_instance_list()
        table=PrettyTable(['attribute','value'])

        if 'nsr' in resp:
            for ns in resp['nsr']:
                if ns_name == ns['name']:
                    # dump ns config
                    for k,v in ns.items():
                        table.add_row([k,json.dumps(v,indent=2)])

                    nsopdata=self.get_ns_opdata(ns['id'])
                    nsr_optdata=nsopdata['nsr:nsr']
                    for k,v in nsr_optdata.items():
                        table.add_row([k,json.dumps(v,indent=2)])
        table.align='l'
        print(table)

    def show_ns_scaling(self,ns_name):
        resp = self.get_ns_instance_list()

        table=PrettyTable(['instance-id','operational status','create-time','vnfr ids'])

        if 'nsr' in resp:
            for ns in resp['nsr']:
                if ns_name == ns['name']:
                    nsopdata=self.get_ns_opdata(ns['id'])
                    scaling_records=nsopdata['nsr:nsr']['scaling-group-record']
                    for record in scaling_records:
                        if 'instance' in record:
                            instances=record['instance'] 
                            for inst in instances:
                                table.add_row([inst['instance-id'],inst['op-status'],time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(inst['create-time'])),inst['vnfrs']])
        table.align='l'
        print(table)

    def list_vnfr(self):
        return self.get_vnfr_catalog()

    def list_vnf_catalog(self):
        resp = self.get_vnf_catalog()
        table=PrettyTable(['vnfd name','id'])
        for ns in resp['vnfd:vnfd']:
            table.add_row([ns['name'],ns['id']])
        table.align='l'
        print(table)
