# Copyright 2017-2018 Sandvine
# Copyright 2018 Telefonica
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
from osmclient import client
from osmclient.common.exceptions import ClientException
from prettytable import PrettyTable
import yaml
import json
import time

def check_client_version(obj, what, version='sol005'):
    '''
    Checks the version of the client object and raises error if it not the expected.

    :param obj: the client object
    :what: the function or command under evaluation (used when an error is raised)
    :return: -
    :raises ClientError: if the specified version does not match the client version
    '''
    fullclassname = obj.__module__ + "." + obj.__class__.__name__
    message = 'the following commands or options are only supported with the option "--sol005": {}'.format(what)
    if version == 'v1':
        message = 'the following commands or options are not supported when using option "--sol005": {}'.format(what)
    if fullclassname != 'osmclient.{}.client.Client'.format(version):
        raise ClientException(message)
    return

@click.group()
@click.option('--hostname',
              default=None,
              envvar='OSM_HOSTNAME',
              help='hostname of server.  ' +
                   'Also can set OSM_HOSTNAME in environment')
@click.option('--so-port',
              default=None,
              envvar='OSM_SO_PORT',
              help='hostname of server.  ' +
                   'Also can set OSM_SO_PORT in environment')
@click.option('--so-project',
              default=None,
              envvar='OSM_SO_PROJECT',
              help='Project Name in SO.  ' +
                   'Also can set OSM_SO_PROJECT in environment')
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
@click.option('--sol005',
              is_flag=True,
              envvar='OSM_SOL005',
              help='Use ETSI NFV SOL005 API')
@click.pass_context
def cli(ctx, hostname, so_port, so_project, ro_hostname, ro_port, sol005):
    if hostname is None:
        print(
            "either hostname option or OSM_HOSTNAME " +
            "environment variable needs to be specified")
        exit(1)
    kwargs={}
    if so_port is not None:
        kwargs['so_port']=so_port
    if so_project is not None:
        kwargs['so_project']=so_project
    if ro_hostname is not None:
        kwargs['ro_host']=ro_hostname
    if ro_port is not None:
        kwargs['ro_port']=ro_port
    
    ctx.obj = client.Client(host=hostname, sol005=sol005, **kwargs)


####################
# LIST operations
####################

@cli.command(name='ns-list')
@click.option('--filter', default=None,
              help='restricts the list to the NS instances matching the filter')
@click.pass_context
def ns_list(ctx, filter):
    '''list all NS instances'''
    if filter:
        check_client_version(ctx.obj, '--filter option')
        resp = ctx.obj.ns.list(filter)
    else:
        resp = ctx.obj.ns.list()
    table = PrettyTable(
        ['ns instance name',
         'id',
         'operational status',
         'config status'])
    for ns in resp:
        fullclassname = ctx.obj.__module__ + "." + ctx.obj.__class__.__name__
        if fullclassname == 'osmclient.sol005.client.Client':
            nsr = ns
        else:
            nsopdata = ctx.obj.ns.get_opdata(ns['id'])
            nsr = nsopdata['nsr:nsr']
        opstatus = nsr['operational-status'] if 'operational-status' in nsr else 'Not found'
        configstatus = nsr['config-status'] if 'config-status' in nsr else 'Not found'
        if configstatus == "config_not_needed":
            configstatus = "configured (no charms)"
        table.add_row(
            [nsr['name'],
             nsr['_id'],
             opstatus,
             configstatus])
    table.align = 'l'
    print(table)


def nsd_list(ctx, filter):
    if filter:
        check_client_version(ctx.obj, '--filter')
        resp = ctx.obj.nsd.list(filter)
    else:
        resp = ctx.obj.nsd.list()
    #print yaml.safe_dump(resp)
    table = PrettyTable(['nsd name', 'id'])
    fullclassname = ctx.obj.__module__ + "." + ctx.obj.__class__.__name__
    if fullclassname == 'osmclient.sol005.client.Client':
        for ns in resp:
            name = ns['name'] if 'name' in ns else '-'
            table.add_row([name, ns['_id']])
    else:
        for ns in resp:
            table.add_row([ns['name'], ns['id']])
    table.align = 'l'
    print(table)


@cli.command(name='nsd-list')
@click.option('--filter', default=None,
              help='restricts the list to the NSD/NSpkg matching the filter')
@click.pass_context
def nsd_list1(ctx, filter):
    '''list all NSD/NSpkg in the system'''
    nsd_list(ctx,filter)


@cli.command(name='nspkg-list')
@click.option('--filter', default=None,
              help='restricts the list to the NSD/NSpkg matching the filter')
@click.pass_context
def nsd_list2(ctx, filter):
    '''list all NSD/NSpkg in the system'''
    nsd_list(ctx,filter)


def vnfd_list(ctx, filter):
    if filter:
        check_client_version(ctx.obj, '--filter')
        resp = ctx.obj.vnfd.list(filter)
    else:
        resp = ctx.obj.vnfd.list()
    #print yaml.safe_dump(resp)
    table = PrettyTable(['vnfd name', 'id'])
    fullclassname = ctx.obj.__module__ + "." + ctx.obj.__class__.__name__
    if fullclassname == 'osmclient.sol005.client.Client':
        for vnfd in resp:
            name = vnfd['name'] if 'name' in vnfd else '-'
            table.add_row([name, vnfd['_id']])
    else:
        for vnfd in resp:
            table.add_row([vnfd['name'], vnfd['id']])
    table.align = 'l'
    print(table)


@cli.command(name='vnfd-list')
@click.option('--filter', default=None,
              help='restricts the list to the VNFD/VNFpkg matching the filter')
@click.pass_context
def vnfd_list1(ctx, filter):
    '''list all VNFD/VNFpkg in the system'''
    vnfd_list(ctx,filter)


@cli.command(name='vnfpkg-list')
@click.option('--filter', default=None,
              help='restricts the list to the VNFD/VNFpkg matching the filter')
@click.pass_context
def vnfd_list2(ctx, filter):
    '''list all VNFD/VNFpkg in the system'''
    vnfd_list(ctx,filter)


@cli.command(name='vnf-list')
@click.pass_context
def vnf_list(ctx):
    ''' list all VNF instances'''
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


####################
# SHOW operations
####################

def nsd_show(ctx, name, literal):
    try:
        resp = ctx.obj.nsd.get(name)
        #resp = ctx.obj.nsd.get_individual(name)
    except ClientException as inst:
        print(inst.message)
        exit(1)

    if literal:
        print yaml.safe_dump(resp)
        return

    table = PrettyTable(['field', 'value'])
    for k, v in resp.items():
        table.add_row([k, json.dumps(v, indent=2)])
    table.align = 'l'
    print(table)


@cli.command(name='nsd-show', short_help='shows the content of a NSD')
@click.option('--literal', is_flag=True,
              help='print literally, no pretty table')
@click.argument('name')
@click.pass_context
def nsd_show1(ctx, name, literal):
    '''shows the content of a NSD

    NAME: name or ID of the NSD/NSpkg
    '''
    nsd_show(ctx, name, literal)


@cli.command(name='nspkg-show', short_help='shows the content of a NSD')
@click.option('--literal', is_flag=True,
              help='print literally, no pretty table')
@click.argument('name')
@click.pass_context
def nsd_show2(ctx, name, literal):
    '''shows the content of a NSD

    NAME: name or ID of the NSD/NSpkg
    '''
    nsd_show(ctx, name, literal)


def vnfd_show(ctx, name, literal):
    try:
        resp = ctx.obj.vnfd.get(name)
        #resp = ctx.obj.vnfd.get_individual(name)
    except ClientException as inst:
        print(inst.message)
        exit(1)

    if literal:
        print yaml.safe_dump(resp)
        return

    table = PrettyTable(['field', 'value'])
    for k, v in resp.items():
        table.add_row([k, json.dumps(v, indent=2)])
    table.align = 'l'
    print(table)


@cli.command(name='vnfd-show', short_help='shows the content of a VNFD')
@click.option('--literal', is_flag=True,
              help='print literally, no pretty table')
@click.argument('name')
@click.pass_context
def vnfd_show1(ctx, name, literal):
    '''shows the content of a VNFD

    NAME: name or ID of the VNFD/VNFpkg
    '''
    vnfd_show(ctx, name, literal)


@cli.command(name='vnfpkg-show', short_help='shows the content of a VNFD')
@click.option('--literal', is_flag=True,
              help='print literally, no pretty table')
@click.argument('name')
@click.pass_context
def vnfd_show2(ctx, name, literal):
    '''shows the content of a VNFD

    NAME: name or ID of the VNFD/VNFpkg
    '''
    vnfd_show(ctx, name, literal)


@cli.command(name='ns-show', short_help='shows the info of a NS instance')
@click.argument('name')
@click.option('--literal', is_flag=True,
              help='print literally, no pretty table')
@click.option('--filter', default=None)
@click.pass_context
def ns_show(ctx, name, literal, filter):
    '''shows the info of a NS instance

    NAME: name or ID of the NS instance
    '''
    try:
        ns = ctx.obj.ns.get(name)
    except ClientException as inst:
        print(inst.message)
        exit(1)

    if literal:
        print yaml.safe_dump(resp)
        return

    table = PrettyTable(['field', 'value'])

    for k, v in ns.items():
        if filter is None or filter in k:
            table.add_row([k, json.dumps(v, indent=2)])

    fullclassname = ctx.obj.__module__ + "." + ctx.obj.__class__.__name__
    if fullclassname != 'osmclient.sol005.client.Client':
        nsopdata = ctx.obj.ns.get_opdata(ns['id'])
        nsr_optdata = nsopdata['nsr:nsr']
        for k, v in nsr_optdata.items():
            if filter is None or filter in k:
                table.add_row([k, json.dumps(v, indent=2)])
    table.align = 'l'
    print(table)


@cli.command(name='vnf-show', short_help='shows the info of a VNF instance')
@click.argument('name')
@click.option('--literal', is_flag=True,
              help='print literally, no pretty table')
@click.option('--filter', default=None)
@click.pass_context
def vnf_show(ctx, name, literal, filter):
    '''shows the info of a VNF instance

    NAME: name or ID of the VNF instance
    '''
    try:
        check_client_version(ctx.obj, ctx.command.name, 'v1')
        resp = ctx.obj.vnf.get(name)
    except ClientException as inst:
        print(inst.message)
        exit(1)

    if literal:
        print yaml.safe_dump(resp)
        return

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
        check_client_version(ctx.obj, ctx.command.name, 'v1')
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
        check_client_version(ctx.obj, ctx.command.name, 'v1')
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


####################
# CREATE operations
####################

def nsd_create(ctx, filename, overwrite):
    try:
        check_client_version(ctx.obj, ctx.command.name)
        ctx.obj.nsd.create(filename, overwrite)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='nsd-create', short_help='creates a new NSD/NSpkg')
@click.argument('filename')
@click.option('--overwrite', default=None,
              help='overwrites some fields in NSD')
@click.pass_context
def nsd_create1(ctx, filename, overwrite):
    '''creates a new NSD/NSpkg

    FILENAME: NSD yaml file or NSpkg tar.gz file
    '''
    nsd_create(ctx, filename, overwrite)


@cli.command(name='nspkg-create', short_help='creates a new NSD/NSpkg')
@click.argument('filename')
@click.option('--overwrite', default=None,
              help='overwrites some fields in NSD')
@click.pass_context
def nsd_create2(ctx, filename, overwrite):
    '''creates a new NSD/NSpkg

    FILENAME: NSD yaml file or NSpkg tar.gz file
    '''
    nsd_create(ctx, filename, overwrite)


def vnfd_create(ctx, filename, overwrite):
    try:
        check_client_version(ctx.obj, ctx.command.name)
        ctx.obj.vnfd.create(filename, overwrite)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='vnfd-create', short_help='creates a new VNFD/VNFpkg')
@click.argument('filename')
@click.option('--overwrite', default=None,
              help='overwrites some fields in VNFD')
@click.pass_context
def vnfd_create1(ctx, filename, overwrite):
    '''creates a new VNFD/VNFpkg

    FILENAME: VNFD yaml file or VNFpkg tar.gz file
    '''
    vnfd_create(ctx, filename, overwrite)


@cli.command(name='vnfpkg-create', short_help='creates a new VNFD/VNFpkg')
@click.argument('filename')
@click.option('--overwrite', default=None,
              help='overwrites some fields in VNFD')
@click.pass_context
def vnfd_create2(ctx, filename, overwrite):
    '''creates a new VNFD/VNFpkg

    FILENAME: VNFD yaml file or VNFpkg tar.gz file
    '''
    vnfd_create(ctx, filename, overwrite)


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
@click.option('--config',
              default=None,
              help='ns specific yaml configuration')
@click.pass_context
def ns_create(ctx,
              nsd_name,
              ns_name,
              vim_account,
              admin_status,
              ssh_keys,
              config):
    '''creates a new NS instance'''
    try:
        if config:
            check_client_version(ctx.obj, '--config', 'v1')
        ctx.obj.ns.create(
            nsd_name,
            ns_name,
            config=config,
            ssh_keys=ssh_keys,
            account=vim_account)
    except ClientException as inst:
        print(inst.message)
        exit(1)


####################
# UPDATE operations
####################

def nsd_update(ctx, name, content):
    try:
        check_client_version(ctx.obj, ctx.command.name)
        ctx.obj.nsd.update(name, content)
    except ClientException as inst:
        print(inst.message)
        exit(1)

@cli.command(name='nsd-update', short_help='updates a NSD/NSpkg')
@click.argument('name')
@click.option('--content', default=None,
              help='filename with the NSD/NSpkg replacing the current one')
@click.pass_context
def nsd_update1(ctx, name, content):
    '''updates a NSD/NSpkg

    NAME: name or ID of the NSD/NSpkg
    '''
    nsd_update(ctx, name, content)


@cli.command(name='nspkg-update', short_help='updates a NSD/NSpkg')
@click.argument('name')
@click.option('--content', default=None,
              help='filename with the NSD/NSpkg replacing the current one')
@click.pass_context
def nsd_update2(ctx, name, content):
    '''updates a NSD/NSpkg

    NAME: name or ID of the NSD/NSpkg
    '''
    nsd_update(ctx, name, content)


def vnfd_update(ctx, name, content):
    try:
        check_client_version(ctx.obj, ctx.command.name)
        ctx.obj.vnfd.update(name, content)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='vnfd-update', short_help='updates a new VNFD/VNFpkg')
@click.argument('name')
@click.option('--content', default=None,
              help='filename with the VNFD/VNFpkg replacing the current one')
@click.pass_context
def vnfd_update1(ctx, name, content):
    '''updates a VNFD/VNFpkg

    NAME: name or ID of the VNFD/VNFpkg
    '''
    vnfd_update(ctx, name, content)


@cli.command(name='vnfpkg-update', short_help='updates a VNFD/VNFpkg')
@click.argument('name')
@click.option('--content', default=None,
              help='filename with the VNFD/VNFpkg replacing the current one')
@click.pass_context
def vnfd_update2(ctx, name, content):
    '''updates a VNFD/VNFpkg

    NAME: VNFD yaml file or VNFpkg tar.gz file
    '''
    vnfd_update(ctx, name, content)


####################
# DELETE operations
####################

def nsd_delete(ctx, name):
    try:
        ctx.obj.nsd.delete(name)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='nsd-delete', short_help='deletes a NSD/NSpkg')
@click.argument('name')
@click.pass_context
def nsd_delete1(ctx, name):
    '''deletes a NSD/NSpkg

    NAME: name or ID of the NSD/NSpkg to be deleted
    '''
    nsd_delete(ctx, name)


@cli.command(name='nspkg-delete', short_help='deletes a NSD/NSpkg')
@click.argument('name')
@click.pass_context
def nsd_delete2(ctx, name):
    '''deletes a NSD/NSpkg

    NAME: name or ID of the NSD/NSpkg to be deleted
    '''
    nsd_delete(ctx, name)


def vnfd_delete(ctx, name):
    try:
        ctx.obj.vnfd.delete(name)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='vnfd-delete', short_help='deletes a VNFD/VNFpkg')
@click.argument('name')
@click.pass_context
def vnfd_delete1(ctx, name):
    '''deletes a VNFD/VNFpkg

    NAME: name or ID of the VNFD/VNFpkg to be deleted
    '''
    vnfd_delete(ctx, name)


@cli.command(name='vnfpkg-delete', short_help='deletes a VNFD/VNFpkg')
@click.argument('name')
@click.pass_context
def vnfd_delete2(ctx, name):
    '''deletes a VNFD/VNFpkg

    NAME: name or ID of the VNFD/VNFpkg to be deleted
    '''
    vnfd_delete(ctx, name)


@cli.command(name='ns-delete', short_help='deletes a NS instance')
@click.argument('name')
@click.pass_context
def ns_delete(ctx, name):
    '''deletes a NS instance

    NAME: name or ID of the NS instance to be deleted
    '''
    try:
        ctx.obj.ns.delete(name)
    except ClientException as inst:
        print(inst.message)
        exit(1)


####################
# VIM operations
####################
 
@cli.command(name='vim-create')
@click.option('--name',
              prompt=True,
              help='Name to create datacenter')
@click.option('--user',
              prompt=True,
              help='VIM username')
@click.option('--password',
              prompt=True,
              hide_input=True,
              confirmation_prompt=True,
              help='VIM password')
@click.option('--auth_url',
              prompt=True,
              help='VIM url')
@click.option('--tenant',
              prompt=True,
              help='VIM tenant name')
@click.option('--config',
              default=None,
              help='VIM specific config parameters')
@click.option('--account_type',
              default='openstack',
              help='VIM type')
@click.option('--description',
              default='no description',
              help='human readable description')
@click.pass_context
def vim_create(ctx,
               name,
               user,
               password,
               auth_url,
               tenant,
               config,
               account_type,
               description):
    '''creates a new VIM account
    '''
    vim = {}
    vim['vim-username'] = user
    vim['vim-password'] = password
    vim['vim-url'] = auth_url
    vim['vim-tenant-name'] = tenant
    vim['config'] = config
    vim['vim-type'] = account_type
    vim['description'] = description
    try:
        ctx.obj.vim.create(name, vim)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='vim-update', short_help='updates a VIM account')
@click.argument('name')
@click.option('--newname', default=None, help='New name for the VIM account')
@click.option('--user', default=None, help='VIM username')
@click.option('--password', default=None, help='VIM password')
@click.option('--auth_url', default=None, help='VIM url')
@click.option('--tenant', default=None, help='VIM tenant name')
@click.option('--config', default=None, help='VIM specific config parameters')
@click.option('--account_type', default=None, help='VIM type')
@click.option('--description',  default=None, help='human readable description')
@click.pass_context
def vim_update(ctx,
               name,
               newname,
               user,
               password,
               auth_url,
               tenant,
               config,
               account_type,
               description):
    '''updates a VIM account

    NAME: name or ID of the VIM account
    '''
    vim = {}
    if newname:
        vim['name'] = newname
    vim['vim_user'] = user
    vim['vim_password'] = password
    vim['vim_url'] = auth_url
    vim['vim-tenant-name'] = tenant
    vim['config'] = config
    vim['vim_type'] = account_type
    vim['description'] = description
    try:
        check_client_version(ctx.obj, ctx.command.name)
        ctx.obj.vim.update(name, vim)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='vim-delete')
@click.argument('name')
@click.pass_context
def vim_delete(ctx, name):
    '''deletes a VIM account

    NAME: name or ID of the VIM account to be deleted
    '''
    try:
        ctx.obj.vim.delete(name)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='vim-list')
@click.option('--ro_update/--no_ro_update',
              default=False,
              help='update list from RO')
@click.option('--filter', default=None,
              help='restricts the list to the VIM accounts matching the filter')
@click.pass_context
def vim_list(ctx, ro_update, filter):
    '''list all VIM accounts'''
    if filter:
        check_client_version(ctx.obj, '--filter')
    if ro_update:
        check_client_version(ctx.obj, '--ro_update', 'v1')
    fullclassname = ctx.obj.__module__ + "." + ctx.obj.__class__.__name__
    if fullclassname == 'osmclient.sol005.client.Client':
        resp = ctx.obj.vim.list(filter)
    else:
        resp = ctx.obj.vim.list(ro_update)
    table = PrettyTable(['vim name', 'uuid'])
    for vim in resp:
        table.add_row([vim['name'], vim['uuid']])
    table.align = 'l'
    print(table)


@cli.command(name='vim-show')
@click.argument('name')
@click.pass_context
def vim_show(ctx, name):
    '''shows the details of a VIM account

    NAME: name or ID of the VIM account
    '''
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


####################
# Other operations
####################

@cli.command(name='upload-package')
@click.argument('filename')
@click.pass_context
def upload_package(ctx, filename):
    '''uploads a VNF package or NS package

    FILENAME: VNF or NS package file (tar.gz)
    '''
    try:
        ctx.obj.package.upload(filename)
        fullclassname = ctx.obj.__module__ + "." + ctx.obj.__class__.__name__
        if fullclassname != 'osmclient.sol005.client.Client':
            ctx.obj.package.wait_for_upload(filename)
    except ClientException as inst:
        print(inst.message)
        exit(1)


@cli.command(name='ns-scaling-show')
@click.argument('ns_name')
@click.pass_context
def show_ns_scaling(ctx, ns_name):
    check_client_version(ctx.obj, ctx.command.name, 'v1')
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
    check_client_version(ctx.obj, ctx.command.name, 'v1')
    ctx.obj.ns.scale(ns_name, ns_scale_group, index)


@cli.command(name='config-agent-list')
@click.pass_context
def config_agent_list(ctx):
    check_client_version(ctx.obj, ctx.command.name, 'v1')
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
        check_client_version(ctx.obj, ctx.command.name, 'v1')
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
        check_client_version(ctx.obj, ctx.command.name, 'v1')
        ctx.obj.vca.create(name, account_type, server, user, secret)
    except ClientException as inst:
        print(inst.message)
        exit(1)

@cli.command(name='ro-dump')
@click.pass_context
def ro_dump(ctx):
    check_client_version(ctx.obj, ctx.command.name, 'v1')
    resp = ctx.obj.vim.get_resource_orchestrator()
    table = PrettyTable(['key', 'attribute'])
    for k, v in resp.items():
        table.add_row([k, json.dumps(v, indent=2)])
    table.align = 'l'
    print(table)


@cli.command(name='vcs-list')
@click.pass_context
def vcs_list(ctx):
    check_client_version(ctx.obj, ctx.command.name, 'v1')
    resp = ctx.obj.utils.get_vcs_info()
    table = PrettyTable(['component name', 'state'])
    for component in resp:
        table.add_row([component['component_name'], component['state']])
    table.align = 'l'
    print(table)


if __name__ == '__main__':
    cli()
