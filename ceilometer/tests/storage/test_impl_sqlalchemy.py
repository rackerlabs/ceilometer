# -*- encoding: utf-8 -*-
#
# Author: John Tran <jhtran@att.com>
#         Julien Danjou <julien@danjou.info>
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
"""Tests for ceilometer/storage/impl_sqlalchemy.py

.. note::
  In order to run the tests against real SQL server set the environment
  variable CEILOMETER_TEST_SQL_URL to point to a SQL server before running
  the tests.

"""

import datetime
import repr

from mock import MagicMock
from mock import patch

from ceilometer.storage import impl_sqlalchemy
from ceilometer.storage import models
from ceilometer.storage.sqlalchemy import models as sql_models
from ceilometer.tests import db as tests_db
from ceilometer import utils


class SimpleTestBase(tests_db.TestBase):
    # Note: Do not derive from SQLAlchemyEngineTestBase, since we
    # don't want to automatically inherit all the Meter setup.
    database_connection = 'sqlite://'


class CeilometerBaseTest(SimpleTestBase):
    def test_ceilometer_base(self):
        base = sql_models.CeilometerBase()
        base['key'] = 'value'
        self.assertEqual(base['key'], 'value')


class TraitTypeTest(SimpleTestBase):
    # TraitType is a construct specific to sqlalchemy.
    # Not applicable to other drivers.

    def test_trait_type_exists(self):
        tt1 = self.conn._get_or_create_trait_type("foo", 0)
        self.assertTrue(tt1.id >= 0)
        tt2 = self.conn._get_or_create_trait_type("foo", 0)
        self.assertEqual(tt1.id, tt2.id)
        self.assertEqual(tt1.desc, tt2.desc)
        self.assertEqual(tt1.data_type, tt2.data_type)

    def test_new_trait_type(self):
        tt1 = self.conn._get_or_create_trait_type("foo", 0)
        self.assertTrue(tt1.id >= 0)
        tt2 = self.conn._get_or_create_trait_type("blah", 0)
        self.assertNotEqual(tt1.id, tt2.id)
        self.assertNotEqual(tt1.desc, tt2.desc)
        # Test the method __repr__ returns a string
        self.assertTrue(repr.repr(tt2))

    def test_trait_different_data_type(self):
        tt1 = self.conn._get_or_create_trait_type("foo", 0)
        self.assertTrue(tt1.id >= 0)
        tt2 = self.conn._get_or_create_trait_type("foo", 1)
        self.assertNotEqual(tt1.id, tt2.id)
        self.assertEqual(tt1.desc, tt2.desc)
        self.assertNotEqual(tt1.data_type, tt2.data_type)
        # Test the method __repr__ returns a string
        self.assertTrue(repr.repr(tt2))


class EventTypeTest(SimpleTestBase):
    # EventType is a construct specific to sqlalchemy
    # Not applicable to other drivers.

    def test_event_type_exists(self):
        et1 = self.conn._get_or_create_event_type("foo")
        self.assertTrue(et1.id >= 0)
        et2 = self.conn._get_or_create_event_type("foo")
        self.assertEqual(et1.id, et2.id)
        self.assertEqual(et1.desc, et2.desc)

    def test_event_type_unique(self):
        et1 = self.conn._get_or_create_event_type("foo")
        self.assertTrue(et1.id >= 0)
        et2 = self.conn._get_or_create_event_type("blah")
        self.assertNotEqual(et1.id, et2.id)
        self.assertNotEqual(et1.desc, et2.desc)
        # Test the method __repr__ returns a string
        self.assertTrue(repr.repr(et2))


class MyException(Exception):
    pass


class EventTest(SimpleTestBase):
    def test_string_traits(self):
        model = models.Trait("Foo", models.Trait.TEXT_TYPE, "my_text")
        event = MagicMock()
        event.id = 1
        trait = self.conn._make_trait(model, event)
        self.assertEqual(trait['trait_type'], models.Trait.TEXT_TYPE)
        self.assertIsNone(trait['t_float'])
        self.assertIsNone(trait['t_int'])
        self.assertIsNone(trait['t_datetime'])
        self.assertEqual(trait['t_string'], "my_text")
        self.assertIsNotNone(trait['trait_type_id'])

    def test_int_traits(self):
        model = models.Trait("Foo", models.Trait.INT_TYPE, 100)
        event = MagicMock()
        event.id = 1
        trait = self.conn._make_trait(model, event)
        self.assertEqual(trait['trait_type'], models.Trait.INT_TYPE)
        self.assertIsNone(trait['t_float'])
        self.assertIsNone(trait['t_string'])
        self.assertIsNone(trait['t_datetime'])
        self.assertEqual(trait['t_int'], 100)
        self.assertIsNotNone(trait['trait_type_id'])

    def test_float_traits(self):
        model = models.Trait("Foo", models.Trait.FLOAT_TYPE, 123.456)
        event = MagicMock()
        event.id = 1
        trait = self.conn._make_trait(model, event)
        self.assertEqual(trait['trait_type'], models.Trait.FLOAT_TYPE)
        self.assertIsNone(trait['t_int'])
        self.assertIsNone(trait['t_string'])
        self.assertIsNone(trait['t_datetime'])
        self.assertEqual(trait['t_float'], 123.456)
        self.assertIsNotNone(trait['trait_type_id'])

    def test_datetime_traits(self):
        now = datetime.datetime.utcnow()
        model = models.Trait("Foo", models.Trait.DATETIME_TYPE, now)
        event = MagicMock()
        event.id = 1
        trait = self.conn._make_trait(model, event)
        self.assertEqual(trait['trait_type'], models.Trait.DATETIME_TYPE)
        self.assertIsNone(trait['t_float'])
        self.assertIsNone(trait['t_string'])
        self.assertIsNone(trait['t_int'])
        self.assertEqual(trait['t_datetime'], utils.dt_to_decimal(now))
        self.assertIsNotNone(trait['trait_type_id'])

    def test_bad_event(self):
        now = datetime.datetime.utcnow()
        m = [models.Event("1", "Foo", now, []),
             models.Event("2", "Zoo", now, [])]

        with patch.object(self.conn, "_record_event") as mock_save:
            mock_save.side_effect = MyException("Boom")
            problem_events = self.conn.record_events(m)
        self.assertEqual(2, len(problem_events))
        for bad, event in problem_events:
            self.assertEqual(models.Event.UNKNOWN_PROBLEM, bad)

    def test_get_none_value_traits(self):
        model = sql_models.Trait(None, None, 5)
        self.assertIsNone(model.get_value())
        self.assertTrue(repr.repr(model))

    def test_event_repr(self):
        ev = sql_models.Event('msg_id', None, False)
        ev.id = 100
        self.assertTrue(repr.repr(ev))


class ModelTest(tests_db.TestBase):
    database_connection = 'mysql://localhost'

    def test_model_table_args(self):
        self.assertIsNotNone(sql_models.table_args())


class LRUCacheTest(SimpleTestBase):
    def test_max_size(self):
        cache = impl_sqlalchemy.LRUCache(max_size=5)
        for i in range(0, 10):
            cache.set('key%s' % i, i)
        self.assertEqual(5, len(cache))

    def test_drops_least_recently_added(self):
        cache = impl_sqlalchemy.LRUCache(max_size=5)
        for i in range(0, 6):
            cache.set('key%s' % i, i)

        self.assertFalse('key0' in cache)
        for i in range(1, 6):
            key = 'key%s' % i
            self.assertTrue(key in cache)
            self.assertEqual(i, cache.get(key))

    def test_drops_least_recently_used(self):
        cache = impl_sqlalchemy.LRUCache(max_size=5)
        for i in range(0, 5):
            cache.set('key%s' % i, i)

        cache.get('key4')
        cache.get('key2')
        cache.get('key0')
        cache.get('key3')
        cache.get('key1')
        cache.set('newkey', 6)
        self.assertFalse('key4' in cache)
        self.assertTrue('newkey' in cache)
        self.assertEqual(6, cache.get('newkey'))
