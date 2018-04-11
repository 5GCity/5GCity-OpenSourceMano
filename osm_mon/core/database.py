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

from osm_mon.plugins.OpenStack.settings import Config

log = logging.getLogger(__name__)
cfg = Config.instance()

db = SqliteExtDatabase('mon.db')


class BaseModel(Model):
    class Meta:
        database = db


class VimCredentials(BaseModel):
    uuid = CharField(unique=True)
    name = CharField()
    type = CharField()
    url = CharField()
    user = CharField()
    password = CharField()
    tenant_name = CharField()
    config = TextField(null=True)


class Alarm(BaseModel):
    alarm_id = CharField()
    credentials = ForeignKeyField(VimCredentials, backref='alarms')


class DatabaseManager:
    def create_tables(self):
        try:
            db.connect()
            db.create_tables([VimCredentials, Alarm])
            db.close()
        except Exception as e:
            log.exception("Error creating tables: ")

    def get_credentials(self, vim_uuid):
        return VimCredentials.get_or_none(VimCredentials.uuid == vim_uuid)

    def save_credentials(self, vim_credentials):
        """Saves vim credentials. If a record with same uuid exists, overwrite it."""
        exists = VimCredentials.get_or_none(VimCredentials.uuid == vim_credentials.uuid)
        if exists:
            vim_credentials.id = exists.id
        vim_credentials.save()

    def get_credentials_for_alarm_id(self, alarm_id, vim_type):
        alarm = Alarm.select() \
            .where(Alarm.alarm_id == alarm_id) \
            .join(VimCredentials) \
            .where(VimCredentials.type == vim_type).get()
        return alarm.credentials

    def save_alarm(self, alarm_id, vim_uuid):
        """Saves alarm. If a record with same id and vim_uuid exists, overwrite it."""
        alarm = Alarm()
        alarm.alarm_id = alarm_id
        creds = VimCredentials.get(VimCredentials.uuid == vim_uuid)
        alarm.credentials = creds
        exists = Alarm.select(Alarm.alarm_id == alarm.alarm_id) \
            .join(VimCredentials) \
            .where(VimCredentials.uuid == vim_uuid)
        if len(exists):
            alarm.id = exists[0].id
        alarm.save()
