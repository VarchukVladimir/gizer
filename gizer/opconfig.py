#!/usr/bin/env python

__author__ = "Yaroslav Litvinov"
__copyright__ = "Copyright 2016, Rackspace Inc."
__email__ = "yaroslav.litvinov@rackspace.com"

from collections import namedtuple

MongoSettings = namedtuple('MongoSettings',
                           ['ssl', 'host', 'port', 'dbname',
                            'user', 'passw'])
PsqlSettings = namedtuple('PsqlSettings',
                          ['host', 'port', 'dbname',
                           'user', 'passw', 
                           'schema', 'operational_schema'])

class SectionKey:
    def __init__(self, section_name):
        self.section_name = section_name
    def key(self, base_key_name):
        return "%s-%s" % (self.section_name, base_key_name)


def mongo_settings_from_config(config, section_name):
    mongo = SectionKey(section_name)
    conf = config[section_name]
    return MongoSettings(ssl=conf[mongo.key('ssl')],
                         host=conf[mongo.key('host')],
                         port=conf[mongo.key('port')],
                         dbname=conf[mongo.key('dbname')],
                         user=conf[mongo.key('user')],
                         passw=conf[mongo.key('pass')])

def psql_settings_from_config(config, section_name):
    psql = SectionKey(section_name)
    conf = config[section_name]
    return PsqlSettings(host=conf[psql.key('host')],
                        port=conf[psql.key('port')],
                        dbname=conf[psql.key('dbname')],
                        user=conf[psql.key('user')],
                        passw=conf[psql.key('pass')],
                        schema=conf[psql.key('schema-name')],
                        operational_schema\
                        =conf[psql.key('operational-schema-name')])


