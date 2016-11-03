from charmhelpers.core.hookenv import (
    config,
    status_set,
    action_get,
    action_set,
    action_fail,
    log,
)

from charms.reactive import (
    when,
    when_not,
    set_state as set_flag,
    remove_state as remove_flag,
)

import subprocess


@when_not('netutils.ready')
def ready():
    status_set('active', 'Ready!')
    set_flag('netutils.ready')


@when('actions.nmap')
def nmap():
    err = ''
    try:
        result, err = _run('nmap {}'.format(action_get('destination')))
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
        result, err = _run('ping -qc {} {}'.format(
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
        result, err = _run('traceroute -m {} {}'.format(action_get('hops'), action_get('destination')))
    except:
        action_fail('traceroute command failed')
    else:
        # Here you can send results back from ping, if you had time to parse it
        action_set({'output': result})
    finally:
        remove_flag('actions.traceroute')



def _run(cmd, env=None):
    if isinstance(cmd, str):
        cmd = cmd.split() if ' ' in cmd else [cmd]

    log(cmd)
    p = subprocess.Popen(cmd,
                         env=env,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    retcode = p.poll()
    if retcode > 0:
        raise subprocess.CalledProcessError(returncode=retcode,
                                            cmd=cmd,
                                            output=stderr.decode("utf-8").strip())
    return (stdout.decode('utf-8'), stderr.decode('utf-8'))
