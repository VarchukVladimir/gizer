#!/usr/bin/env python

""" Implementation of ComparatorMongoPsql """

__author__ = "Yaroslav Litvinov"
__copyright__ = "Copyright 2016, Rackspace Inc."
__email__ = "yaroslav.litvinov@rackspace.com"

from logging import getLogger
from collections import namedtuple
from gizer.etl_mongo_reader import EtlMongoReader
from gizer.psql_objects import load_single_rec_into_tables_obj
from gizer.psql_objects import cmp_psql_mongo_tables
from mongo_reader.prepare_mongo_request import prepare_mongo_request_for_list
from mongo_schema.schema_engine import create_tables_load_bson_data

# comparator is using for data integrity verification
MONGO_PSQL_CMP_BSON_WORKERS_COUNT = 8
MONGO_PSQL_CMP_QUEUE_SIZE = MONGO_PSQL_CMP_BSON_WORKERS_COUNT*2

CompareRes = namedtuple('CompareRes', ['rec_id', 'flag', 'attempt'])

def async_worker_handle_mongo_rec(schema_engines,
                                  rec_data_and_collection):
    """ function intended to call by FastQueueProcessor.
    process mongo record / bson data in separate process.
    schema_engines -- dict {'collection name': SchemaEngine}. Here is
    many schema engines to use every queue to handle items from any collection;
    rec_data_and_collection - tuple('collection name', bson record)"""
    rec = rec_data_and_collection[0]
    collection = rec_data_and_collection[1]
    return create_tables_load_bson_data(schema_engines[collection],
                                        [rec])

class ComparatorMongoPsql:
    """ Compare records data from Mongo DB and Postgres DB.
        Class object is fetching all required data then doing comparisons and
        getting result as Boolean."""

    def __init__(self, schema_engines, mongo_readers, psql, psql_schema):
        self.schema_engines = schema_engines
        self.mongo_readers = mongo_readers
        self.psql = psql
        self.psql_schema = psql_schema
        self.recs_to_compare = {}
        self.etl_mongo_reader = EtlMongoReader(MONGO_PSQL_CMP_BSON_WORKERS_COUNT,
                                               MONGO_PSQL_CMP_QUEUE_SIZE,
                                               async_worker_handle_mongo_rec,
                                               #1st worker param
                                               self.schema_engines, 
                                               self.mongo_readers)

    def __del__(self):
        del self.etl_mongo_reader

    def add_to_compare(self, collection_name, rec_id, attempt):
        if collection_name not in self.recs_to_compare:
            self.recs_to_compare[collection_name] = {}
        # every time item adding to compare list will reset old state
        # distinguish dict key and rec_id as rec_id can be a mongo object
        getLogger(__name__).info("%s is rec_id attempt=%d" % (str(rec_id), attempt))
        self.recs_to_compare[collection_name][str(rec_id)] \
            = CompareRes(rec_id, False, attempt)

    def compare_one_src_dest(self, collection_name, rec_id, 
                             mongo_tables_obj, psql_tables_obj):
        schema_engine = self.schema_engines[collection_name]
        mongo_reader = self.mongo_readers[collection_name]
        getLogger(__name__).info("comparing... rec_id=" + str(rec_id))
        equal = cmp_psql_mongo_tables(rec_id, mongo_tables_obj, psql_tables_obj)
        getLogger(__name__).info("compare res=" + str(equal) + 
                                 " for rec_id=" + str(rec_id))
        return equal

    def compare_src_dest(self):
        cmp_res = True
        # iterate mongo items belong to one collection
        for collection, recs in self.recs_to_compare.iteritems():
            # comparison strategy: filter out previously compared recs;
            # so will be compared only that items which never compared or
            # prev comparison gave False
            recs_list_cmp = []
            max_recs_in_list = 1000
            for rec_id, compare_res in recs.iteritems():
                if not compare_res.flag:
                    recs_list_cmp.append(compare_res.rec_id)
            # if nothing to compare just skip current collection
            if not recs_list_cmp:
                continue

            maxs = 1000
            lst = recs_list_cmp
            splitted = [lst[i:i + maxs] for i in xrange(0, len(lst), maxs)]
            for chunk in splitted:
                res = self.compare_src_dest_portion(collection, chunk)
                if not res:
                    cmp_res = res
        return cmp_res

    def compare_src_dest_portion(self, collection, recs):
        getLogger(__name__).info('Compare recs: %s' % self.recs_to_compare )
        cmp_res = True
        # prepare query
        mongo_query = prepare_mongo_request_for_list(
            self.schema_engines[collection], recs)
        getLogger(__name__).debug('query to fetch recs for cmp: %s', mongo_query)
        self.etl_mongo_reader.execute_query(collection, mongo_query)
        received_list = []
        # get and process records to compare
        processed_recs = self.etl_mongo_reader.next_processed()
        while processed_recs is not None:
            # do cmp for every returned obj
            for mongo_tables_obj in processed_recs:
                rec_id = mongo_tables_obj.rec_id()
                received_list.append(rec_id)
                psql_tables_obj = load_single_rec_into_tables_obj(
                    self.psql,
                    self.schema_engines[collection],
                    self.psql_schema,
                    rec_id )
                # this check makes sence ony for mock transport as it 
                # will return all records and not only requested
                key = str(rec_id)
                if key in self.recs_to_compare[collection] and \
                        not self.recs_to_compare[collection][key].flag:
                    equal = self.compare_one_src_dest(collection,
                                                      rec_id,
                                                      mongo_tables_obj,
                                                      psql_tables_obj)
                    if not equal:
                        cmp_res = False
                else:
                    continue
                # update cmp result in main dict
                attempt = self.recs_to_compare[collection][key].attempt
                # update cmp result in main dict
                self.recs_to_compare[collection][key] = \
                    CompareRes(rec_id, equal, attempt)
            processed_recs = self.etl_mongo_reader.next_processed()
        # should return True for deleted items (non existing items)
        for rec_id in recs:
            if rec_id not in received_list:
                psql_tables_obj = load_single_rec_into_tables_obj(
                    self.psql,
                    self.schema_engines[collection],
                    self.psql_schema,
                    rec_id )
                # if psql data also doesn't exist
                if psql_tables_obj.is_empty():
                    key = str(rec_id)
                    attempt = self.recs_to_compare[collection][key].attempt
                    self.recs_to_compare[collection][key] = \
                        CompareRes(rec_id, True, attempt)                    
                    getLogger(__name__).info("cmp non existing rec_id %s."
                                             % (str(rec_id)))
        return cmp_res

    def get_failed_cmp_attempts(self):
        failed_attempts_list = []
        for collection, recs in self.recs_to_compare.iteritems():
            for rec_id, compare_res in recs.iteritems():
                if not compare_res.flag and \
                        compare_res.attempt not in failed_attempts_list:
                    failed_attempts_list.append(compare_res.attempt)
        failed_attempts_list.sort()
        return failed_attempts_list
    
