import logging

from peewee import *
from playhouse.sqlite_ext import SqliteExtDatabase

from osm_policy_module.core.config import Config

log = logging.getLogger(__name__)
cfg = Config.instance()

db = SqliteExtDatabase('mon.db')


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
