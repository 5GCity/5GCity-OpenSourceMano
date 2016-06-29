
import subprocess
import paramiko

from charmhelpers.core.hookenv import (
    config,
    status_set,
    action_get,
    action_set,
    action_fail,
)

from charms.reactive import (
    when,
    when_not,
    set_state as set_flag,
    remove_state as remove_flag,
)


@when('config.changed')
def test_connection():
    status_set('maintenance', 'configuring ssh connection')
    remove_flag('vyos-proxy.ready')
    try:
        who, _ = run('whoami')
    except MgmtNotConfigured as e:
        remove_flag('vyos-proxy.configured')
        status_set('blocked', str(e))
    except subprocess.CalledProcessError as e:
        remove_flag('vyos-proxy.configured')
        status_set('blocked', e.output)
    else:
        set_flag('vyos-proxy.configured')


@when('vyos-proxy.configured')
@when_not('vyos-proxy.ready')
def vyos_proxy_ready():
    status_set('active', 'ready')
    set_flag('vyos-proxy.ready')


@when('action.ping')
@when_not('vyos-proxy.configured')
def pingme():
    action_fail('proxy is not ready')


@when('action.ping')
@when('vyos-proxy.configured')
def pingme_forreal():
    try:
        result, err = run('ping -qc {} {}'.format(action_get('count'), action_get('destination')))
    except:
        action_fail('ping command failed')
    finally:
        remove_flag('action.ping')

    # Here you can send results back from ping, if you had time to parse it
    action_set(result)



class MgmtNotConfigured(Exception):
    pass


def run(cmd):
    ''' Suddenly this project needs to SSH to something. So we replicate what
        _run was doing with subprocess using the Paramiko library. This is
        temporary until this charm /is/ the VPE Router '''

    cfg = config()

    hostname = cfg.get('hostname')
    password = cfg.get('pass')
    username = cfg.get('user')

    if not (username and password and hostname):
        raise MgmtNotConfigured('incomplete remote credentials')

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    client.connect(cfg.get('hostname'), port=22,
                   username=cfg.get('user'), password=cfg.get('pass'))

    stdin, stdout, stderr = client.exec_command(cmd)
    retcode = stdout.channel.recv_exit_status()
    client.close()  # @TODO re-use connections
    if retcode > 0:
        output = stderr.read().strip()
        raise subprocess.CalledProcessError(returncode=retcode, cmd=cmd,
                                            output=output)
    return (''.join(stdout), ''.join(stderr))
