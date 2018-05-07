
import logging
import os
import os.path
import re
import ssl
import sys
import time

# FIXME: this should load the juju inside or modules without having to
# explicitly install it. Check why it's not working.
# Load our subtree of the juju library
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
path = os.path.join(path, "modules/libjuju/")
if path not in sys.path:
    sys.path.insert(1, path)

from juju.controller import Controller
from juju.model import Model, ModelObserver


# We might need this to connect to the websocket securely, but test and verify.
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python doesn't verify by default (see pep-0476)
    #   https://www.python.org/dev/peps/pep-0476/
    pass


# Custom exceptions
class JujuCharmNotFound(Exception):
    """The Charm can't be found or is not readable."""


class JujuApplicationExists(Exception):
    """The Application already exists."""


class N2VCPrimitiveExecutionFailed(Exception):
    """Something failed while attempting to execute a primitive."""


# Quiet the debug logging
logging.getLogger('websockets.protocol').setLevel(logging.INFO)
logging.getLogger('juju.client.connection').setLevel(logging.WARN)
logging.getLogger('juju.model').setLevel(logging.WARN)
logging.getLogger('juju.machine').setLevel(logging.WARN)


class VCAMonitor(ModelObserver):
    """Monitor state changes within the Juju Model."""
    log = None
    ns_name = None
    applications = {}

    def __init__(self, ns_name):
        self.log = logging.getLogger(__name__)

        self.ns_name = ns_name

    def AddApplication(self, application_name, callback, *callback_args):
        if application_name not in self.applications:
            self.applications[application_name] = {
                'callback': callback,
                'callback_args': callback_args
            }

    def RemoveApplication(self, application_name):
        if application_name in self.applications:
            del self.applications[application_name]

    async def on_change(self, delta, old, new, model):
        """React to changes in the Juju model."""

        if delta.entity == "unit":
            # Ignore change events from other applications
            if delta.data['application'] not in self.applications.keys():
                return

            try:

                application_name = delta.data['application']

                callback = self.applications[application_name]['callback']
                callback_args = self.applications[application_name]['callback_args']

                if old and new:
                    old_status = old.workload_status
                    new_status = new.workload_status

                    if old_status == new_status:
                        """The workload status may fluctuate around certain events,
                        so wait until the status has stabilized before triggering
                        the callback."""
                        if callback:
                            callback(
                                self.ns_name,
                                delta.data['application'],
                                new_status,
                                *callback_args)

                if old and not new:
                    # This is a charm being removed
                    if callback:
                        callback(
                            self.ns_name,
                            delta.data['application'],
                            "removed",
                            *callback_args)
            except Exception as e:
                self.log.debug("[1] notify_callback exception {}".format(e))
        elif delta.entity == "action":
            # TODO: Decide how we want to notify the user of actions

            # uuid = delta.data['id']     # The Action's unique id
            # msg = delta.data['message'] # The output of the action
            #
            # if delta.data['status'] == "pending":
            #     # The action is queued
            #     pass
            # elif delta.data['status'] == "completed""
            #     # The action was successful
            #     pass
            # elif delta.data['status'] == "failed":
            #     # The action failed.
            #     pass

            pass

########
# TODO
#
# Create unique models per network service
# Document all public functions


class N2VC:

    # Juju API
    api = None
    log = None
    controller = None
    connecting = False
    authenticated = False

    models = {}
    default_model = None

    # Model Observers
    monitors = {}

    # VCA config
    hostname = ""
    port = 17070
    username = ""
    secret = ""

    def __init__(self,
                 log=None,
                 server='127.0.0.1',
                 port=17070,
                 user='admin',
                 secret=None,
                 artifacts=None
                 ):
        """Initialize N2VC

        :param vcaconfig dict A dictionary containing the VCA configuration

        :param artifacts str The directory where charms required by a vnfd are
            stored.

        :Example:
        n2vc = N2VC(vcaconfig={
            'secret': 'MzI3MDJhOTYxYmM0YzRjNTJiYmY1Yzdm',
            'user': 'admin',
            'ip-address': '10.44.127.137',
            'port': 17070,
            'artifacts': '/path/to/charms'
        })

        """

        if log:
            self.log = log
        else:
            self.log = logging.getLogger(__name__)

        # Quiet websocket traffic
        logging.getLogger('websockets.protocol').setLevel(logging.INFO)
        logging.getLogger('juju.client.connection').setLevel(logging.WARN)
        logging.getLogger('model').setLevel(logging.WARN)
        # logging.getLogger('websockets.protocol').setLevel(logging.DEBUG)

        self.log.debug('JujuApi: instantiated')

        self.server = server
        self.port = port

        self.secret = secret
        if user.startswith('user-'):
            self.user = user
        else:
            self.user = 'user-{}'.format(user)

        self.endpoint = '%s:%d' % (server, int(port))

        self.artifacts = artifacts

    def __del__(self):
        """Close any open connections."""
        yield self.logout()

    def notify_callback(self, model_name, application_name, status, callback=None, *callback_args):
        try:
            if callback:
                callback(model_name, application_name, status, *callback_args)
        except Exception as e:
            self.log.error("[0] notify_callback exception {}".format(e))
            raise e
        return True

    # Public methods
    async def CreateNetworkService(self, nsd):
        """Create a new model to encapsulate this network service.

        Create a new model in the Juju controller to encapsulate the
        charms associated with a network service.

        You can pass either the nsd record or the id of the network
        service, but this method will fail without one of them.
        """
        if not self.authenticated:
            await self.login()

        # Ideally, we will create a unique model per network service.
        # This change will require all components, i.e., LCM and SO, to use
        # N2VC for 100% compatibility. If we adopt unique models for the LCM,
        # services deployed via LCM would't be manageable via SO and vice versa

        return self.default_model

    async def DeployCharms(self, model_name, application_name, vnfd, charm_path, params={}, machine_spec={}, callback=None, *callback_args):
        """Deploy one or more charms associated with a VNF.

        Deploy the charm(s) referenced in a VNF Descriptor.

        You can pass either the nsd record or the id of the network
        service, but this method will fail without one of them.

        :param str ns_name: The name of the network service
        :param str application_name: The name of the application
        :param dict vnfd: The name of the application
        :param str charm_path: The path to the Juju charm
        :param dict params: A dictionary of runtime parameters
          Examples::
          {
            'rw_mgmt_ip': '1.2.3.4',
            # Pass the initial-config-primitives section of the vnf or vdu
            'initial-config-primitives': {...}
          }
        :param dict machine_spec: A dictionary describing the machine to install to
          Examples::
          {
            'hostname': '1.2.3.4',
            'username': 'ubuntu',
          }
        :param obj callback: A callback function to receive status changes.
        :param tuple callback_args: A list of arguments to be passed to the callback
        """

        ########################################################
        # Verify the path to the charm exists and is readable. #
        ########################################################
        if not os.path.exists(charm_path):
            self.log.debug("Charm path doesn't exist: {}".format(charm_path))
            self.notify_callback(model_name, application_name, "failed", callback, *callback_args)
            raise JujuCharmNotFound("No artifacts configured.")

        ################################
        # Login to the Juju controller #
        ################################
        if not self.authenticated:
            self.log.debug("Authenticating with Juju")
            await self.login()

        ##########################################
        # Get the model for this network service #
        ##########################################
        # TODO: In a point release, we will use a model per deployed network
        # service. In the meantime, we will always use the 'default' model.
        model_name = 'default'
        model = await self.get_model(model_name)

        ########################################
        # Verify the application doesn't exist #
        ########################################
        app = await self.get_application(model, application_name)
        if app:
            raise JujuApplicationExists("Can't deploy application \"{}\" to model \"{}\" because it already exists.".format(application_name, model))

        ################################################################
        # Register this application with the model-level event monitor #
        ################################################################
        if callback:
            self.monitors[model_name].AddApplication(
                application_name,
                callback,
                *callback_args
            )

        ########################################################
        # Check for specific machine placement (native charms) #
        ########################################################
        to = ""
        if machine_spec.keys():
            # TODO: This needs to be tested.
            # if all(k in machine_spec for k in ['hostname', 'username']):
            #     # Enlist the existing machine in Juju
            #     machine = await self.model.add_machine(spec='ssh:%@%'.format(
            #         specs['host'],
            #         specs['user'],
            #     ))
            #     to = machine.id
            pass

        #######################################
        # Get the initial charm configuration #
        #######################################

        rw_mgmt_ip = None
        if 'rw_mgmt_ip' in params:
            rw_mgmt_ip = params['rw_mgmt_ip']

        initial_config = self._get_config_from_dict(
            params['initial-config-primitive'],
            {'<rw_mgmt_ip>': rw_mgmt_ip}
        )

        self.log.debug("JujuApi: Deploying charm ({}) from {}".format(
            application_name,
            charm_path,
            to=to,
        ))

        ########################################################
        # Deploy the charm and apply the initial configuration #
        ########################################################
        app = await model.deploy(
            # We expect charm_path to be either the path to the charm on disk
            # or in the format of cs:series/name
            charm_path,
            # This is the formatted, unique name for this charm
            application_name=application_name,
            # Proxy charms should use the current LTS. This will need to be
            # changed for native charms.
            series='xenial',
            # Apply the initial 'config' primitive during deployment
            config=initial_config,
            # TBD: Where to deploy the charm to.
            to=None,
        )

        # #######################################
        # # Execute initial config primitive(s) #
        # #######################################
        primitives = {}

        # Build a sequential list of the primitives to execute
        for primitive in params['initial-config-primitive']:
            try:
                if primitive['name'] == 'config':
                    # This is applied when the Application is deployed
                    pass
                else:
                    seq = primitive['seq']

                    primitives[seq] = {
                        'name': primitive['name'],
                        'parameters': self._map_primitive_parameters(
                            primitive['parameter'],
                            {'<rw_mgmt_ip>': rw_mgmt_ip}
                        ),
                    }

                    for primitive in sorted(primitives):
                        await self.ExecutePrimitive(
                            model_name,
                            application_name,
                            primitives[primitive]['name'],
                            callback,
                            callback_args,
                            **primitives[primitive]['parameters'],
                        )
            except N2VCPrimitiveExecutionFailed as e:
                self.debug.log(
                    "[N2VC] Exception executing primitive: {}".format(e)
                )
                raise

    async def ExecutePrimitive(self, model_name, application_name, primitive, callback, *callback_args, **params):
        """
        Queue the execution of a primitive

        returns the UUID of the executed primitive
        """
        uuid = None
        try:
            if not self.authenticated:
                await self.login()

            # FIXME: This is hard-coded until model-per-ns is added
            model_name = 'default'

            model = await self.controller.get_model(model_name)

            if primitive == 'config':
                # config is special, and expecting params to be a dictionary
                self.log.debug("Setting charm configuration for {}".format(application_name))
                self.log.debug(params['params'])
                await self.set_config(model, application_name, params['params'])
            else:
                app = await self.get_application(model, application_name)
                if app:
                    # Run against the first (and probably only) unit in the app
                    unit = app.units[0]
                    if unit:
                        self.log.debug("Executing primitive {}".format(primitive))
                        action = await unit.run_action(primitive, **params)
                        uuid = action.id
                await model.disconnect()
        except Exception as e:
            self.log.debug("Caught exception while executing primitive: {}".format(e))
            raise e
        return uuid

    async def RemoveCharms(self, model_name, application_name, callback=None, *callback_args):
        try:
            if not self.authenticated:
                await self.login()

            model = await self.get_model(model_name)
            app = await self.get_application(model, application_name)
            if app:
                # Remove this application from event monitoring
                self.monitors[model_name].RemoveApplication(application_name)

                # self.notify_callback(model_name, application_name, "removing", callback, *callback_args)
                self.log.debug("Removing the application {}".format(application_name))
                await app.remove()

                # Notify the callback that this charm has been removed.
                self.notify_callback(model_name, application_name, "removed", callback, *callback_args)

        except Exception as e:
            print("Caught exception: {}".format(e))
            self.log.debug(e)
            raise e

    async def DestroyNetworkService(self, nsd):
        raise NotImplementedError()

    async def GetMetrics(self, model_name, application_name):
        """Get the metrics collected by the VCA.

        :param model_name The name of the model
        :param application_name The name of the application
        """
        metrics = {}
        model = await self.get_model(model_name)
        app = await self.get_application(model, application_name)
        if app:
            metrics = await app.get_metrics()

        return metrics

    # Non-public methods
    async def add_relation(self, a, b, via=None):
        """
        Add a relation between two application endpoints.

        :param a An application endpoint
        :param b An application endpoint
        :param via The egress subnet(s) for outbound traffic, e.g.,
            (192.168.0.0/16,10.0.0.0/8)
        """
        if not self.authenticated:
            await self.login()

        m = await self.get_model()
        try:
            m.add_relation(a, b, via)
        finally:
            await m.disconnect()

    # async def apply_config(self, config, application):
    #     """Apply a configuration to the application."""
    #     print("JujuApi: Applying configuration to {}.".format(
    #         application
    #     ))
    #     return await self.set_config(application=application, config=config)

    def _get_config_from_dict(self, config_primitive, values):
        """Transform the yang config primitive to dict.

        Expected result:

            config = {
                'config':
            }
        """
        config = {}
        for primitive in config_primitive:
            if primitive['name'] == 'config':
                # config = self._map_primitive_parameters()
                for parameter in primitive['parameter']:
                    param = str(parameter['name'])
                    if parameter['value'] == "<rw_mgmt_ip>":
                        config[param] = str(values[parameter['value']])
                    else:
                        config[param] = str(parameter['value'])

        return config

    def _map_primitive_parameters(self, parameters, values):
        params = {}
        for parameter in parameters:
            param = str(parameter['name'])
            if parameter['value'] == "<rw_mgmt_ip>":
                params[param] = str(values[parameter['value']])
            else:
                params[param] = str(parameter['value'])
        return params

    def _get_config_from_yang(self, config_primitive, values):
        """Transform the yang config primitive to dict."""
        config = {}
        for primitive in config_primitive.values():
            if primitive['name'] == 'config':
                for parameter in primitive['parameter'].values():
                    param = str(parameter['name'])
                    if parameter['value'] == "<rw_mgmt_ip>":
                        config[param] = str(values[parameter['value']])
                    else:
                        config[param] = str(parameter['value'])

        return config

    def FormatApplicationName(self, *args):
        """
        Generate a Juju-compatible Application name

        :param args tuple: Positional arguments to be used to construct the
        application name.

        Limitations::
        - Only accepts characters a-z and non-consequitive dashes (-)
        - Application name should not exceed 50 characters

        Examples::

            FormatApplicationName("ping_pong_ns", "ping_vnf", "a")
        """

        appname = ""
        for c in "-".join(list(args)):
            if c.isdigit():
                c = chr(97 + int(c))
            elif not c.isalpha():
                c = "-"
            appname += c
        return re.sub('\-+', '-', appname.lower())


    # def format_application_name(self, nsd_name, vnfr_name, member_vnf_index=0):
    #     """Format the name of the application
    #
    #     Limitations:
    #     - Only accepts characters a-z and non-consequitive dashes (-)
    #     - Application name should not exceed 50 characters
    #     """
    #     name = "{}-{}-{}".format(nsd_name, vnfr_name, member_vnf_index)
    #     new_name = ''
    #     for c in name:
    #         if c.isdigit():
    #             c = chr(97 + int(c))
    #         elif not c.isalpha():
    #             c = "-"
    #         new_name += c
    #     return re.sub('\-+', '-', new_name.lower())

    def format_model_name(self, name):
        """Format the name of model.

        Model names may only contain lowercase letters, digits and hyphens
        """

        return name.replace('_', '-').lower()

    async def get_application(self, model, application):
        """Get the deployed application."""
        if not self.authenticated:
            await self.login()

        app = None
        if application and model:
            if model.applications:
                if application in model.applications:
                    app = model.applications[application]

        return app

    async def get_model(self, model_name='default'):
        """Get a model from the Juju Controller.

        Note: Model objects returned must call disconnected() before it goes
        out of scope."""
        if not self.authenticated:
            await self.login()

        if model_name not in self.models:
            print("connecting to model {}".format(model_name))
            self.models[model_name] = await self.controller.get_model(model_name)

            # Create an observer for this model
            self.monitors[model_name] = VCAMonitor(model_name)
            self.models[model_name].add_observer(self.monitors[model_name])

        return self.models[model_name]

    async def login(self):
        """Login to the Juju controller."""

        if self.authenticated:
            return

        self.connecting = True

        self.log.debug("JujuApi: Logging into controller")

        cacert = None
        self.controller = Controller()

        if self.secret:
            self.log.debug("Connecting to controller... ws://{}:{} as {}/{}".format(self.endpoint, self.port, self.user, self.secret))
            await self.controller.connect(
                endpoint=self.endpoint,
                username=self.user,
                password=self.secret,
                cacert=cacert,
            )
        else:
            # current_controller no longer exists
            # self.log.debug("Connecting to current controller...")
            # await self.controller.connect_current()
            # await self.controller.connect(
            #     endpoint=self.endpoint,
            #     username=self.user,
            #     cacert=cacert,
            # )
            self.log.fatal("VCA credentials not configured.")

        self.authenticated = True
        self.log.debug("JujuApi: Logged into controller")

        # self.default_model = await self.controller.get_model("default")

    async def logout(self):
        """Logout of the Juju controller."""
        if not self.authenticated:
            return

        try:
            if self.default_model:
                self.log.debug("Disconnecting model {}".format(self.default_model))
                await self.default_model.disconnect()
                self.default_model = None

            for model in self.models:
                await self.models[model].disconnect()

            if self.controller:
                self.log.debug("Disconnecting controller {}".format(self.controller))
                await self.controller.disconnect()
                # self.controller = None

            self.authenticated = False
        except Exception as e:
            self.log.fail("Fatal error logging out of Juju Controller: {}".format(e))
            raise e


    # async def remove_application(self, name):
    #     """Remove the application."""
    #     if not self.authenticated:
    #         await self.login()
    #
    #     app = await self.get_application(name)
    #     if app:
    #         self.log.debug("JujuApi: Destroying application {}".format(
    #             name,
    #         ))
    #
    #         await app.destroy()

    async def remove_relation(self, a, b):
        """
        Remove a relation between two application endpoints

        :param a An application endpoint
        :param b An application endpoint
        """
        if not self.authenticated:
            await self.login()

        m = await self.get_model()
        try:
            m.remove_relation(a, b)
        finally:
            await m.disconnect()

    async def resolve_error(self, application=None):
        """Resolve units in error state."""
        if not self.authenticated:
            await self.login()

        app = await self.get_application(self.default_model, application)
        if app:
            self.log.debug("JujuApi: Resolving errors for application {}".format(
                application,
            ))

            for unit in app.units:
                app.resolved(retry=True)

    async def run_action(self, application, action_name, **params):
        """Execute an action and return an Action object."""
        if not self.authenticated:
            await self.login()
        result = {
            'status': '',
            'action': {
                'tag': None,
                'results': None,
            }
        }
        app = await self.get_application(self.default_model, application)
        if app:
            # We currently only have one unit per application
            # so use the first unit available.
            unit = app.units[0]

            self.log.debug("JujuApi: Running Action {} against Application {}".format(
                action_name,
                application,
            ))

            action = await unit.run_action(action_name, **params)

            # Wait for the action to complete
            await action.wait()

            result['status'] = action.status
            result['action']['tag'] = action.data['id']
            result['action']['results'] = action.results

        return result

    async def set_config(self, model_name, application, config):
        """Apply a configuration to the application."""
        if not self.authenticated:
            await self.login()

        app = await self.get_application(model_name, application)
        if app:
            self.log.debug("JujuApi: Setting config for Application {}".format(
                application,
            ))
            await app.set_config(config)

            # Verify the config is set
            newconf = await app.get_config()
            for key in config:
                if config[key] != newconf[key]['value']:
                    self.log.debug("JujuApi: Config not set! Key {} Value {} doesn't match {}".format(key, config[key], newconf[key]))

    # async def set_parameter(self, parameter, value, application=None):
    #     """Set a config parameter for a service."""
    #     if not self.authenticated:
    #         await self.login()
    #
    #     self.log.debug("JujuApi: Setting {}={} for Application {}".format(
    #         parameter,
    #         value,
    #         application,
    #     ))
    #     return await self.apply_config(
    #         {parameter: value},
    #         application=application,
        # )

    async def wait_for_application(self, name, timeout=300):
        """Wait for an application to become active."""
        if not self.authenticated:
            await self.login()

        app = await self.get_application(self.default_model, name)
        if app:
            self.log.debug(
                "JujuApi: Waiting {} seconds for Application {}".format(
                    timeout,
                    name,
                )
            )

            await self.default_model.block_until(
                lambda: all(
                    unit.agent_status == 'idle'
                    and unit.workload_status
                    in ['active', 'unknown'] for unit in app.units
                ),
                timeout=timeout
            )
