#!/usb/bin/env python
"""Tests."""
#from mongo_to_hive_mapping import schema_engine

from update import *
import textwrap
#from mongo_to_hive_mapping.schema_engine import *
from gizer.opinsert import *
from gizer.opupdate import *
from update_test_data import *
import pprint
from bson.json_util import loads
import datetime
from dateutil import tz
import pytz

TEST_INFO = 'TEST_OPUPDATE'

'update post_adresse_streets set name="STREETNAME" where post_id="aabbccddeeff" and post_adresses_idx=0, idx=7'

def test_get_obj_id():
    oplog_data = loads(oplog_u_01)
    model = {"id_oid":"56b8da51f9fcee1b00000006"}
    result = get_obj_id(oplog_data)
    assert result == model
    print(TEST_INFO, 'get_obj_id', 'PASSED')


def test_get_obj_id_recursive():
    model = {'aaa_bbb_ccc_ddd_eeee': 'abcdef'}
    assert model == get_obj_id_recursive(test_data_01, [], [])
    print(TEST_INFO, 'get_obj_id_recursive', 'PASSED')

def d(str_date):
    timestamp_fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
    l = datetime.datetime.strptime(str_date, timestamp_fmt)
    return datetime.datetime(l.year, l.month, l.day, l.hour, l.minute, l.second, l.microsecond, tzinfo=pytz.utc)


def test_update():

    oplog_data = loads(oplog_u_01)
    # model = [{'UPDATE post_comments SET body=(%s), created_at=(%s), id_oid=(%s), updated_at=(%s) WHERE posts_id_oid=(%s) and idx=(%s);': ['comment6', d('2016-02-08T19:42:33.589Z'), '56b8efa9f9fcee1b0000000f', d('2016-02-08T19:42:33.589Z'), '56b8da51f9fcee1b00000006', '5']}, {'INSERT INTO post_comments (body, created_at, id_oid, updated_at) VALUES(%s, %s, %s, %s);': ['comment6', d('2016-02-08T19:42:33.589Z'), '56b8efa9f9fcee1b0000000f', d('2016-02-08T19:42:33.589Z'), '56b8da51f9fcee1b00000006', '5']}]
    model = [{'UPDATE post_comments SET body=(%s), created_at=(%s), id_oid=(%s), updated_at=(%s) WHERE posts_id_oid=(%s) and idx=(%s);': ['comment6', d('2016-02-08T19:42:33.589Z'), '56b8efa9f9fcee1b0000000f', d('2016-02-08T19:42:33.589Z'), '56b8da51f9fcee1b00000006', '5']}]
    result = update(schema, oplog_data)
    assert result == model

    oplog_data = loads(oplog_u_02)
    model = [{'UPDATE posts SET updated_at=(%s) WHERE id_oid=(%s);': [d('2016-02-08T19:52:23.883Z'), '56b8da59f9fcee1b00000007']}]
    result = update(schema, oplog_data)
    assert result == model

    oplog_data = loads(oplog_u_03)
    model = [{'DELETE FROM post_comments WHERE (id_oid=(%s));': ['56b8da59f9fcee1b00000007']}, {'INSERT INTO {table} ({columns}) VALUES({values});': []}]
    result = update(schema, oplog_data)
    assert result == model

    oplog_data = loads(oplog_u_04)
    # model = [{'UPDATE post_comments SET body="%s", created_at="%s", id_oid="%s", updated_at="%s" WHERE posts_id_oid="%s" and idx=%s;': ['commments2222', d('2016-02-08T19:58:06.008Z'), '56b8f34ef9fcee1b00000019', d('2016-02-08T19:58:06.008Z'), '56b8da59f9fcee1b00000007', '1']}, {'INSERT INTO post_comments (body, created_at, id_oid, updated_at) VALUES("%s", "%s", "%s", "%s");': ['commments2222', d('2016-02-08T19:58:06.008Z'), '56b8f34ef9fcee1b00000019', d('2016-02-08T19:58:06.008Z'), '56b8da59f9fcee1b00000007', '1']}]
    model = [{'UPDATE post_comments SET body=(%s), created_at=(%s), id_oid=(%s), updated_at=(%s) WHERE posts_id_oid=(%s) and idx=(%s);': ['commments2222', d('2016-02-08T19:58:06.008Z'), '56b8f34ef9fcee1b00000019', d('2016-02-08T19:58:06.008Z'), '56b8da59f9fcee1b00000007', '1']}]
    result = update(schema, oplog_data)
    assert result == model

    oplog_data = loads(oplog_u_05)
    # model = [{'UPDATE post_comments SET created_at="%s", id_oid="%s", updated_at="%s" WHERE posts_id_oid="%s" and idx=%s;': [d('2016-02-08T19:58:22.847Z'), '56b8f35ef9fcee1b0000001a', d('2016-02-08T19:58:22.847Z'), '56b8da59f9fcee1b00000007', '2']}, {'INSERT INTO post_comments (created_at, id_oid, updated_at) VALUES((%s), "%s", "%s");': [d('2016-02-08T19:58:22.847Z'), '56b8f35ef9fcee1b0000001a', d('2016-02-08T19:58:22.847Z'), '56b8da59f9fcee1b00000007', '2']}]
    model = [{'UPDATE post_comments SET created_at=(%s), id_oid=(%s), updated_at=(%s) WHERE posts_id_oid=(%s) and idx=(%s);': [d('2016-02-08T19:58:22.847Z'), '56b8f35ef9fcee1b0000001a', d('2016-02-08T19:58:22.847Z'), '56b8da59f9fcee1b00000007', '2']}]
    result = update(schema, oplog_data)
    assert result == model

    oplog_data = loads(oplog_u_06)
    # model = [{'DELETE FROM post_comments WHERE (id_oid="%s");': ['56b8da59f9fcee1b00000007']}, {'INSERT INTO {table} ({columns}) VALUES({values});': []}]
    model = [{'DELETE FROM post_comments WHERE (id_oid=(%s));': ['56b8da59f9fcee1b00000007']}, {'INSERT INTO {table} ({columns}) VALUES({values});': []}]
    result = update(schema, oplog_data)
    assert result == model

    oplog_data = loads(oplog_u_07)
    # model = [{'DELETE FROM post_comments WHERE (id_oid="%s");': ['56b8da59f9fcee1b00000007']}, {'INSERT INTO {table} ({columns}) VALUES({values});': []}]
    model = [{'DELETE FROM post_comments WHERE (id_oid=(%s));': ['56b8da59f9fcee1b00000007']}, {'INSERT INTO {table} ({columns}) VALUES({values});': []}]
    result = update(schema, oplog_data)
    assert result == model

    oplog_data = loads(oplog_u_08)
    # model = [{'UPDATE posts SET updated_at="%s", title="%s" WHERE id_oid="%s";': [d('2016-02-08T20:02:12.985Z'), 'sada', '56b8f05cf9fcee1b00000010']}]
    model = [{'UPDATE posts SET updated_at=(%s), title=(%s) WHERE id_oid=(%s);': [d('2016-02-08T20:02:12.985Z'), 'sada', '56b8f05cf9fcee1b00000010']}]
    result = update(schema, oplog_data)
    assert result == model

    print(TEST_INFO, 'update', 'PASSED')


pp = pprint.PrettyPrinter(indent=4)


test_get_obj_id()
test_get_obj_id_recursive()
test_update()