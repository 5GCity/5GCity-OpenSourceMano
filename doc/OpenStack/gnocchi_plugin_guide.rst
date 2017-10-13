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

Gnocchi Plugin Guide for OSM MON
********************************
The Gnocchi plugin for the MON module allows an OSM user to utilise metric and
resource functionality from their OpenStack deployment.

This plugin allows you to create, list, delete and read metric data.

    .. note::


     An update metric request can also be performed but Gnocchi does not
     support this functionality, your request will just be logged.

Supported Metrics
-----------------
Currently this plugin only supports the following metrics:

* AVERAGE_MEMORY_UTILIZATION
* DISK_READ_OPS
* DISK_WRITE_OPS
* DISK_READ_BYTES
* DISK_WRITE_BYTES
* PACKETS_DROPPED
* PACKETS_RECEIVED
* PACKETS_SENT
* CPU_UTILIZATION

Configuring a Metric
--------------------
Any of the above OpenStack metrics can be configured based on the following
configuration options:

* Resource_uuid: Specifies the resource that your metric will be configured for.
* Metric_name: Specify one of the above metrics for your desired resource.
* Metric_unit: the unit that you wish your metric to be monitored in.

    .. note::


     Your metric can only be specified once for a particular resource.

Deleting a Metric
-----------------
To delete a metric all that is required is to specify the metric_uuid of the
metric you wish to delete.

Listing Metrics
---------------
A full list of OSM generated metrics can be created by perform a list request
without defining any list parameters.

Specific lists can also be created based on two different input parameters:

* Metric_name
* Resource_uuid

These parameters will generate a list of metrics that have the metric_name
and/or the resource_uuid defined. These parameters can be defined seperately or
in combination.

Reading Metric Data
-------------------
To define what metric data you want to read from the Gnocchi database a no. of
parameters have to be defined:

* Metric_uuid: To define which metric's data you would like to read.
* Collection_unit: Defines the unit of time that you want to read the metric
  data over.

    .. note::


     The units that you can define include: HR, DAY, WEEK, MONTH, YEAR.

* Collection_period: defines the integer value of the collection period.
  E.g. 1 DAY.

This type of request results in a list of data values and a corresponding list
of timestamps.
