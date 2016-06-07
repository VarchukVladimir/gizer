#!/usr/bin/env python

""" Oplog parser, and patcher of end data by oplog operations.
Oplog synchronization with initially loaded data stored in psql.
OplogParser -- class for basic oplog parsing
do_oplog_apply -- handling oplog and applying oplog ops func
sync_oplog -- find syncronization point in oplog for initially loaded data."""

__author__ = "Yaroslav Litvinov"
__copyright__ = "Copyright 2016, Rackspace Inc."
__email__ = "yaroslav.litvinov@rackspace.com"

import bson
import sys
from os import environ
from bson.json_util import loads
from collections import namedtuple
from gizer.oppartial_record import get_tables_data_from_oplog_set_command
from gizer.psql_objects import load_single_rec_into_tables_obj
from gizer.psql_objects import insert_rec_from_one_tables_set_to_another
from gizer.psql_objects import create_psql_tables
from gizer.oplog_parser import OplogParser
from gizer.oplog_parser import exec_insert
from gizer.oplog_parser import cb_before
from gizer.oplog_handlers import cb_insert
from gizer.oplog_handlers import cb_update
from gizer.oplog_handlers import cb_delete
from gizer.etlstatus_table import timestamp_str_to_object
from gizer.all_schema_engines import get_schema_engines_as_dict
from mongo_reader.prepare_mongo_request import prepare_mongo_request
from mongo_reader.prepare_mongo_request import prepare_oplog_request
from mongo_schema.schema_engine import create_tables_load_bson_data


Callback = namedtuple('Callback', ['cb', 'ext_arg'])
OplogApplyRes = namedtuple('OplogApplyRes', 
                           ['ts', # oplog timestamp
                            'res', # True/False res
                            'compare' # compare result as dict {rec_id: bool} 
                            ])

def message(mes, cr='\n'):
    sys.stderr.write( mes + cr)

def create_truncate_psql_objects(psql, schemas_path, psql_schema):
    """ drop and create tables for all collections """
    schema_engines = get_schema_engines_as_dict(schemas_path)
    for schema_name, schema in schema_engines.iteritems():
        tables_obj = create_tables_load_bson_data(schema, None)
        drop = True
        create_psql_tables(tables_obj, psql, psql_schema, '', drop)
        psql.cursor.execute("COMMIT")

def compare_psql_and_mongo_records(psql, mongo_reader, schema_engine, rec_id,
                                   dst_schema_name):
    """ Return True/False. Compare actual mongo record with record's relational
    model from operational tables. Comparison of non existing objects gets True.
    psql -- psql cursor wrapper
    mongo_reader - mongo cursor wrapper tied to specific collection
    schema_engine -- 'SchemaEngine' object
    rec_id - record id to compare
    dst_schema_name -- psql schema name where psql tables store that record"""
    res = None
    psql_tables_obj = load_single_rec_into_tables_obj(psql,
                                                      schema_engine,
                                                      dst_schema_name,
                                                      rec_id)
    mongo_tables_obj = None
    # retrieve actual mongo record and transform it to relational data
    query = prepare_mongo_request(schema_engine, rec_id)
    mongo_reader.make_new_request(query)
    rec = mongo_reader.next()
    if not rec:
        if psql_tables_obj.is_empty():
            # comparison of non existing objects gets True
            res= True
        else:
            res = False
    else:
        mongo_tables_obj = create_tables_load_bson_data(schema_engine,
                                                        [rec])
        compare_res = mongo_tables_obj.compare(psql_tables_obj)
        # save result of comparison
        res = compare_res
    message("rec_id=" + str(rec_id) + ", compare res=" + str(res))
    return res


class OplogHighLevel:
    def __init__(self, psql, mongo_readers, oplog,
                 schemas_path, schema_engines, psql_schema_to_apply_ops,
                 psql_schema_initial_load=None):
        """ params:
        psql -- Postgres cursor wrapper
        mongo_readers -- dict of mongo readers, one per collection
        oplog -- Mongo oplog cursor wrappper
        schemas_path -- Path with js schemas representing mongo collections
        psql_schema_to_apply_ops -- psql schema whose tables data to patch.
        psql_schema_initial_load -- optional param, psql schema whose data
        is source for copying into tables of psql_schema_to_apply_ops
        where data will be pacthed by oplog operations. If not specified then data
        in psql_schema_to_apply_ops will be patched directly without preparing."""
        self.psql = psql
        self.mongo_readers = mongo_readers
        self.oplog = oplog
        self.schemas_path = schemas_path
        self.schema_engines = schema_engines
        self.psql_schema_to_apply_ops = psql_schema_to_apply_ops
        self.psql_schema_initial_load = psql_schema_initial_load
        self.compare = {}

    def do_oplog_apply(self, start_ts):
        """ Read oplog operations starting just after timestamp start_ts.
        Apply oplog operations to psql db.
        Compare source (mongo) and dest(psql) records.
        Return named tuple - Self.OplogApplyRes. Where:
        Self.OplogApplyRes.ts is ts to apply operations.
        Self.OplogApplyRes.res is result of applying self.oplog operations.
        False - apply failed.
        Self.OplogApplyRes.compare dict of results of comparison of all affected
        recs from mongo with their relational model taken from psql;
        This function is using Self.OplogParser itself.
        params:
        start_ts -- Timestamp of record in self.oplog db which should be
        applied first or next available"""
    
        compare_rec_ids = {} # {collection: {rec_ids: bool}}
        if self.psql_schema_initial_load is None:
            callback_before = None
        else:
            callback_before = cb_before
        
        self.oplog_query = prepare_oplog_request(start_ts)
        self.oplog.make_new_request(self.oplog_query)
        # create self.oplog parser
        parser = OplogParser(self.oplog, self.schemas_path, \
                    Callback(callback_before,
                             ext_arg=(self.psql,
                                      self.psql_schema_initial_load,
                                      self.psql_schema_to_apply_ops)),
                    Callback(cb_insert, ext_arg=self.psql_schema_to_apply_ops),
                    Callback(cb_update, ext_arg=(self.psql,
                                                 self.psql_schema_to_apply_ops)),
                    Callback(cb_delete, ext_arg=(self.psql,
                                                 self.psql_schema_to_apply_ops)))
        # go over self.oplog, and apply all self.oplog pacthes starting from start_ts
        self.oplog_queries = parser.next()
        while self.oplog_queries != None:
            for self.oplog_query in self.oplog_queries:
                if self.oplog_query.op == "u" or \
                   self.oplog_query.op == "d" or \
                   self.oplog_query.op == "i" or self.oplog_query.op == "ui":
                    # add rec_id only if query executed
                    exec_insert(self.psql, self.oplog_query)
                    collection_name = parser.item_info.schema_name
                    rec_id = parser.item_info.rec_id
                    self.add_to_compare(collection_name, rec_id)
            self.oplog_queries = parser.next()
        # compare mongo data & psql data after self.oplog records applied
        sync_res = self.compare_src_dest()
        if parser.first_handled_ts: # self.oplog applied with res
            return OplogApplyRes(parser.first_handled_ts, sync_res, compare_rec_ids)
        else: # no self.oplog records to apply
            return OplogApplyRes(start_ts, True, compare_rec_ids)

    def do_oplog_sync(self, ts):
        """ Oplog sync is using local psql database with all data from main psql db
        for applying test patches from mongodb oplog. It's expected high intensive
        queries execution flow. The result of synchronization would be a single
        timestamp from oplog which is last operation applied to data which resides
        in main psql database. If TS is not located then synchronization failed.
        do oplog sync, return ts - last ts which is part of initilly loaded data
        params:
        ts -- oplog timestamp which is start point to locate sync point"""
    
        schema_engines = get_schema_engines_as_dict(self.schemas_path)
    
        # erase operational psql schema
        create_truncate_psql_objects(self.psql, self.schemas_path,
        self.psql_schema_to_apply_ops)
    
        # oplog_ts_to_test is timestamp starting from which oplog records
        # should be applied to psql tables to locate ts which corresponds to
        # initially loaded psql data;
        # None - means oplog records should be tested starting from beginning
        oplog_ts_to_test = ts
        sync_res = self._sync_oplog(oplog_ts_to_test)
        while True:
            if sync_res is False or sync_res is True:
                break
            else:
                oplog_ts_to_test = sync_res
            sync_res = self._sync_oplog(oplog_ts_to_test)
        print "sync_res=", sync_res, " oplog_ts_to_test=", oplog_ts_to_test
        if sync_res:
            # if oplog sync point is located at None, then all oplog ops
            # must be applied starting from first ever ts
            if not oplog_ts_to_test:
                return True;
            else:
                return oplog_ts_to_test
        else: 
            return None
    

    def _sync_oplog(self, test_ts):
        """ Find syncronization point of oplog and psql data
        (which usually is initially loaded data.)
        Return True if able to locate and synchronize initially loaded data
        with oplog data, or return next ts candidate for syncing.
        start_ts -- Timestamp of oplog record to start sync tests"""
        # create/truncate psql operational tables
        # which are using during oplog tail lookup
        create_truncate_psql_objects(self.psql,
    				 self.schemas_path, 
    				 self.psql_schema_to_apply_ops)
        ts_sync = self.do_oplog_apply(test_ts)
        if ts_sync.res == True:
            # sync succesfull if sync ok and was handled non null ts
            self.psql.cursor.execute('COMMIT')
            return True
        elif ts_sync.ts:
            message("failed to sync ts=" + str(test_ts) +
                    ", try next ts=" + str(ts_sync.ts))
            # next sync iteration, starting from ts_sync.ts
            return ts_sync.ts
        else:
            return False

    def add_to_compare(self, collection_name, rec_id):
        if collection_name not in self.compare:
            self.compare[collection_name] = {}
        if rec_id not in self.compare[collection_name]:
            self.compare[collection_name][rec_id] = False # by default

    def compare_src_dest(self):
        # compare mongo data & psql data after self.oplog records applied
        for collection_name, recs in self.compare.iteritems():
            schema_engine = self.schema_engines[collection_name]
            mongo_reader = self.mongo_readers[collection_name]
            for rec_id in recs:
                equal = compare_psql_and_mongo_records(self.psql,
                                                       mongo_reader,
                                                       schema_engine,
                                                       rec_id,
                                                       self.psql_schema_to_apply_ops)
                self.compare[collection_name][rec_id] = equal
                if not equal:
                    return False
        return True
