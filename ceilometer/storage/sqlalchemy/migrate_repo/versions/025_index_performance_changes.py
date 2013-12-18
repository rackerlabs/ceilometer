# -*- encoding: utf-8 -*-
#
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from migrate import ForeignKeyConstraint
from sqlalchemy import Index, MetaData, Table


INDEXES_TO_DELETE = {
    #`table_name`: ((`index_name`, `column`),)
    "trait": (('ix_trait_t_int', 't_int'),
              ('ix_trait_t_string', 't_string'),
              ('ix_trait_t_datetime', 't_datetime'),
              ('ix_trait_t_float', 't_float'),),
}

INDEXES_TO_CREATE = {
    #`table_name`: ((`index_name`, `column`, {additional_argunments}),)
    "trait": (('ix_trait_trait_type', 'trait_type_id', {}),
              ('ix_trait_event', 'event_id', {})),
    "trait_type": (('ix_trait_type_desc', 'desc', {"mysql_limit": 32}),
                   ('ix_trait_type_data_type', 'data_type', {})),
    "event_type": (('ix_event_type_desc', 'desc', {"mysql_limit": 32}),),
}

FOREIGN_KEYS_TO_DROP = {
    "trait": (('trait_type_id', 'trait_type', 'id'),
              ('event_id', 'event', 'id')),
    "event": (('event_type_id', 'event_type', 'id'),)
}

TABLES = set(INDEXES_TO_CREATE.keys())\
    .union(set(INDEXES_TO_DELETE.keys()))\
    .union(set(FOREIGN_KEYS_TO_DROP.keys()))


def upgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)
    load_tables = dict((table_name, Table(table_name, meta, autoload=True))
                       for table_name in TABLES)

    for table_name, fk in FOREIGN_KEYS_TO_DROP.items():
        for col, ref, ref_col in fk:
            fk_table = load_tables[table_name]
            ref_table = load_tables[ref]
            params = {'columns': [fk_table.c[col]],
                      'refcolumns': [ref_table.c[ref_col]]}
            if migrate_engine.name == 'mysql':
                params['name'] = "trait_ibfk_2" if (table_name, col) == \
                    ('trait', 'event_id') else "fk_%s" % col
            ForeignKeyConstraint(**params).drop()

    for table_name, indexes in INDEXES_TO_DELETE.items():
        table = load_tables[table_name]
        for index_name, column in list(indexes):
            index = Index(index_name, table.c[column])
            index.drop()

    for table_name, indexes in INDEXES_TO_CREATE.items():
        table = load_tables[table_name]
        for index_name, column, args in indexes:
            index = Index(index_name, table.c[column], **args)
            index.create()


def downgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)
    load_tables = dict((table_name, Table(table_name, meta, autoload=True))
                       for table_name in TABLES)

    for table_name, indexes in INDEXES_TO_DELETE.items():
        table = load_tables[table_name]
        for index_name, column in indexes:
            index = Index(index_name, table.c[column])
            index.create()

    for table_name, indexes in INDEXES_TO_CREATE.items():
        table = load_tables[table_name]
        for index_name, column, _ in indexes:
            index = Index(index_name, table.c[column])
            index.drop()

    for table_name, fk in FOREIGN_KEYS_TO_DROP.items():
        for col, ref, ref_col in fk:
            fk_table = load_tables[table_name]
            ref_table = load_tables[ref]
            params = {'columns': [getattr(fk_table.c, col)],
                      'refcolumns': [getattr(ref_table.c, ref_col)]}
            if migrate_engine.name == 'mysql':
                params['name'] = "trait_ibfk_2" if (table_name, col) == \
                    ('trait', 'event_id') else "fk_%s" % col
            ForeignKeyConstraint(**params).create()
