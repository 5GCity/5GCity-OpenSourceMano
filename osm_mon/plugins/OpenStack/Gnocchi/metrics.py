# Copyright 2017 Intel Research and Development Ireland Limited
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Intel Corporation

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at

#         http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# For those usages not covered by the Apache License, Version 2.0 please
# contact: helena.mcgough@intel.com or adrian.hoban@intel.com
##
"""Carry out OpenStack metric requests via Gnocchi API."""

import datetime
import json
import logging

import time

import six
import yaml

from osm_mon.core.message_bus.producer import KafkaProducer
from osm_mon.plugins.OpenStack.common import Common

from osm_mon.plugins.OpenStack.response import OpenStack_Response
from osm_mon.plugins.OpenStack.settings import Config

log = logging.getLogger(__name__)

METRIC_MAPPINGS = {
    "average_memory_utilization": "memory.usage",
    "disk_read_ops": "disk.read.requests",
    "disk_write_ops": "disk.write.requests",
    "disk_read_bytes": "disk.read.bytes",
    "disk_write_bytes": "disk.write.bytes",
    "packets_dropped": "interface.if_dropped",
    "packets_received": "interface.if_packets",
    "packets_sent": "interface.if_packets",
    "cpu_utilization": "cpu_util",
}

PERIOD_MS = {
    "HR": 3600000,
    "DAY": 86400000,
    "WEEK": 604800000,
    "MONTH": 2629746000,
    "YEAR": 31556952000
}


class Metrics(object):
    """OpenStack metric requests performed via the Gnocchi API."""

    def __init__(self):
        """Initialize the metric actions."""
        # Configure an instance of the OpenStack metric plugin
        config = Config.instance()
        config.read_environ()

        # Initialise authentication for API requests
        self._common = Common()

        # Use the Response class to generate valid json response messages
        self._response = OpenStack_Response()

        # Initializer a producer to send responses back to SO
        self._producer = KafkaProducer("metric_response")

    def metric_calls(self, message):
        """Consume info from the message bus to manage metric requests."""
        try:
            values = json.loads(message.value)
        except ValueError:
            values = yaml.safe_load(message.value)
        log.info("OpenStack metric action required.")

        auth_token = Common.get_auth_token(values['vim_uuid'])

        endpoint = Common.get_endpoint("metric", values['vim_uuid'])

        if message.key == "create_metric_request":
            # Configure metric
            metric_details = values['metric_create']
            metric_id, resource_id, status = self.configure_metric(
                endpoint, auth_token, metric_details)

            # Generate and send a create metric response
            try:
                resp_message = self._response.generate_response(
                    'create_metric_response', status=status,
                    cor_id=values['correlation_id'],
                    metric_id=metric_id, r_id=resource_id)
                log.info("Response messages: %s", resp_message)
                self._producer.create_metrics_resp(
                    'create_metric_response', resp_message,
                    'metric_response')
            except Exception as exc:
                log.warn("Failed to create response: %s", exc)

        elif message.key == "read_metric_data_request":
            # Read all metric data related to a specified metric
            timestamps, metric_data = self.read_metric_data(
                endpoint, auth_token, values)

            # Generate and send a response message
            try:

                metric_id = self.get_metric_id(endpoint, auth_token, METRIC_MAPPINGS[values['metric_name']],
                                          values['resource_uuid'])
                resp_message = self._response.generate_response(
                    'read_metric_data_response',
                    m_id=metric_id,
                    m_name=values['metric_name'],
                    r_id=values['resource_uuid'],
                    cor_id=values['correlation_id'],
                    times=timestamps, metrics=metric_data)
                log.info("Response message: %s", resp_message)
                self._producer.read_metric_data_response(
                    'read_metric_data_response', resp_message,
                    'metric_response')
            except Exception as exc:
                log.warn("Failed to send read metric response:%s", exc)

        elif message.key == "delete_metric_request":
            # delete the specified metric in the request
            metric_id = self.get_metric_id(endpoint, auth_token, METRIC_MAPPINGS[values['metric_name']],
                                           values['resource_uuid'])
            status = self.delete_metric(
                endpoint, auth_token, metric_id)

            # Generate and send a response message
            try:
                resp_message = self._response.generate_response(
                    'delete_metric_response', m_id=metric_id,
                    m_name=values['metric_name'],
                    status=status, r_id=values['resource_uuid'],
                    cor_id=values['correlation_id'])
                log.info("Response message: %s", resp_message)
                self._producer.delete_metric_response(
                    'delete_metric_response', resp_message,
                    'metric_response')
            except Exception as exc:
                log.warn("Failed to send delete response:%s", exc)

        elif message.key == "update_metric_request":
            # Gnocchi doesn't support configuration updates
            # Log and send a response back to this effect
            log.warn("Gnocchi doesn't support metric configuration\
                      updates.")
            req_details = values['metric_create']
            metric_name = req_details['metric_name']
            resource_id = req_details['resource_uuid']
            metric_id = self.get_metric_id(
                endpoint, auth_token, metric_name, resource_id)

            # Generate and send a response message
            try:
                resp_message = self._response.generate_response(
                    'update_metric_response', status=False,
                    cor_id=values['correlation_id'],
                    r_id=resource_id, m_id=metric_id)
                log.info("Response message: %s", resp_message)
                self._producer.update_metric_response(
                    'update_metric_response', resp_message,
                    'metric_response')
            except Exception as exc:
                log.warn("Failed to send an update response:%s", exc)

        elif message.key == "list_metric_request":
            list_details = values['metrics_list_request']

            metric_list = self.list_metrics(
                endpoint, auth_token, list_details)

            # Generate and send a response message
            try:
                resp_message = self._response.generate_response(
                    'list_metric_response', m_list=metric_list,
                    cor_id=list_details['correlation_id'])
                log.info("Response message: %s", resp_message)
                self._producer.list_metric_response(
                    'list_metric_response', resp_message,
                    'metric_response')
            except Exception as exc:
                log.warn("Failed to send a list response:%s", exc)

        else:
            log.warn("Unknown key, no action will be performed.")

        return

    def configure_metric(self, endpoint, auth_token, values):
        """Create the new metric in Gnocchi."""
        try:
            resource_id = values['resource_uuid']
        except KeyError:
            log.warn("Resource is not defined correctly.")
            return None, None, False

        # Check/Normalize metric name
        norm_name, metric_name = self.get_metric_name(values)
        if metric_name is None:
            log.warn("This metric is not supported by this plugin.")
            return None, resource_id, False

        # Check for an existing metric for this resource
        metric_id = self.get_metric_id(
            endpoint, auth_token, metric_name, resource_id)

        if metric_id is None:
            # Try appending metric to existing resource
            try:
                base_url = "{}/v1/resource/generic/%s/metric"
                res_url = base_url.format(endpoint) % resource_id
                payload = {metric_name: {'archive_policy_name': 'high',
                                         'unit': values['metric_unit']}}
                result = Common.perform_request(
                    res_url, auth_token, req_type="post",
                    payload=json.dumps(payload))
                # Get id of newly created metric
                for row in json.loads(result.text):
                    if row['name'] == metric_name:
                        metric_id = row['id']
                log.info("Appended metric to existing resource.")

                return metric_id, resource_id, True
            except Exception as exc:
                # Gnocchi version of resource does not exist creating a new one
                log.info("Failed to append metric to existing resource:%s",
                         exc)
                try:
                    url = "{}/v1/resource/generic".format(endpoint)
                    metric = {'name': metric_name,
                              'archive_policy_name': 'high',
                              'unit': values['metric_unit'], }

                    resource_payload = json.dumps({'id': resource_id,
                                                   'metrics': {
                                                       metric_name: metric}})

                    resource = Common.perform_request(
                        url, auth_token, req_type="post",
                        payload=resource_payload)

                    # Return the newly created resource_id for creating alarms
                    new_resource_id = json.loads(resource.text)['id']
                    log.info("Created new resource for metric: %s",
                             new_resource_id)

                    metric_id = self.get_metric_id(
                        endpoint, auth_token, metric_name, new_resource_id)

                    return metric_id, new_resource_id, True
                except Exception as exc:
                    log.warn("Failed to create a new resource:%s", exc)
            return None, None, False

        else:
            log.info("This metric already exists for this resource.")

        return metric_id, resource_id, False

    def delete_metric(self, endpoint, auth_token, metric_id):
        """Delete metric."""
        url = "{}/v1/metric/%s".format(endpoint) % metric_id

        try:
            result = Common.perform_request(
                url, auth_token, req_type="delete")
            if str(result.status_code) == "404":
                log.warn("Failed to delete the metric.")
                return False
            else:
                return True
        except Exception as exc:
            log.warn("Failed to carry out delete metric request:%s", exc)
        return False

    def list_metrics(self, endpoint, auth_token, values):
        """List all metrics."""

        # Check for a specified list
        try:
            # Check if the metric_name was specified for the list
            metric_name = values['metric_name'].lower()
            if metric_name not in METRIC_MAPPINGS.keys():
                log.warn("This metric is not supported, won't be listed.")
                metric_name = None
        except KeyError as exc:
            log.info("Metric name is not specified: %s", exc)
            metric_name = None

        try:
            resource = values['resource_uuid']
        except KeyError as exc:
            log.info("Resource is not specified:%s", exc)
            resource = None

        try:
            url = "{}/v1/metric?sort=name:asc".format(endpoint)
            result = Common.perform_request(
                url, auth_token, req_type="get")
            metrics = []
            metrics_partial = json.loads(result.text)
            for metric in metrics_partial:
                metrics.append(metric)

            while len(json.loads(result.text)) > 0:
                last_metric_id = metrics_partial[-1]['id']
                url = "{}/v1/metric?sort=name:asc&marker={}".format(endpoint, last_metric_id)
                result = Common.perform_request(
                    url, auth_token, req_type="get")
                if len(json.loads(result.text)) > 0:
                    metrics_partial = json.loads(result.text)
                    for metric in metrics_partial:
                        metrics.append(metric)

            if metrics is not None:
                # Format the list response
                if metric_name is not None and resource is not None:
                    metric_list = self.response_list(
                        metrics, metric_name=metric_name, resource=resource)
                    log.info("Returning an %s resource list for %s metrics",
                             metric_name, resource)
                elif metric_name is not None:
                    metric_list = self.response_list(
                        metrics, metric_name=metric_name)
                    log.info("Returning a list of %s metrics", metric_name)
                elif resource is not None:
                    metric_list = self.response_list(
                        metrics, resource=resource)
                    log.info("Return a list of %s resource metrics", resource)
                else:
                    metric_list = self.response_list(metrics)
                    log.info("Returning a complete list of metrics")

                return metric_list
            else:
                log.info("There are no metrics available")
                return []
        except Exception as exc:
            log.warn("Failed to generate any metric list. %s", exc)
        return None

    def get_metric_id(self, endpoint, auth_token, metric_name, resource_id):
        """Check if the desired metric already exists for the resource."""
        url = "{}/v1/resource/generic/%s".format(endpoint) % resource_id
        try:
            # Try return the metric id if it exists
            result = Common.perform_request(
                url, auth_token, req_type="get")
            return json.loads(result.text)['metrics'][metric_name]
        except Exception:
            log.info("Metric doesn't exist. No metric_id available")
        return None

    def get_metric_name(self, values):
        """Check metric name configuration and normalize."""
        metric_name = None
        try:
            # Normalize metric name
            metric_name = values['metric_name'].lower()
            return metric_name, METRIC_MAPPINGS[metric_name]
        except KeyError:
            log.info("Metric name %s is invalid.", metric_name)
        return metric_name, None

    def read_metric_data(self, endpoint, auth_token, values):
        """Collect metric measures over a specified time period."""
        timestamps = []
        data = []
        try:
            #get metric_id
            metric_id = self.get_metric_id(endpoint, auth_token, METRIC_MAPPINGS[values['metric_name']], values['resource_uuid'])
            # Try and collect measures
            collection_unit = values['collection_unit'].upper()
            collection_period = values['collection_period']

            # Define the start and end time based on configurations
            # FIXME: Local timezone may differ from timezone set in Gnocchi, causing discrepancies in measures
            stop_time = time.strftime("%Y-%m-%d") + "T" + time.strftime("%X")
            end_time = int(round(time.time() * 1000))
            if collection_unit == 'YEAR':
                diff = PERIOD_MS[collection_unit]
            else:
                diff = collection_period * PERIOD_MS[collection_unit]
            s_time = (end_time - diff) / 1000.0
            start_time = datetime.datetime.fromtimestamp(s_time).strftime(
                '%Y-%m-%dT%H:%M:%S.%f')
            base_url = "{}/v1/metric/%(0)s/measures?start=%(1)s&stop=%(2)s"
            url = base_url.format(endpoint) % {
                "0": metric_id, "1": start_time, "2": stop_time}

            # Perform metric data request
            metric_data = Common.perform_request(
                url, auth_token, req_type="get")

            # Generate a list of the requested timestamps and data
            for r in json.loads(metric_data.text):
                timestamp = r[0].replace("T", " ")
                timestamps.append(timestamp)
                data.append(r[2])

            return timestamps, data
        except Exception as exc:
            log.warn("Failed to gather specified measures: %s", exc)
        return timestamps, data

    def response_list(self, metric_list, metric_name=None, resource=None):
        """Create the appropriate lists for a list response."""
        resp_list, name_list, res_list = [], [], []

        # Create required lists
        for row in metric_list:
            # Only list OSM metrics
            name = None
            if row['name'] in METRIC_MAPPINGS.values():
                for k,v in six.iteritems(METRIC_MAPPINGS):
                    if row['name'] == v:
                        name = k
                metric = {"metric_name": name,
                          "metric_uuid": row['id'],
                          "metric_unit": row['unit'],
                          "resource_uuid": row['resource_id']}
                resp_list.append(metric)
            # Generate metric_name specific list
            if metric_name is not None and name is not None:
                if metric_name in METRIC_MAPPINGS.keys() and row['name'] == METRIC_MAPPINGS[metric_name]:
                    metric = {"metric_name": metric_name,
                              "metric_uuid": row['id'],
                              "metric_unit": row['unit'],
                              "resource_uuid": row['resource_id']}
                    name_list.append(metric)
            # Generate resource specific list
            if resource is not None and name is not None:
                if row['resource_id'] == resource:
                    metric = {"metric_name": name,
                              "metric_uuid": row['id'],
                              "metric_unit": row['unit'],
                              "resource_uuid": row['resource_id']}
                    res_list.append(metric)

        # Join required lists
        if metric_name is not None and resource is not None:
            # Return intersection of res_list and name_list
            return [i for i in res_list for j in name_list if i['metric_uuid'] == j['metric_uuid']]
        elif metric_name is not None:
            return name_list
        elif resource is not None:
            return res_list
        else:
            return resp_list
