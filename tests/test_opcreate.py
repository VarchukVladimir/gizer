#!/usr/bin/env python

import os
from mongo_to_hive_mapping.test_schema_engine import get_schema_engine, get_schema_tables
from gizer.opcreate import generate_create_table_statement
from mongo_to_hive_mapping import schema_engine

files = {'a_inserts': ('../test_data/opinsert/json_schema2.txt',
                       '../test_data/opinsert/bson_data2.txt')}

def get_schema_engine(collection_name):
    dirpath=os.path.dirname(os.path.abspath(__file__))
    schema_fname = files[collection_name][0]
    schema_path = os.path.join(dirpath, schema_fname)
    return schema_engine.create_schema_engine(collection_name, schema_path)

def get_schema_tables(schema_engine_obj):
    collection_name = schema_engine_obj.root_node.name
    dirpath=os.path.dirname(os.path.abspath(__file__))
    data_fname = files[collection_name][1]
    data_path = os.path.join(dirpath, data_fname)
    return schema_engine.create_tables_load_file(schema_engine_obj, \
                                                 data_path)


def test_insert1():
    collection_name = 'a_inserts'
    schema_engine = get_schema_engine(collection_name)
    tables = get_schema_tables(schema_engine)
    assert(tables.tables.keys() == ['a_insert_comment_items',
                                    'a_inserts',
                                    'a_insert_comments',
                                    'a_insert_comment_slugs'])

    sqltable1 = tables.tables[collection_name]
    create1 = generate_create_table_statement(sqltable1)
    query1 = 'CREATE TABLE a_inserts (body TEXT, created_at TIMESTAMP, id_bsontype INTEGER, id_oid TEXT, title TEXT, updated_at TIMESTAMP, user_id TEXT, idx BIGINT);'
    print create1
    assert(query1==create1)
#test another table
    sqltable2 = tables.tables[collection_name[:-1]+'_comments']
    create2 = generate_create_table_statement(sqltable2)
    query2 = 'CREATE TABLE a_insert_comments (a_inserts_id_oid TEXT, body TEXT, created_at TIMESTAMP, id_bsontype INTEGER, id_oid TEXT, updated_at TIMESTAMP, a_inserts_idx BIGINT, idx BIGINT);'
    print create2
    assert(query2==create2)
#test another table
    sqltable3 = tables.tables[collection_name[:-1]+'_comment_items']
    create3 = generate_create_table_statement(sqltable3)
    query3 = 'CREATE TABLE a_insert_comment_items (a_inserts_comments_id_oid TEXT, a_inserts_id_oid TEXT, data TEXT, a_inserts_idx BIGINT, a_inserts_comments_idx BIGINT, idx BIGINT);'
    print create3
    assert(query3==create3)
#test another table
    sqltable4 = tables.tables[collection_name[:-1]+'_comment_slugs']
    create4 = generate_create_table_statement(sqltable4)
    query4 = 'CREATE TABLE a_insert_comment_slugs (slugs INTEGER, a_inserts_idx BIGINT, a_inserts_comments_idx BIGINT, idx BIGINT);'
    print create4
    assert(query4==create4)
