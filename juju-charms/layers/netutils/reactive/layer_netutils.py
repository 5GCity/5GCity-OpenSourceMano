from charmhelpers.core.hookenv import (
    action_get,
    action_fail,
    action_set,
    config,
    log,
    status_set,
)

from charms.reactive import (
    remove_state as remove_flag,
    set_state as set_flag,
    when,
    when_not,
)
import charms.sshproxy
from subprocess import CalledProcessError


@when_not('netutils.ready')
def ready():
    status_set('active', 'Ready!')
    set_flag('netutils.ready')


@when('actions.dig')
def dig():
    err = ''
    try:
        nsserver = action_get('nsserver')
        host = action_get('host')
        nstype = action_get('type')
        cmd = "dig"

        if nsserver:
            cmd += " @{}".format(nsserver)
        if host:
            cmd += " {}".format(host)
        else:
            action_fail('Hostname required.')
        if nstype:
            cmd += " -t {}".format(nstype)

        result, err = charms.sshproxy._run(cmd)
    except:
        action_fail('dig command failed:' + err)
    else:
        action_set({'outout': result})
    finally:
        remove_flag('actions.dig')


@when('actions.nmap')
def nmap():
    err = ''
    try:
        result, err = charms.sshproxy._run(
            'nmap {}'.format(action_get('destination'))
        )
    except:
        action_fail('nmap command failed:' + err)
    else:
        action_set({'outout': result})
    finally:
        remove_flag('actions.nmap')


@when('actions.ping')
def ping():
    err = ''
    try:
        result, err = charms.sshproxy._run('ping -qc {} {}'.format(
            action_get('count'), action_get('destination'))
        )

    except:
        action_fail('ping command failed:' + err)
    else:
        # Here you can send results back from ping, if you had time to parse it
        action_set({'output': result})
    finally:
        remove_flag('actions.ping')


@when('actions.traceroute')
def traceroute():
    try:
        result, err = charms.sshproxy._run(
            'traceroute -m {} {}'.format(
                    action_get('hops'),
                    action_get('destination')
            )
        )
    except:
        action_fail('traceroute command failed')
    else:
        # Here you can send results back from ping, if you had time to parse it
        action_set({'output': result})
    finally:
        remove_flag('actions.traceroute')


@when('actions.iperf3')
def iperf3():
    err = ''
    try:
        # TODO: read all the flags via action_get and build the
        # proper command line to run iperf3
        host = action_get('host')

        cmd = 'iperf3 -c {} --json'.format(host)
        result, err = charms.sshproxy._run(cmd)
    except CalledProcessError as e:
        action_fail('iperf3 command failed:' + e.output)
    else:
        action_set({'outout': result})
    finally:
        remove_flag('actions.iperf3')


@when('config.changed')
def config_changed():
    """ Handle configuration changes """
    cfg = config()
    if cfg.changed('iperf3'):
        if cfg['iperf3']:
            # start iperf in server + daemon mode
            cmd = "iperf3 -s -D"
        else:
            cmd = "killall iperf3"
        try:
            charms.sshproxy._run(cmd)
            log("iperf3 stopped.")
        except CalledProcessError:
            log("iperf3 not running.")
        else:
            log("iperf3 started.")
