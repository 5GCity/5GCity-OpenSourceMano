# Copyright 2017 Sandvine
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
OSM shell/cli
"""

import click
from osmclient.client import client
from osmclient.common.exceptions import ClientException
from prettytable import PrettyTable
import json
import time


@click.group()
@click.option('--hostname',
              default=None,
              envvar='OSM_HOSTNAME',
              help='hostname of server.  ' +
                   'Also can set OSM_HOSTNAME in environment')
@click.option('--so-port',
              default=8008,
              envvar='OSM_SO_PORT',
              help='hostname of server.  ' +
                   'Also can set OSM_SO_PORT in environment')
@click.option('--ro-hostname',
              default=None,
              envvar='OSM_RO_HOSTNAME',
              help='hostname of RO server.  ' +
              'Also can set OSM_RO_HOSTNAME in environment')
@click.option('--ro-port',
              default=9090,
              envvar='OSM_RO_PORT',
              help='hostname of RO server.  ' +
                   'Also can set OSM_RO_PORT in environment')
@click.pass_context
def cli(ctx, hostname, so_port, ro_hostname, ro_port):
    if hostname is None:
        print(
            "either hostname option or OSM_HOSTNAME " +
            "environment variable needs to be specified")
        exit(1)
    ctx.obj = client.Client(
        host=hostname,
        so_port=so_port,
        ro_host=ro_hostname,
        ro_port=ro_port)


@cli.command(name='ns-list')
@click.pass_context
def ns_list(ctx):
    resp = ctx.obj.ns.list()
    table = PrettyTable(
        ['ns instance name',
         'id',
         'operational status',
         'config status'])
    for ns in resp:
        nsopdata = ctx.obj.ns.get_opdata(ns['id'])
        nsr = nsopdata['nsr:nsr']
        table.add_row(
            [nsr['name-ref'],
             nsr['ns-instance-config-ref'],
             nsr['operational-status'],
             nsr['config-status']])
    table.align = 'l'
    print(table)


@cli.command(name='nsd-list')
@click.pass_context
def nsd_list(ctx):
    resp = ctx.obj.nsd.list()
    table = PrettyTable(['nsd name', 'id'])
    for ns in resp:
        table.add_row([ns['name'], ns['id']])
    table.align = 'l'
    print(table)


@cli.command(name='vnfd-list')
@click.pass_context
def vnfd_list(ctx):
    resp = ctx.obj.vnfd.list()
    table = PrettyTable(['vnfd name', 'id'])
    for vnfd in resp:
        table.add_row([vnfd['name'], vnfd['id']])
    table.align = 'l'
    print(table)


@cli.command(name='vnf-list')
@click.pass_context
def vnf_list(ctx):
    resp = ctx.obj.vnf.list()
    table = PrettyTable(
        ['vnf name',
         'id',
         'operational status',
         'config status'])
    for vnfr in resp:
        if 'mgmt-interface' not in vnfr:
            vnfr['mgmt-interface'] = {}
            vnfr['mgmt-interface']['ip-address'] = None
        table.add_row(
            [vnfr['name'],
             vnfr['id'],
             vnfr['operational-status'],
             vnfr['config-status']])
    table.align = 'l'
    print(table)


@cli.command(name='vnf-show')
@click.argument('vnf_name')
@click.option('--filter', default=None)
@click.pass_context
def vnf_show(ctx, vnf_name, filter):
    try:
        resp = ctx.obj.vnf.get(vnf_name)
    except ClientException as inst:
        print(inst.message)
        exit(1)

    table = PrettyTable(['field', 'value'])
    for k, v in resp.items():
        if filter is None or filter in k:
            table.add_row([k, json.dumps(v, indent=2)])
    table.align = 'l'
    print(table)


@cli.command(name='vnf-monitoring-show')
@click.argument('vnf_name')
@click.pass_context
def vnf_monitoring_show(ctx, vnf_name):
    try:
        resp = ctx.obj.vnf.get_monitoring(vnf_name)
    except ClientException as inst:
        print(inst.message)
        exit(1)

    table = PrettyTable(['vnf name', 'monitoring name', 'value', 'units'])
    if resp is not None:
        for monitor in resp:
            table.add_row(
                [vnf_name,
                 monitor['name'],
                    monitor['value-integer'],
                    monitor['units']])
    table.align = 'l'
    print(table)


@cli.command(name='ns-monitoring-show')
@click.argument('ns_name')
@click.pass_context
def ns_monitoring_show(ctx, ns_name):
    try:
        resp = ctx.obj.ns.get_monitoring(ns_name)
    except ClientException as inst:
        print(inst.message)
        exit(1)

    table = PrettyTable(['vnf name', 'monitoring name', 'value', 'units'])
    for key, val in resp.items():
        for monitor in val:
            table.add_row(
                [key,
                 monitor['name'],
                    monitor['value-integer'],
                    monitor['units']])
    table.align = 'l'
    print(table)


@cli.command(name='ns-create')
@click.option('--ns_name',
              prompt=True)
@click.option('--nsd_name',
              prompt=True)
@click.option('--vim_account',
              prompt=True)
@click.option('--admin_status',
              default='ENABLED',
              help='administration status')
@click.option('--ssh_keys',
              default=None,
              help='comma separated list of keys to inject to vnfs')
@click.option('--vim_network_prefix',
              default=None,
              help='vim network name prefix')
@click.pass_context
def ns_create(ctx,
              nsd_name,
              ns_name,
              vim_account,
              admin_status,
              ssh_keys,
              vim_network_prefix):
    try:
        ctx.obj.ns.create(
            nsd_name,
            ns_name,
            vim_network_prefix=vim_network_prefix,
            ssh_keys=ssh_keys,
            account=vim_account)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='ns-delete')
@click.argument('ns_name')
@click.pass_context
def ns_delete(ctx, ns_name):
    try:
        ctx.obj.ns.delete(ns_name)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='upload-package')
@click.argument('filename')
@click.pass_context
def upload_package(ctx, filename):
    try:
        ctx.obj.package.upload(filename)
        ctx.obj.package.wait_for_upload(filename)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='ns-show')
@click.argument('ns_name')
@click.option('--filter', default=None)
@click.pass_context
def ns_show(ctx, ns_name, filter):
    try:
        ns = ctx.obj.ns.get(ns_name)
    except ClientException as inst:
        print(inst.message)
        exit(1)

    table = PrettyTable(['field', 'value'])

    for k, v in ns.items():
        if filter is None or filter in k:
            table.add_row([k, json.dumps(v, indent=2)])

    nsopdata = ctx.obj.ns.get_opdata(ns['id'])
    nsr_optdata = nsopdata['nsr:nsr']
    for k, v in nsr_optdata.items():
        if filter is None or filter in k:
            table.add_row([k, json.dumps(v, indent=2)])
    table.align = 'l'
    print(table)


@cli.command(name='ns-scaling-show')
@click.argument('ns_name')
@click.pass_context
def show_ns_scaling(ctx, ns_name):
    resp = ctx.obj.ns.list()

    table = PrettyTable(
        ['group-name',
         'instance-id',
         'operational status',
         'create-time',
         'vnfr ids'])

    for ns in resp:
        if ns_name == ns['name']:
            nsopdata = ctx.obj.ns.get_opdata(ns['id'])
            scaling_records = nsopdata['nsr:nsr']['scaling-group-record']
            for record in scaling_records:
                if 'instance' in record:
                    instances = record['instance']
                    for inst in instances:
                        table.add_row(
                            [record['scaling-group-name-ref'],
                             inst['instance-id'],
                                inst['op-status'],
                                time.strftime('%Y-%m-%d %H:%M:%S',
                                              time.localtime(
                                                  inst['create-time'])),
                                inst['vnfrs']])
    table.align = 'l'
    print(table)


@cli.command(name='ns-scale')
@click.argument('ns_name')
@click.option('--ns_scale_group', prompt=True)
@click.option('--index', prompt=True)
@click.pass_context
def ns_scale(ctx, ns_name, ns_scale_group, index):
    ctx.obj.ns.scale(ns_name, ns_scale_group, index)


@cli.command(name='nsd-delete')
@click.argument('nsd_name')
@click.pass_context
def nsd_delete(ctx, nsd_name):
    try:
        ctx.obj.nsd.delete(nsd_name)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='vnfd-delete')
@click.argument('vnfd_name')
@click.pass_context
def vnfd_delete(ctx, vnfd_name):
    try:
        ctx.obj.vnfd.delete(vnfd_name)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='config-agent-list')
@click.pass_context
def config_agent_list(ctx):
    table = PrettyTable(['name', 'account-type', 'details'])
    for account in ctx.obj.vca.list():
        table.add_row(
            [account['name'],
             account['account-type'],
             account['juju']])
    table.align = 'l'
    print(table)


@cli.command(name='config-agent-delete')
@click.argument('name')
@click.pass_context
def config_agent_delete(ctx, name):
    try:
        ctx.obj.vca.delete(name)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='config-agent-add')
@click.option('--name',
              prompt=True)
@click.option('--account_type',
              prompt=True)
@click.option('--server',
              prompt=True)
@click.option('--user',
              prompt=True)
@click.option('--secret',
              prompt=True,
              hide_input=True,
              confirmation_prompt=True)
@click.pass_context
def config_agent_add(ctx, name, account_type, server, user, secret):
    try:
        ctx.obj.vca.create(name, account_type, server, user, secret)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='vim-create')
@click.option('--name',
              prompt=True)
@click.option('--user',
              prompt=True)
@click.option('--password',
              prompt=True,
              hide_input=True,
              confirmation_prompt=True)
@click.option('--auth_url',
              prompt=True)
@click.option('--tenant',
              prompt=True)
@click.option('--floating_ip_pool',
              default=None)
@click.option('--keypair',
              default=None)
@click.option('--account_type',
              default='openstack')
@click.option('--description',
              default='no description')
@click.pass_context
def vim_create(ctx,
               name,
               user,
               password,
               auth_url,
               tenant,
               floating_ip_pool,
               keypair,
               account_type,
               description):
    vim = {}
    vim['os-username'] = user
    vim['os-password'] = password
    vim['os-url'] = auth_url
    vim['os-project-name'] = tenant
    vim['floating_ip_pool'] = floating_ip_pool
    vim['keypair'] = keypair
    vim['vim-type'] = 'openstack'
    vim['description'] = description
    try:
        ctx.obj.vim.create(name, vim)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='vim-delete')
@click.argument('name')
@click.pass_context
def vim_delete(ctx, name):
    try:
        ctx.obj.vim.delete(name)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='vim-list')
@click.pass_context
def vim_list(ctx):
    resp = ctx.obj.vim.list()
    table = PrettyTable(['vim name', 'uuid'])
    for vim in resp:
        table.add_row([vim['name'], vim['uuid']])
    table.align = 'l'
    print(table)


@cli.command(name='vim-show')
@click.argument('name')
@click.pass_context
def vim_show(ctx, name):
    try:
        resp = ctx.obj.vim.get(name)
    except ClientException as inst:
        print(inst.message)
        exit(1)

    table = PrettyTable(['key', 'attribute'])
    for k, v in resp.items():
        table.add_row([k, json.dumps(v, indent=2)])
    table.align = 'l'
    print(table)


@cli.command(name='ro-dump')
@click.pass_context
def ro_dump(ctx):
    resp = ctx.obj.vim.get_resource_orchestrator()
    table = PrettyTable(['key', 'attribute'])
    for k, v in resp.items():
        table.add_row([k, json.dumps(v, indent=2)])
    table.align = 'l'
    print(table)


@cli.command(name='vcs-list')
@click.pass_context
def vcs_list(ctx):
    resp = ctx.obj.utils.get_vcs_info()
    table = PrettyTable(['component name', 'state'])
    for component in resp:
        table.add_row([component['component_name'], component['state']])
    table.align = 'l'
    print(table)


if __name__ == '__main__':
    cli()
