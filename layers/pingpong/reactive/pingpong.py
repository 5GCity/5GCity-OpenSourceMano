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


@when('pingpong.configured')
@when('actions.start')
def start():
    err = ''
    try:
        cmd = "service {} start".format(cfg['mode'])
        result, err = charms.sshproxy._run(cmd)
    except:
        action_fail('command failed:' + err)
    else:
        action_set({'outout': result})
    finally:
        remove_flag('actions.start')


@when('pingpong.configured')
@when('actions.stop')
def stop():
    err = ''
    try:
        # Enter the command to stop your service(s)
        cmd = "service {} stop".format(cfg['mode'])
        result, err = charms.sshproxy._run(cmd)
    except:
        action_fail('command failed:' + err)
    else:
        action_set({'outout': result})
    finally:
        remove_flag('actions.stop')


@when('pingpong.configured')
@when('actions.restart')
def restart():
    err = ''
    try:
        # Enter the command to restart your service(s)
        cmd = "service {} restart".format(cfg['mode'])
        result, err = charms.sshproxy._run(cmd)
    except:
        action_fail('command failed:' + err)
    else:
        action_set({'outout': result})
    finally:
        remove_flag('actions.restart')


@when('pingpong.configured')
@when('actions.set-server')
def set_server():
    err = ''
    try:
        # Get the target service info
        target_ip = action_get('server-ip')
        target_port = action_get('server-port')

        data = json.dumps({'ip': target_ip, 'port': target_port})

        cmd = format_curl(
            'POST',
            '/server',
            data,
        )

        result, err = charms.sshproxy._run(cmd)
    except Exception as err:
        print("error: {0}".format(err))
        action_fail('command failed:' + err)
    else:
        action_set({'outout': result})
    finally:
        remove_flag('actions.set-server')


@when('pingpong.configured')
@when('actions.set-rate')
def set_rate():
    err = ''
    try:
        if is_ping():
            rate = action_get('rate')
            cmd = format_curl('POST', '/rate', '{"rate": {}}'.format(rate))

            result, err = charms.sshproxy._run(cmd)
    except:
        action_fail('command failed:' + err)
    else:
        action_set({'outout': result})
    finally:
        remove_flag('actions.set-rate')


@when('pingpong.configured')
@when('actions.get-rate')
def get_rate():
    err = ''
    try:
        if is_ping():
            cmd = format_curl('GET', '/rate')

            result, err = charms.sshproxy._run(cmd)
    except:
        action_fail('command failed:' + err)
    else:
        action_set({'outout': result})
    finally:
        remove_flag('actions.get-rate')


@when('pingpong.configured')
@when('actions.get-state')
def get_state():
    err = ''
    try:
        cmd = format_curl('GET', '/state')

        result, err = charms.sshproxy._run(cmd)
    except:
        action_fail('command failed:' + err)
    else:
        action_set({'outout': result})
    finally:
        remove_flag('actions.get-state')


@when('pingpong.configured')
@when('actions.get-stats')
def get_stats():
    err = ''
    try:
        cmd = format_curl('GET', '/stats')

        result, err = charms.sshproxy._run(cmd)
    except:
        action_fail('command failed:' + err)
    else:
        action_set({'outout': result})
    finally:
        remove_flag('actions.get-stats')


@when('pingpong.configured')
@when('actions.start-ping')
def start_ping():
    err = ''
    try:
        cmd = format_curl('POST', '/adminstatus/state', '{"enable":true}')

        result, err = charms.sshproxy._run(cmd)
    except:
        action_fail('command failed:' + err)
    else:
        action_set({'outout': result})
    finally:
        remove_flag('actions.start-ping')


@when('pingpong.configured')
@when('actions.stop-ping')
def stop_ping():
    err = ''
    try:
        cmd = format_curl('POST', '/adminstatus/state', '{"enable":false}')

        result, err = charms.sshproxy._run(cmd)
    except:
        action_fail('command failed:' + err)
    else:
        action_set({'outout': result})
    finally:
        remove_flag('actions.stop-ping')


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
           '-H', '"Accept: application/vnd.yang.data+xml"',
           '-H', '"Content-Type: application/vnd.yang.data+json"',
           '-X', method]

    if method == "POST" and data:
        cmd.append('-d')
        cmd.append("'{}'".format(data))

    cmd.append(
        'http://{}:{}/api/v1/{}{}'.format(host, port, mode, path)
    )
    return cmd
