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
"""Generate valid responses to send back to the SO."""

import json
import logging

log = logging.getLogger(__name__)

schema_version = "1.0"


class OpenStack_Response(object):
    """Generates responses for OpenStack plugin."""

    def __init__(self):
        """Initialize OpenStack Response instance."""

    def generate_response(self, key, **kwargs):
        """Make call to appropriate response function."""
        if key == "list_alarm_response":
            message = self.alarm_list_response(**kwargs)
        elif key == "create_alarm_response":
            message = self.create_alarm_response(**kwargs)
        elif key == "delete_alarm_response":
            message = self.delete_alarm_response(**kwargs)
        elif key == "update_alarm_response":
            message = self.update_alarm_response(**kwargs)
        elif key == "create_metric_response":
            message = self.metric_create_response(**kwargs)
        elif key == "read_metric_data_response":
            message = self.read_metric_data_response(**kwargs)
        elif key == "delete_metric_response":
            message = self.delete_metric_response(**kwargs)
        elif key == "update_metric_response":
            message = self.update_metric_response(**kwargs)
        elif key == "list_metric_response":
            message = self.list_metric_response(**kwargs)
        elif key == "notify_alarm":
            message = self.notify_alarm(**kwargs)
        else:
            log.warning("Failed to generate a valid response message.")
            message = None

        return message

    def alarm_list_response(self, **kwargs):
        """Generate the response for an alarm list request."""
        alarm_list_resp = {"schema_version": schema_version,
                           "schema_type": "list_alarm_response",
                           "correlation_id": kwargs['cor_id'],
                           "list_alarm_response": kwargs['alarm_list']}
        return json.dumps(alarm_list_resp)

    def create_alarm_response(self, **kwargs):
        """Generate a response for a create alarm request."""
        create_alarm_resp = {"schema_version": schema_version,
                             "schema_type": "create_alarm_response",
                             "alarm_create_response": {
                                 "correlation_id": kwargs['cor_id'],
                                 "alarm_uuid": kwargs['alarm_id'],
                                 "status": kwargs['status']}}
        return json.dumps(create_alarm_resp)

    def delete_alarm_response(self, **kwargs):
        """Generate a response for a delete alarm request."""
        delete_alarm_resp = {"schema_version": schema_version,
                             "schema_type": "alarm_deletion_response",
                             "alarm_deletion_response": {
                                 "correlation_id": kwargs['cor_id'],
                                 "alarm_uuid": kwargs['alarm_id'],
                                 "status": kwargs['status']}}
        return json.dumps(delete_alarm_resp)

    def update_alarm_response(self, **kwargs):
        """Generate a response for an update alarm request."""
        update_alarm_resp = {"schema_version": schema_version,
                             "schema_type": "update_alarm_response",
                             "alarm_update_response": {
                                 "correlation_id": kwargs['cor_id'],
                                 "alarm_uuid": kwargs['alarm_id'],
                                 "status": kwargs['status']}}
        return json.dumps(update_alarm_resp)

    def metric_create_response(self, **kwargs):
        """Generate a response for a create metric request."""
        create_metric_resp = {"schema_version": schema_version,
                              "schema_type": "create_metric_response",
                              "correlation_id": kwargs['cor_id'],
                              "metric_create_response": {
                                  "metric_uuid": kwargs['metric_id'],
                                  "resource_uuid": kwargs['r_id'],
                                  "status": kwargs['status']}}
        return json.dumps(create_metric_resp)

    def read_metric_data_response(self, **kwargs):
        """Generate a response for a read metric data request."""
        read_metric_data_resp = {"schema_version": schema_version,
                                 "schema_type": "read_metric_data_response",
                                 "metric_name": kwargs['m_name'],
                                 "metric_uuid": kwargs['m_id'],
                                 "resource_uuid": kwargs['r_id'],
                                 "correlation_id": kwargs['cor_id'],
                                 "metrics_data": {
                                     "time_series": kwargs['times'],
                                     "metrics_series": kwargs['metrics']}}
        return json.dumps(read_metric_data_resp)

    def delete_metric_response(self, **kwargs):
        """Generate a response for a delete metric request."""
        delete_metric_resp = {"schema_version": schema_version,
                              "schema_type": "delete_metric_response",
                              "metric_name": kwargs['m_name'],
                              "metric_uuid": kwargs['m_id'],
                              "resource_uuid": kwargs['r_id'],
                              "correlation_id": kwargs['cor_id'],
                              "status": kwargs['status']}
        return json.dumps(delete_metric_resp)

    def update_metric_response(self, **kwargs):
        """Generate a repsonse for an update metric request."""
        update_metric_resp = {"schema_version": schema_version,
                              "schema_type": "update_metric_response",
                              "correlation_id": kwargs['cor_id'],
                              "metric_update_response": {
                                  "metric_uuid": kwargs['m_id'],
                                  "status": kwargs['status'],
                                  "resource_uuid": kwargs['r_id']}}
        return json.dumps(update_metric_resp)

    def list_metric_response(self, **kwargs):
        """Generate a response for a list metric request."""
        list_metric_resp = {"schema_version": schema_version,
                            "schema_type": "list_metric_response",
                            "correlation_id": kwargs['cor_id'],
                            "metrics_list": kwargs['m_list']}
        return json.dumps(list_metric_resp)

    def notify_alarm(self, **kwargs):
        """Generate a response to send alarm notifications."""
        notify_alarm_resp = {"schema_version": schema_version,
                             "schema_type": "notify_alarm",
                             "notify_details": {
                                 "alarm_uuid": kwargs['a_id'],
                                 "vdu_name": kwargs['vdu_name'],
                                 "vnf_member_index": kwargs['vnf_member_index'],
                                 "ns_id": kwargs['ns_id'],
                                 "metric_name": kwargs['metric_name'],
                                 "threshold_value": kwargs['threshold_value'],
                                 "operation": kwargs['operation'],
                                 "severity": kwargs['sev'],
                                 "status": kwargs['state'],
                                 "start_date": kwargs['date']}}
        return json.dumps(notify_alarm_resp)
