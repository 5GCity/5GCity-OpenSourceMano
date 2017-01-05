from charmhelpers.core.hookenv import (
    action_get,
    action_fail,
    action_set,
    config,
    status_set,
)

from charms.reactive import (
    remove_state as remove_flag,
    set_state as set_flag,
    when,
)
import charms.sshproxy
import json
from subprocess import (
    Popen,
    CalledProcessError,
    PIPE,
)
import time


cfg = config()


@when('config.changed')
def config_changed():
    if all(k in cfg for k in ['mode']):
        if cfg['mode'] in ['ping', 'pong']:
            set_flag('pingpong.configured')
            status_set('active', 'ready!')
            return
    status_set('blocked', 'Waiting for configuration')


def is_ping():
    if cfg['mode'] == 'ping':
        return True
    return False


def is_pong():
    return not is_ping()


def get_port():
    port = 18888
    if is_pong():
        port = 18889
    return port

def run(cmd):
    """ Run a command on the local machine. """
    if isinstance(cmd, str):
        cmd = cmd.split() if ' ' in cmd else [cmd]
    p = Popen(cmd,
              stdout=PIPE,
              stderr=PIPE)
    stdout, stderr = p.communicate()
    retcode = p.poll()
    if retcode > 0:
        raise CalledProcessError(returncode=retcode,
                                 cmd=cmd,
                                 output=stderr.decode("utf-8").strip())
    return (stdout.decode('utf-8').strip(), stderr.decode('utf-8').strip())

@when('pingpong.configured')
@when('actions.start')
def start():
    try:
        # Bring up the eth1 interface.
        # The selinux label on the file needs to be set correctly
        cmd = "sudo /sbin/restorecon -v /etc/sysconfig/network-scripts/ifcfg-eth1"
        result, err = charms.sshproxy._run(cmd)
    except Exception as e:
        err = "{}".format(e)
        action_fail('command failed: {}, errors: {}'.format(err, e.output))
        remove_flag('actions.start')
        return

    try:
        cmd =  "sudo /sbin/ifup eth1"
        result, err = charms.sshproxy._run(cmd)
    except Exception as e:
        action_fail('command failed: {}, errors: {}'.format(e, e.output))
        remove_flag('actions.start')
        return

    try:
        cmd =  "sudo /usr/bin/systemctl start {}". \
              format(cfg['mode'])
        result, err = charms.sshproxy._run(cmd)
    except Exception as e:
        action_fail('command failed: {}, errors: {}'.format(e, e.output))
    else:
        action_set({'stdout': result,
                    'errors': err})
    finally:
        remove_flag('actions.start')


@when('pingpong.configured')
@when('actions.stop')
def stop():
    try:
        # Enter the command to stop your service(s)
        cmd = "sudo /usr/bin/systemctl stop {}".format(cfg['mode'])
        result, err = charms.sshproxy._run(cmd)
    except Exception as e:
        action_fail('command failed: {}, errors: {}'.format(e, e.output))
    else:
        action_set({'stdout': result,
                    'errors': err})
    finally:
        remove_flag('actions.stop')


@when('pingpong.configured')
@when('actions.restart')
def restart():
    try:
        # Enter the command to restart your service(s)
        cmd = "sudo /usr/bin/systemctl restart {}".format(cfg['mode'])
        result, err = charms.sshproxy._run(cmd)
    except Exception as e:
        action_fail('command failed: {}, errors: {}'.format(e, e.output))
    else:
        action_set({'stdout': result,
                    'errors': err})
    finally:
        remove_flag('actions.restart')


@when('pingpong.configured')
@when('actions.set-server')
def set_server():
    try:
        # Get the target service info
        target_ip = action_get('server-ip')
        target_port = action_get('server-port')

        data = '{{"ip" : "{}", "port" : {} }}'. \
               format(target_ip, target_port)

        cmd = format_curl(
            'POST',
            '/server',
            data,
        )

        result, err = run(cmd)
    except Exception as e:
        action_fail('command failed: {}, errors: {}'.format(e, e.output))
    else:
        action_set({'stdout': result,
                    'errors': err})
    finally:
        remove_flag('actions.set-server')


@when('pingpong.configured')
@when('actions.set-rate')
def set_rate():
    try:
        if is_ping():
            rate = action_get('rate')
            cmd = format_curl('POST', '/rate', '{{"rate" : {}}}'.format(rate))

            result, err = run(cmd)
    except Exception as e:
        err = "{}".format(e)
        action_fail('command failed: {}, errors: {}'.format(err, e.output))
    else:
        action_set({'stdout': result,
                    'errors': err})
    finally:
        remove_flag('actions.set-rate')


@when('pingpong.configured')
@when('actions.get-rate')
def get_rate():
    try:
        if is_ping():
            cmd = format_curl('GET', '/rate')

            result, err = run(cmd)
    except Exception as e:
        action_fail('command failed: {}, errors: {}'.format(e, e.output))
    else:
        action_set({'stdout': result,
                    'errors': err})
    finally:
        remove_flag('actions.get-rate')


@when('pingpong.configured')
@when('actions.get-state')
def get_state():
    try:
        cmd = format_curl('GET', '/state')

        result, err = run(cmd)
    except Exception as e:
        action_fail('command failed: {}, errors: {}'.format(e, e.output))
    else:
        action_set({'stdout': result,
                    'errors': err})
    finally:
        remove_flag('actions.get-state')


@when('pingpong.configured')
@when('actions.get-stats')
def get_stats():
    try:
        cmd = format_curl('GET', '/stats')

        result, err = run(cmd)
    except Exception as e:
        action_fail('command failed: {}, errors: {}'.format(e, e.output))
    else:
        action_set({'stdout': result,
                    'errors': err})
    finally:
        remove_flag('actions.get-stats')


@when('pingpong.configured')
@when('actions.start-traffic')
def start_traffic():
    try:
        cmd = format_curl('POST', '/adminstatus/state', '{"enable" : true}')

        result, err = run(cmd)
    except Exception as e:
        action_fail('command failed: {}, errors: {}'.format(e, e.output))
    else:
        action_set({'stdout': result,
                    'errors': err})
    finally:
        remove_flag('actions.start-traffic')


@when('pingpong.configured')
@when('actions.stop-traffic')
def stop_traffic():
    try:
        cmd = format_curl('POST', '/adminstatus/state', '{"enable" : false}')

        result, err = run(cmd)
    except Exception as e:
        action_fail('command failed: {}, errors: {}'.format(e, e.output))
    else:
        action_set({'stdout': result,
                    'errors': err})
    finally:
        remove_flag('actions.stop-traffic')


def format_curl(method, path, data=None):
    """ A utility function to build the curl command line. """

    # method must be GET or POST
    if method not in ['GET', 'POST']:
        # Throw exception
        return None

    # Get our service info
    host = cfg['ssh-hostname']
    port = get_port()
    mode = cfg['mode']

    cmd = ['curl',
           # '-D', '/dev/stdout',
           '-H', 'Accept: application/vnd.yang.data+xml',
           '-H', 'Content-Type: application/vnd.yang.data+json',
           '-X', method]

    if method == "POST" and data:
        cmd.append('-d')
        cmd.append('{}'.format(data))

    cmd.append(
        'http://{}:{}/api/v1/{}{}'.format(host, port, mode, path)
    )
    return cmd
