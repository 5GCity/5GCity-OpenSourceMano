from flask import request, Response
from flask_restful import Resource
from emuvim.api.openstack.resources import Stack
from emuvim.api.openstack.openstack_dummies.base_openstack_dummy import BaseOpenstackDummy
from datetime import datetime
from emuvim.api.openstack.heat_parser import HeatParser
import logging
import json


class HeatDummyApi(BaseOpenstackDummy):
    def __init__(self, in_ip, in_port, compute):
        super(HeatDummyApi, self).__init__(in_ip, in_port)
        self.compute = compute

        self.api.add_resource(Shutdown, "/shutdown")
        self.api.add_resource(HeatListAPIVersions, "/",
                              resource_class_kwargs={'api': self})
        self.api.add_resource(HeatCreateStack, "/v1/<tenant_id>/stacks",
                              resource_class_kwargs={'api': self})
        self.api.add_resource(HeatShowStack, "/v1/<tenant_id>/stacks/<stack_name_or_id>",
                              "/v1/<tenant_id>/stacks/<stack_name_or_id>/<stack_id>",
                              resource_class_kwargs={'api': self})
        self.api.add_resource(HeatUpdateStack, "/v1/<tenant_id>/stacks/<stack_name_or_id>",
                              "/v1/<tenant_id>/stacks/<stack_name_or_id>/<stack_id>",
                              resource_class_kwargs={'api': self})
        self.api.add_resource(HeatDeleteStack, "/v1/<tenant_id>/stacks/<stack_name_or_id>",
                              "/v1/<tenant_id>/stacks/<stack_name_or_id>/<stack_id>",
                              resource_class_kwargs={'api': self})

        @self.app.after_request
        def add_access_control_header(response):
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response


    def _start_flask(self):
        logging.info("Starting %s endpoint @ http://%s:%d" % (__name__, self.ip, self.port))
        if self.app is not None:
            self.app.before_request(self.dump_playbook)
            self.app.run(self.ip, self.port, debug=True, use_reloader=False)


class Shutdown(Resource):
    """
    A get request to /shutdown will shut down this endpoint.
    """

    def get(self):
        logging.debug(("%s is beeing shut down") % (__name__))
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()


class HeatListAPIVersions(Resource):
    def __init__(self, api):
        self.api = api

    def get(self):
        logging.debug("API CALL: %s GET" % str(self.__class__.__name__))
        resp = dict()

        resp['versions'] = dict()
        resp['versions'] = [{
            "status": "CURRENT",
            "id": "v1.0",
            "links": [
                {
                    "href": "http://%s:%d/v2.0" % (self.api.ip, self.api.port),
                    "rel": "self"
                }
            ]
        }]

        return Response(json.dumps(resp), status=200, mimetype="application/json")


class HeatCreateStack(Resource):
    def __init__(self, api):
        self.api = api

    def post(self, tenant_id):
        """
        Create and deploy a new stack.

        :param tenant_id:
        :return: 409, if the stack name was already used.
            400, if the heat template could not be parsed properly.
            500, if any exception occurred while creation.
            201, if everything worked out.
        """
        logging.debug("API CALL: %s POST" % str(self.__class__.__name__))

        try:
            stack_dict = json.loads(request.data)
            for stack in self.api.compute.stacks.values():
                if stack.stack_name == stack_dict['stack_name']:
                    return [], 409
            stack = Stack()
            stack.stack_name = stack_dict['stack_name']
            reader = HeatParser(self.api.compute)

            if isinstance(stack_dict['template'], str) or isinstance(stack_dict['template'], unicode):
                stack_dict['template'] = json.loads(stack_dict['template'])
            if not reader.parse_input(stack_dict['template'], stack, self.api.compute.dc.label):
                self.api.compute.clean_broken_stack(stack)
                return 'Could not create stack.', 400

            stack.creation_time = str(datetime.now())
            stack.status = "CREATE_COMPLETE"

            return_dict = {"stack": {"id": stack.id,
                                     "links": [
                                         {
                                             "href": "http://%s:%s/v1/%s/stacks/%s"
                                                     % (self.api.ip, self.api.port, tenant_id, stack.id),
                                             "rel": "self"
                                         }]}}

            self.api.compute.add_stack(stack)
            self.api.compute.deploy_stack(stack.id)
            return Response(json.dumps(return_dict), status=201, mimetype="application/json")

        except Exception as ex:
            logging.exception("Heat: Create Stack exception.")
            return ex.message, 500

    def get(self, tenant_id):
        """
        Calculates information about the requested stack.

        :param tenant_id:
        :return: Returns a json response which contains information like the stack id, name, status, creation time.
            500, if any exception occurred.
            200, if everything worked out.
        """
        logging.debug("API CALL: %s GET" % str(self.__class__.__name__))
        try:
            return_stacks = dict()
            return_stacks['stacks'] = list()
            for stack in self.api.compute.stacks.values():
                return_stacks['stacks'].append(
                    {"creation_time": stack.creation_time,
                     "description": "desc of " + stack.id,
                     "id": stack.id,
                     "links": [],
                     "stack_name": stack.stack_name,
                     "stack_status": stack.status,
                     "stack_status_reason": "Stack CREATE completed successfully",
                     "updated_time": stack.update_time,
                     "tags": ""
                     })

            return Response(json.dumps(return_stacks), status=200, mimetype="application/json")
        except Exception as ex:
            logging.exception("Heat: List Stack exception.")
            return ex.message, 500


class HeatShowStack(Resource):
    def __init__(self, api):
        self.api = api

    def get(self, tenant_id, stack_name_or_id, stack_id=None):
        """
        Calculates detailed information about the requested stack.

        :param tenant_id:
        :param stack_name_or_id:
        :param stack_id:
        :return: Returns a json response which contains information like the stack id, name, status, creation time.
            500, if any exception occurred.
            200, if everything worked out.
        """
        logging.debug("API CALL: %s GET" % str(self.__class__.__name__))
        try:
            stack = None
            if stack_name_or_id in self.api.compute.stacks:
                stack = self.api.compute.stacks[stack_name_or_id]
            else:
                for tmp_stack in self.api.compute.stacks.values():
                    if tmp_stack.stack_name == stack_name_or_id:
                        stack = tmp_stack
            if stack is None:
                return 'Could not resolve Stack - ID', 404

            return_stack = {
                "stack": {
                    "capabilities": [],
                    "creation_time": stack.creation_time,
                    "description": "desc of " + stack.stack_name,
                    "disable_rollback": True,
                    "id": stack.id,
                    "links": [
                        {
                            "href": "http://%s:%s/v1/%s/stacks/%s"
                                    % (self.api.ip, self.api.port, tenant_id, stack.id),
                            "rel": "self"
                        }
                    ],
                    "notification_topics": [],
                    "outputs": [],
                    "parameters": {
                        "OS::project_id": "3ab5b02f-a01f-4f95-afa1-e254afc4a435",  # add real project id
                        "OS::stack_id": stack.id,
                        "OS::stack_name": stack.stack_name
                    },
                    "stack_name": stack.stack_name,
                    "stack_owner": "The owner of the stack.",  # add stack owner
                    "stack_status": stack.status,
                    "stack_status_reason": "The reason for the current status of the stack.",  # add status reason
                    "template_description": "The description of the stack template.",
                    "stack_user_project_id": "The project UUID of the stack user.",
                    "timeout_mins": "",
                    "updated_time": "",
                    "parent": "",
                    "tags": ""
                }
            }

            return Response(json.dumps(return_stack), status=200, mimetype="application/json")

        except Exception as ex:
            logging.exception("Heat: Show stack exception.")
            return ex.message, 500


class HeatUpdateStack(Resource):
    def __init__(self, api):
        self.api = api

    def put(self, tenant_id, stack_name_or_id, stack_id=None):
        """
        Updates an existing stack with a new heat template.

        :param tenant_id:
        :param stack_name_or_id: Specifies the stack, which should be updated.
        :param stack_id:
        :return: 404, if the requested stack could not be found.
            400, if the stack creation (because of errors in the heat template) or the stack update failed.
            500, if any exception occurred while updating.
            202, if everything worked out.
        """
        logging.debug("API CALL: %s PUT" % str(self.__class__.__name__))
        try:
            old_stack = None
            if stack_name_or_id in self.api.compute.stacks:
                old_stack = self.api.compute.stacks[stack_name_or_id]
            else:
                for tmp_stack in self.api.compute.stacks.values():
                    if tmp_stack.stack_name == stack_name_or_id:
                        old_stack = tmp_stack
            if old_stack is None:
                return 'Could not resolve Stack - ID', 404

            stack_dict = json.loads(request.data)

            stack = Stack()
            stack.stack_name = old_stack.stack_name
            stack.id = old_stack.id
            stack.creation_time = old_stack.creation_time
            stack.update_time = str(datetime.now())
            stack.status = "UPDATE_COMPLETE"

            reader = HeatParser(self.api.compute)
            if isinstance(stack_dict['template'], str) or isinstance(stack_dict['template'], unicode):
                stack_dict['template'] = json.loads(stack_dict['template'])
            if not reader.parse_input(stack_dict['template'], stack, self.api.compute.dc.label, stack_update=True):
                return 'Could not create stack.', 400

            if not self.api.compute.update_stack(old_stack.id, stack):
                return 'Could not update stack.', 400

            return Response(status=202, mimetype="application/json")

        except Exception as ex:
            logging.exception("Heat: Update Stack exception")
            return ex.message, 500


class HeatDeleteStack(Resource):
    def __init__(self, api):
        self.api = api

    def delete(self, tenant_id, stack_name_or_id, stack_id=None):
        """
        Deletes an existing stack.

        :param tenant_id:
        :param stack_name_or_id: Specifies the stack, which should be deleted.
        :param stack_id:
        :return: 500, if any exception occurred while deletion.
            204, if everything worked out.
        """
        logging.debug("API CALL: %s DELETE" % str(self.__class__.__name__))
        try:
            if stack_name_or_id in self.api.compute.stacks:
                self.api.compute.delete_stack(stack_name_or_id)
                return Response('Deleted Stack: ' + stack_name_or_id, 204)

            for stack in self.api.compute.stacks.values():
                if stack.stack_name == stack_name_or_id:
                    self.api.compute.delete_stack(stack.id)
                    return Response('Deleted Stack: ' + stack_name_or_id, 204)

        except Exception as ex:
            logging.exception("Heat: Delete Stack exception")
            return ex.message, 500
