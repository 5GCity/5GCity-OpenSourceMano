import asyncio
import logging
import os

import pyrfc3339

from . import model, utils
from .client import client
from .errors import JujuError

log = logging.getLogger(__name__)


class Machine(model.ModelEntity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_change(self._workaround_1695335)

    async def _workaround_1695335(self, delta, old, new, model):
        """
        This is a (hacky) temporary work around for a bug in Juju where the
        instance status and agent version fields don't get updated properly
        by the AllWatcher.

        Deltas never contain a value for `data['agent-status']['version']`,
        and once the `instance-status` reaches `pending`, we no longer get
        any updates for it (the deltas come in, but the `instance-status`
        data is always the same after that).

        To work around this, whenever a delta comes in for this machine, we
        query FullStatus and use the data from there if and only if it's newer.
        Luckily, the timestamps on the `since` field does seem to be accurate.

        See https://bugs.launchpad.net/juju/+bug/1695335
        """
        if delta.data.get('synthetic', False):
            # prevent infinite loops re-processing already processed deltas
            return

        full_status = await utils.run_with_interrupt(model.get_status(),
                                                     model._watch_stopping,
                                                     model.loop)
        if model._watch_stopping.is_set():
            return

        if self.id not in full_status.machines:
            return

        if not full_status.machines[self.id]['instance-status']['since']:
            return

        machine = full_status.machines[self.id]

        change_log = []
        key_map = {
            'status': 'current',
            'info': 'message',
            'since': 'since',
        }

        # handle agent version specially, because it's never set in
        # deltas, and we don't want even a newer delta to clear it
        agent_version = machine['agent-status']['version']
        if agent_version:
            delta.data['agent-status']['version'] = agent_version
            change_log.append(('agent-version', '', agent_version))

        # only update (other) delta fields if status data is newer
        status_since = pyrfc3339.parse(machine['instance-status']['since'])
        delta_since = pyrfc3339.parse(delta.data['instance-status']['since'])
        if status_since > delta_since:
            for status_key in ('status', 'info', 'since'):
                delta_key = key_map[status_key]
                status_value = machine['instance-status'][status_key]
                delta_value = delta.data['instance-status'][delta_key]
                change_log.append((delta_key, delta_value, status_value))
                delta.data['instance-status'][delta_key] = status_value

        if change_log:
            log.debug('Overriding machine delta with FullStatus data')
            for log_item in change_log:
                log.debug('    {}: {} -> {}'.format(*log_item))
            delta.data['synthetic'] = True
            old_obj, new_obj = self.model.state.apply_delta(delta)
            await model._notify_observers(delta, old_obj, new_obj)

    async def destroy(self, force=False):
        """Remove this machine from the model.

        Blocks until the machine is actually removed.

        """
        facade = client.ClientFacade.from_connection(self.connection)

        log.debug(
            'Destroying machine %s', self.id)

        await facade.DestroyMachines(force, [self.id])
        return await self.model._wait(
            'machine', self.id, 'remove')
    remove = destroy

    def run(self, command, timeout=None):
        """Run command on this machine.

        :param str command: The command to run
        :param int timeout: Time to wait before command is considered failed

        """
        raise NotImplementedError()

    async def set_annotations(self, annotations):
        """Set annotations on this machine.

        :param annotations map[string]string: the annotations as key/value
            pairs.

        """
        log.debug('Updating annotations on machine %s', self.id)

        self.ann_facade = client.AnnotationsFacade.from_connection(
            self.connection)

        ann = client.EntityAnnotations(
            entity=self.id,
            annotations=annotations,
        )
        return await self.ann_facade.Set([ann])

    async def scp_to(self, source, destination, user='ubuntu', proxy=False,
                     scp_opts=''):
        """Transfer files to this machine.

        :param str source: Local path of file(s) to transfer
        :param str destination: Remote destination of transferred files
        :param str user: Remote username
        :param bool proxy: Proxy through the Juju API server
        :param str scp_opts: Additional options to the `scp` command
        """
        if proxy:
            raise NotImplementedError('proxy option is not implemented')

        address = self.dns_name
        destination = '%s@%s:%s' % (user, address, destination)
        await self._scp(source, destination, scp_opts)

    async def scp_from(self, source, destination, user='ubuntu', proxy=False,
                       scp_opts=''):
        """Transfer files from this machine.

        :param str source: Remote path of file(s) to transfer
        :param str destination: Local destination of transferred files
        :param str user: Remote username
        :param bool proxy: Proxy through the Juju API server
        :param str scp_opts: Additional options to the `scp` command
        """
        if proxy:
            raise NotImplementedError('proxy option is not implemented')

        address = self.dns_name
        source = '%s@%s:%s' % (user, address, source)
        await self._scp(source, destination, scp_opts)

    async def _scp(self, source, destination, scp_opts):
        """ Execute an scp command. Requires a fully qualified source and
        destination.
        """
        cmd = [
            'scp',
            '-i', os.path.expanduser('~/.local/share/juju/ssh/juju_id_rsa'),
            '-o', 'StrictHostKeyChecking=no',
            '-q',
            '-B',
            source, destination
        ]
        cmd += scp_opts.split()
        loop = self.model.loop
        process = await asyncio.create_subprocess_exec(*cmd, loop=loop)
        await process.wait()
        if process.returncode != 0:
            raise JujuError("command failed: %s" % cmd)

    def ssh(
            self, command, user=None, proxy=False, ssh_opts=None):
        """Execute a command over SSH on this machine.

        :param str command: Command to execute
        :param str user: Remote username
        :param bool proxy: Proxy through the Juju API server
        :param str ssh_opts: Additional options to the `ssh` command

        """
        raise NotImplementedError()

    def status_history(self, num=20, utc=False):
        """Get status history for this machine.

        :param int num: Size of history backlog
        :param bool utc: Display time as UTC in RFC3339 format

        """
        raise NotImplementedError()

    @property
    def agent_status(self):
        """Returns the current Juju agent status string.

        """
        return self.safe_data['agent-status']['current']

    @property
    def agent_status_since(self):
        """Get the time when the `agent_status` was last updated.

        """
        return pyrfc3339.parse(self.safe_data['agent-status']['since'])

    @property
    def agent_version(self):
        """Get the version of the Juju machine agent.

        May return None if the agent is not yet available.
        """
        version = self.safe_data['agent-status']['version']
        if version:
            return client.Number.from_json(version)
        else:
            return None

    @property
    def status(self):
        """Returns the current machine provisioning status string.

        """
        return self.safe_data['instance-status']['current']

    @property
    def status_message(self):
        """Returns the current machine provisioning status message.

        """
        return self.safe_data['instance-status']['message']

    @property
    def status_since(self):
        """Get the time when the `status` was last updated.

        """
        return pyrfc3339.parse(self.safe_data['instance-status']['since'])

    @property
    def dns_name(self):
        """Get the DNS name for this machine. This is a best guess based on the
        addresses available in current data.

        May return None if no suitable address is found.
        """
        for scope in ['public', 'local-cloud']:
            addresses = self.safe_data['addresses'] or []
            addresses = [address for address in addresses
                         if address['scope'] == scope]
            if addresses:
                return addresses[0]['value']
        return None

    @property
    def series(self):
        """Returns the series of the current machine

        """
        return self.safe_data['series']
