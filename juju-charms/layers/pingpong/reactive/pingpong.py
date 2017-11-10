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
    when_not,
)
import charms.sshproxy
# from subprocess import (
#     Popen,
#     CalledProcessError,
#     PIPE,
# )


cfg = config()


@when_not('pingpong.configured')
def not_configured():
    """Check the current configuration.

    Check the current values in config to see if we have enough
    information to continue.
    """
    config_changed()


@when('config.changed', 'sshproxy.configured')
def config_changed():
    """Verify the configuration.

    Verify that the charm has been configured
    """

    try:
        status_set('maintenance', 'Verifying configuration data...')

        (validated, output) = charms.sshproxy.verify_ssh_credentials()
        if not validated:
            status_set('blocked', 'Unable to verify SSH credentials: {}'.format(
                output
            ))
            return

        if all(k in cfg for k in ['mode']):
            if cfg['mode'] in ['ping', 'pong']:
                set_flag('pingpong.configured')
                status_set('active', 'ready!')
                return
        status_set('blocked', 'Waiting for configuration')

    except Exception as err:
        status_set('blocked', 'Waiting for valid configuration ({})'.format(err))


@when('config.changed')
@when_not('sshproxy.configured')
def invalid_credentials():
    status_set('blocked', 'Waiting for SSH credentials.')
    pass


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
    try:
        # Bring up the eth1 interface.
        # The selinux label on the file needs to be set correctly
        cmd = "sudo timeout 5 /sbin/restorecon -v /etc/sysconfig/network-scripts/ifcfg-eth1"
        result, err = charms.sshproxy._run(cmd)
    except Exception as e:
        err = "{}".format(e)
        action_fail('command failed: {}, errors: {}'.format(err, e.output))
        remove_flag('actions.start')
        return

    # Attempt to raise the non-mgmt interface, but ignore failures if
    # the interface is already up.
    try:
        cmd = "sudo timeout 30 /sbin/ifup eth1"
        result, err = charms.sshproxy._run(cmd)
    except Exception as e:
        pass

    try:
        cmd = "sudo timeout 30 /usr/bin/systemctl start {}". \
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
        cmd = "sudo timeout 30 /usr/bin/systemctl stop {}".format(cfg['mode'])
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
        cmd = "sudo timeout 30 /usr/bin/systemctl restart {}".format(cfg['mode'])
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

        result, err = charms.sshproxy._run(cmd)
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

            result, err = charms.sshproxy._run(cmd)
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

            result, err = charms.sshproxy._run(cmd)
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

        result, err = charms.sshproxy._run(cmd)
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

        result, err = charms.sshproxy._run(cmd)
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

        result, err = charms.sshproxy._run(cmd)
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

        result, err = charms.sshproxy._run(cmd)
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
    host = '127.0.0.1'
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
