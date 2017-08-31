from kafka import KafkaProducer
from kafka.errors import KafkaError
import logging
import json
import os


class KafkaProducer(object):

    def __init__(self, topic, message):

        self._topic= topic
        self._message = message

    if "ZOOKEEPER_URI" in os.environ:
        broker = os.getenv("ZOOKEEPER_URI")
    else:
        broker = "SO-ub.lxd:2181"

        '''
        If the zookeeper broker URI is not set in the env, by default,
        SO-ub.lxd container is taken as the host because an instance of
        is already running.
        '''

        producer = KafkaProducer(key_serializer=str.encode,
                   value_serializer=lambda v: json.dumps(v).encode('ascii'),
                   bootstrap_servers=broker, api_version=(0,10))


    def publish(self, key, message, topic=None):
        try:
            future = producer.send('alarms', key, payload)
            producer.flush()
        except Exception:
            log.exception("Error publishing to {} topic." .format(topic))
            raise
        try:
            record_metadata = future.get(timeout=10)
            self._log.debug("TOPIC:", record_metadata.topic)
            self._log.debug("PARTITION:", record_metadata.partition)
            self._log.debug("OFFSET:", record_metadata.offset)
        except KafkaError:
            pass

    def configure_alarm(self, key, message, topic):

        payload_configure = {
            "alarm_configuration":
             {
               "schema_version": 1.0,
               "schema_type": "configure_alarm",
               "alarm_configuration":
               {
                 "metric_name": { "type": "string" },
                 "tenant_uuid": { "type": "string" },
                 "resource_uuid": { "type": "string" },
                 "description": { "type": "string" },
                 "severity": { "type": "string" },
                 "operation": { "type": "string" },
                 "threshold_value": { "type": "integer" },
                 "unit": { "type": "string" },
                 "statistic": { "type": "string" }
               },
               "required": [ "schema_version",
                             "schema_type",
                             "metric_name",
                             "resource_uuid",
                             "severity",
                             "operation",
                             "threshold_value",
                             "unit",
                             "statistic" ]
             }
           }

        publish(key, value=json.dumps(payload_configure), topic='alarms')

    def notify_alarm(self, key, message, topic):

        payload_notify = {
            "notify_alarm":
            {
              "schema_version": 1.0,
              "schema_type": "notify_alarm",
              "notify_details":
              {
                "alarm_uuid": { "type": "string" },
                "resource_uuid": { "type": "string" },
                "description": { "type": "string" },
                "tenant_uuid": { "type": "string" },
                "severity": { "type" : ["integer", "string"] },
                "status": { "type": "string" },
                "start_date": { "type": "date-time" },
                "update_date": { "type": "date-time" },
                "cancel_date": { "type": "date-time" }
              },
              "required": [ "schema_version",
                            "schema_type",
                            "alarm_uuid",
                            "resource_uuid",
                            "tenant_uuid",
                            "severity",
                            "status",
                            "start_date" ]
            }
         }

        publish(key, value=json.dumps(payload_notify), topic='alarms')

    def alarm_ack(self, key, message, topic):

        payload_ack = {
            "alarm_ack":
            {
              "schema_version": 1.0,
              "schema_type": "alarm_ack",
              "ack_details":
              {
                "alarm_uuid": { "type": "string" },
                "tenant_uuid": { "type": "string" },
                "resource_uuid": { "type": "string" }
              },
              "required": [ "schema_version",
                            "schema_type",
                            "alarm_uuid",
                            "tenant_uuid",
                            "resource_uuid" ]
            }
          }

        publish(key, value.json.dumps(payload_ack), topic='alarms')

    def configure_metrics(self, key, message, topic):

        payload_configure_metrics = {
            "configure_metrics":
            {
              "schema_version": 1.0,
              "schema_type": "configure_metrics",
              "tenant_uuid": { "type": "string" },
              "metrics_configuration":
              {
                "metric_name": { "type": "string" },
                "metric_unit": { "type": "string" },
                "resource_uuid": { "type": "string" }
              },
              "required": [ "schema_version",
                            "schema_type",
                            "metric_name",
                            "metric_unit",
                            "resource_uuid" ]
            }
          }

        publish(key, value.json.dumps(payload_configure_metrics), topic='metrics')

    def metric_data_request(self, key, message, topic):

        payload_metric_data_request = {
            "metric_data_request":
            {
              "schema_version": 1.0,
              "schema_type": "metric_data_request",
              "metric_name": { "type": "string" },
              "resource_uuid": { "type": "string" },
              "tenant_uuid": { "type": "string" },
              "collection_period": { "type": "string" }
            },
            "required": ["schema_version",
                         "schema_type",
                         "tenant_uuid",
                         "metric_name",
                         "collection_period",
                         "resource_uuid"]
          }

        publish(key, value.json.dumps(payload_metric_data_request), topic='metrics')

    def metric_data_response(self, key, message, topic):

        payload_metric_data_response = {
            "metric_data_response":
            {
              "schema_version": 1.0,
              "schema_type": "metric_data_response",
              "metrics_name": { "type": "string" },
              "resource_uuid": { "type": "string" },
              "tenant_uuid": { "type": "string" },
              "metrics_data":
              {
                "time_series": { "type": "array" },
                "metrics_series": { "type": "array" }
              }
            },
            "required": [ "schema_version",
                          "schema_type",
                          "metrics_name",
                          "resource_uuid",
                          "tenant_uuid",
                          "time_series",
                          "metrics_series" ]
          }

        publish(key, value.json.dumps(payload_metric_data_response), topic='metrics')

    def access_credentials(self, key, message, topic):

        payload_access_credentials = {
            "access_credentials":
            {
              "schema_version": 1.0,
              "schema_type": "vim_access_credentials",
              "vim_type": { "type": "string" },
              "required": [ "schema_version",
                            "schema_type",
                            "vim_type" ],
              "access_config":
              {
                "if":
                {
                  "vim_type": "openstack"
                },
                "then":
                {
                  "openstack-site": { "type": "string" },
                  "user": { "type": "string" },
                  "password": { "type": "string",
                                "options": { "hidden": true }},
                  "vim_tenant_name": { "type": "string" }
                },
                "required": [ "openstack_site",
                              "user",
                              "password",
                              "vim_tenant_name" ],
                "else":
                {
                  "vim_type": "aws"
                },
                "then":
                {
                  "aws_site": { "type": "string" },
                  "user": { "type": "string" },
                  "password": { "type": "string",
                                "options": { "hidden": true }},
                  "vim_tenant_name": { "type": "string" }
                },
                "required": [ "aws_site",
                              "user",
                              "password",
                              "vim_tenant_name" ],
                "else":
                {
                  "vim_type": "VMWare"
                },
                "then":
                {
                  "vrops_site": { "type": "string" },
                  "vrops_user": { "type": "string" },
                  "vrops_password": { "type": "string",
                                      "options": { "hidden": true }},
                  "vcloud_site": { "type": "string" },
                  "admin_username": { "type": "string" },
                  "admin_password": { "type": "string",
                                      "options": { "hidden": true }},
                  "nsx_manager": { "type": "string" },
                  "nsx_user": { "type": "string" },
                  "nsx_password": { "type": "string",
                                    "options": { "hidden": true }},
                  "vcenter_ip": { "type": "string" },
                  "vcenter_port": { "type": "string" },
                  "vcenter_user": { "type": "string" },
                  "vcenter_password": { "type": "string",
                                        "options": { "hidden": true }},
                  "vim_tenant_name": { "type": "string" },
                  "org_name": { "type": "string" }
                },
                "required": [ "vrops_site",
                              "vrops_user",
                              "vrops_password",
                              "vcloud_site",
                              "admin_username",
                              "admin_password",
                              "vcenter_ip",
                              "vcenter_port",
                              "vcenter_user",
                              "vcenter_password",
                              "vim_tenant_name",
                              "orgname" ]
              }
            }
          }

        publish(key, value.json.dumps(payload_access_credentials), topic='access_credentials')
