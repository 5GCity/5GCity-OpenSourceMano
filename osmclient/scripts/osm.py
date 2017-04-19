import click
from osmclient.common import OsmAPI
from prettytable import PrettyTable
import pprint
import textwrap

@click.group()
@click.option('--hostname',default=None,envvar='OSM_HOSTNAME',help='hostname of server.  Also can set OSM_HOSTNAME in environment')
@click.pass_context
def cli(ctx,hostname):
    if hostname is None:
        print("either hostname option or OSM_HOSTNAME environment variable needs to be specified") 
        exit(1)
    ctx.obj=OsmAPI.OsmAPI(hostname)

@cli.command(name='ns-list')
@click.pass_context
def ns_list(ctx):
    ctx.obj.list_ns_instance()

@cli.command(name='nsd-list')
@click.pass_context
def nsd_list(ctx):
    ctx.obj.list_ns_catalog()

@cli.command(name='vnfd-list')
@click.pass_context
def vnfd_list(ctx):
    ctx.obj.list_vnf_catalog()

@cli.command(name='vnf-list')
@click.pass_context
def vnf_list(ctx):
    resp=ctx.obj.list_vnfr()
    table=PrettyTable(['vnf name','id','operational status','config Status','mgmt interface','nsr id'])
    if resp is not None:
        for vnfr in resp['vnfr:vnfr']:
            if not 'mgmt-interface' in vnfr:
                vnfr['mgmt-interface'] = {}
                vnfr['mgmt-interface']['ip-address'] = None
            table.add_row([vnfr['name'],vnfr['id'],vnfr['operational-status'],vnfr['config-status'],vnfr['mgmt-interface']['ip-address'],vnfr['nsr-id-ref']])
        table.align='l'
    print(table)

@cli.command(name='vnf-monitoring-show')
@click.argument('vnf_name')
@click.pass_context
def vnf_monitoring_show(ctx,vnf_name):
    resp=ctx.obj.get_vnf_monitoring(vnf_name)
    table=PrettyTable(['vnf name','monitoring name','value','units'])
    if resp is not None:
        for monitor in resp:
            table.add_row([vnf_name,monitor['name'],monitor['value-integer'],monitor['units']])
    table.align='l'
    print(table)

@cli.command(name='ns-monitoring-show')
@click.argument('ns_name')
@click.pass_context
def ns_monitoring_show(ctx,ns_name):
    resp=ctx.obj.get_ns_monitoring(ns_name)
    table=PrettyTable(['vnf name','monitoring name','value','units'])
    if resp is not None:
        for key,val in resp.items():
            for monitor in val:
                table.add_row([key,monitor['name'],monitor['value-integer'],monitor['units']])
    table.align='l'
    print(table)

@cli.command(name='ns-create')
@click.argument('nsd_name')
@click.argument('ns_name')
@click.argument('vim_account')
@click.option('--admin_status',default='ENABLED',help='administration status')
@click.option('--ssh_keys',default=None,help='comma separated list of keys to inject to vnfs')
@click.option('--vim_network_prefix',default=None,help='vim network name prefix')
@click.pass_context
def ns_create(ctx,nsd_name,ns_name,vim_account,admin_status,ssh_keys,vim_network_prefix):
    ctx.obj.instantiate_ns(nsd_name,ns_name,vim_network_prefix=vim_network_prefix,ssh_keys=ssh_keys,account=vim_account)

@cli.command(name='ns-delete')
@click.argument('ns_name')
@click.pass_context
def ns_delete(ctx,ns_name):
    ctx.obj.terminate_ns(ns_name)

'''
@cli.command(name='keypair-list')
@click.pass_context
def keypair_list(ctx):
    resp=ctx.obj.list_key_pair()
    table=PrettyTable(['key Name','key'])
    for kp in resp:
        table.add_row([kp['name'],kp['key']])
    table.align='l'
    print(table)
'''

@cli.command(name='upload-package')
@click.argument('filename')
@click.pass_context
def upload_package(ctx,filename):
    ctx.obj.upload_package(filename)

@cli.command(name='ns-show')
@click.argument('ns_name')
@click.pass_context
def ns_show(ctx,ns_name):
    ctx.obj.show_ns(ns_name)

@cli.command(name='ns-scaling-show')
@click.argument('ns_name')
@click.pass_context
def show_ns_scaling(ctx,ns_name):
    ctx.obj.show_ns_scaling(ns_name)

@cli.command(name='nsd-delete')
@click.argument('nsd_name')
@click.pass_context
def nsd_delete(ctx,nsd_name):
    ctx.obj.delete_nsd(nsd_name)

@cli.command(name='vnfd-delete')
@click.argument('vnfd_name')
@click.pass_context
def nsd_delete(ctx,vnfd_name):
    ctx.obj.delete_vnfd(vnfd_name)

@cli.command(name='config-agent-list')
@click.pass_context
def config_agent_list(ctx):
    table=PrettyTable(['name','account-type','details'])
    for account in ctx.obj.get_config_agents():
      table.add_row([account['name'],account['account-type'],account['juju']])
    table.align='l'
    print(table)

@cli.command(name='config-agent-delete')
@click.argument('name')
@click.pass_context
def config_agent_delete(ctx,name):
    ctx.obj.delete_config_agent(name)

@cli.command(name='config-agent-add')
@click.argument('name')
@click.argument('account_type')
@click.argument('server')
@click.argument('user')
@click.argument('secret')
@click.pass_context
def config_agent_add(ctx,name,account_type,server,user,secret):
    ctx.obj.add_config_agent(name,account_type,server,user,secret)

'''
@cli.command(name='vim-create')
@click.argument('name')
@click.argument('user')
@click.argument('password')
@click.argument('auth_url')
@click.argument('tenant')
@click.argument('mgmt_network')
@click.argument('floating_ip_pool')
@click.option('--account_type',default='openstack')
@click.pass_context
def vim_create(ctx,name,user,password,auth_url,tenant,mgmt_network,floating_ip_pool,account_type):
    ctx.obj.add_vim_account(name,user,password,auth_url,tenant,mgmt_network,floating_ip_pool,account_type)
'''

@cli.command(name='vim-list')
@click.pass_context
def vim_list(ctx):
    resp=ctx.obj.list_vim_accounts()
    table=PrettyTable(['ro-account','datacenter name','uuid'])
    for roaccount in resp:
        for datacenter in roaccount['datacenters']:
            table.add_row([roaccount['name'],datacenter['name'],datacenter['uuid']])
    table.align='l'
    print(table)

@cli.command(name='vcs-list')
@click.pass_context
def vcs_list(ctx):
    resp=ctx.obj.get_vcs_info()
    table=PrettyTable(['component name','state'])
    for component in resp:
        table.add_row([component['component_name'],component['state']])
    table.align='l'
    print(table)

if __name__ == '__main__':
    cli()
