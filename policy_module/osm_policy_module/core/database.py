# -*- coding: utf-8 -*-

# Copyright 2018 Whitestack, LLC
# *************************************************************

# This file is part of OSM Monitoring module
# All Rights Reserved to Whitestack, LLC

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
# contact: bdiaz@whitestack.com or glavado@whitestack.com
##
import logging

from peewee import *
from playhouse.sqlite_ext import SqliteExtDatabase

from osm_policy_module.core.config import Config

log = logging.getLogger(__name__)
cfg = Config.instance()

db = SqliteExtDatabase('policy_module.db')


class BaseModel(Model):
    class Meta:
        database = db


class ScalingRecord(BaseModel):
    nsr_id = CharField()
    name = CharField()
    content = TextField()


class ScalingAlarm(BaseModel):
    alarm_id = CharField()
    action = CharField()
    scaling_record = ForeignKeyField(ScalingRecord, related_name='scaling_alarms')


class DatabaseManager:
    def create_tables(self):
        try:
            db.connect()
            db.create_tables([ScalingRecord, ScalingAlarm])
            db.close()
        except Exception as e:
            log.exception("Error creating tables: ")
