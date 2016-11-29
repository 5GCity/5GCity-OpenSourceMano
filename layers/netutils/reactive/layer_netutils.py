from charmhelpers.core.hookenv import (
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
import charms.sshproxy


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
