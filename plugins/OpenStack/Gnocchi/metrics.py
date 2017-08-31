"""Gnocchi acts on a metric message received from the SO via MON."""

import json
import logging as log

from kafka import KafkaConsumer

from plugins.OpenStack.common import Common


class Metrics(object):
    """Gnocchi based metric actions performed on info from MON."""

    def __init__(self):
        """Initialize the metric actions."""
        self._common = Common()

        # TODO(mcgoughh): Initialize a generic consumer object to consume
        # message from the SO. This is hardcoded for now
        server = {'server': 'localhost:9092', 'topic': 'metrics'}
        self._consumer = KafkaConsumer(server['topic'],
                                       group_id='my-group',
                                       bootstrap_servers=server['server'])

        # TODO(mcgoughh): Initialize a producer to send messages bask to the SO

    def metric_calls(self):
        """Consume info from the message bus to manage metrics."""
        # Concumer check for metric messages
        for message in self._consumer:

            if message.topic == "metrics":
                log.info("Metric action required on this topic: %s",
                         (message.topic))

                if message.key == "configure_metric":
                    # Configure/Update a resource and its metric
                    values = json.loads(message.value)
                    schema = values['configure_metrics']
                    metric_details = schema['metrics_configuration']

                    # Generate authentication credentials via keystone:
                    # auth_token, endpoint
                    auth_token = self._common._authenticate(
                        schema['tenant_uuid'])
                    endpoint = self._common.get_endpoint("metric")

                    metric_id = self.configure_metric(
                        endpoint, auth_token, metric_details)
                    log.info("New metric created with metricID: %s", metric_id)

                    # TODO(mcgoughh): will send an acknowledge message back on
                    # the bus via the producer

                # TODO(mcoughh): Key alternatives are "metric_data_request" and
                # "metric_data_response" will be accomodated later
                # Will also need a producer for this functionality
                elif message.key == "metric_data_request":
                    log.debug("Key used to request a metrics data")

                elif message.key == "metric_data_response":
                    log.debug("Key used for a metrics data response")

                else:
                    log.debug("Unknown key, no action will be performed")

            else:
                log.info("Message topic not relevant to this plugin: %s",
                         message.topic)

        return

    def configure_metric(self, endpoint, auth_token, values):
        """Create the new SO desired metric in Gnocchi."""
        metric_id = None

        # TODO(mcgoughh): error check the values sent in the message
        # will query the database for the request resource and then
        # check that resource for the desired metric
        metric_name = values['metric_name']

        if metric_id is None:

            # Need to create a new version of the resource for gnocchi to
            # the new metric
            resource_url = "{}/v1/resource/generic".format(endpoint)

            metric = {'name': metric_name,
                      'unit': values['metric_unit'], }

            resource_payload = json.dumps({'id': values['resource_uuid'],
                                           'metrics': {metric_name: metric}})

            new_resource = self._common._perform_request(
                resource_url, auth_token,
                req_type="post", payload=resource_payload)
            new_metric = json.loads(new_resource.text)['metrics']

            return new_metric[metric_name]
        else:
            return metric_id

    def delete_metric(self, endpoint, auth_token, metric_id):
        """Delete metric."""
        url = "{}/v1/metric/%s".format(endpoint) % (metric_id)

        self._common._perform_request(url, auth_token, req_type="delete")
        return None

    def list_metrics(self, endpoint, auth_token):
        """List all metrics."""
        url = "{}/v1/metric/".format(endpoint)

        metric_list = self._common._perform_request(
            url, auth_token, req_type="get")
        return json.loads(metric_list.text)
