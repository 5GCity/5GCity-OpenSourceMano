..
       # Copyright 2017 Intel Research and Development Ireland Limited
       # *************************************************************
       # This file is part of OSM Monitoring module
       # All Rights Reserved to Intel Corporation
       #
       # Licensed under the Apache License, Version 2.0 (the "License"); you
       # may not use this file except in compliance with the License. You may
       # obtain a copy of the License at
       #
       #         http://www.apache.org/licenses/LICENSE-2.0
       #
       # Unless required by applicable law or agreed to in writing, software
       # distributed under the License is distributed on an "AS IS" BASIS,
       # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
       # implied. See the License for the specific language governing
       # permissions and limitations under the License.
       #
       # For those usages not covered by the Apache License, Version 2.0 please
       # contact: helena.mcgough@intel.com or adrian.hoban@intel.com

MON Usage Guide
***************
This is a guide on how to use the MON module and its three plugins.

The MON module sends requests to an from the SO via an Apache Kafka message
bus. Currently each message is sent on the message bus in json format, along
with a unique request key and its topic.

The topics that the plugins will consume messages based on are:

* alarm_request
* metric_request

Each type of request has it's own unique key:
* create_alarm_request
* create_metric_request
* list_alarm_request
* list_metric_request
* delete_alarm_request
* delete_metric_request
* update_alarm_request
* update_metric_request
* acknowledge_alarm_request
* read_metric_data_request

In return the plugins will send messages back to the SO with the following
topics:

* alarm_response
* metric_response

Each request has a corresponding response key:
* create_alarm_reponse
* create_metric_response
* list_alarm_response
* list_metric_response
* delete_alarm_response
* delete_metric_response
* update_alarm_response
* update_metric_response
* acknowledge_alarm_response
* read_metric_data_response

  .. note::

      There is an additional response key to send notifications to the SO
      when an alarm has been triggered:
      * notify_alarm

Sending Request Messages
------------------------
For each of the request message that can be sent there is a json schema defined
in the models directory of the MON repo:
: `</MON/osm_mon/core/models/>`

To send a valid message to the MON module for use by one of the plugins, your
message must match the json schema for that request type.

Once you have created a valid json object with your message you can send it on
the message bus with the required topic and key.

To ensure that the correct plugin uses your message you must also specify the
vim_type correctly:

    +----------------------+----------------------+
    |       Plugin         |      vim_type        |
    +----------------------+----------------------+
    | CloudWatch           | cloudwatch           |
    |                      |                      |
    | OpenStack            | openstack            |
    |                      |                      |
    | vROPs                | vrops                |
    +----------------------+----------------------+


* Example
  A create alarm request for the vROPs plugin would be sent with the following
  information:

    - topic: alarm_request
    - create_alarm_request
    - message: a valid message that matches the json schema, with the vim_type
      specified as vrops

A KafkaProducer is used to send the message and it will be consumed by a
KafkaConsumer which is running for each plugin


  .. note::

        The SO support for sending and receiving messages is currently not
        supported. Support will be added in a later release.
