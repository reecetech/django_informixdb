from decimal import Decimal
from collections import namedtuple

import pytest
from django.test import TestCase
from django.db import connection, transaction
from django.core.exceptions import ValidationError

from .models import Donut


RawDonutResult = namedtuple('RawDonut', [
    'id', 'name', 'trim_name', 'is_frosted', 'is_fresh', 'is_only_fresh', 'cost'
])


class DataTypesTestCase(TestCase):
    def test_boolean_false(self):
        d = Donut(name='Apple Fritter')
        self.assertFalse(d.is_frosted)
        d.save()
        d2 = Donut.objects.get(name='Apple Fritter')
        self.assertFalse(d2.is_frosted)

    def test_boolean_true(self):
        d = Donut(name='Apple Fritter', is_frosted=True)
        self.assertTrue(d.is_frosted)
        d.save()
        d2 = Donut.objects.get(name='Apple Fritter')
        self.assertTrue(d2.is_frosted)

    def test_decimal(self):
        d = Donut(name='Apple Fritter', cost=1)
        self.assertEqual(d.cost, 1)
        d.save()
        d2 = Donut.objects.get(name='Apple Fritter')
        self.assertEqual(d2.cost, Decimal(1))

    def test_decimal_precision(self):
        d = Donut(name='Apple Fritter', cost=1.23)
        self.assertEqual(d.cost, 1.23)
        d.save()
        d2 = Donut.objects.get(name='Apple Fritter')
        self.assertEqual(d2.cost, Decimal('1.23'))

    def test_characters(self):
        d = Donut(name='Apple Fritter ')
        self.assertEqual(d.name, 'Apple Fritter ')
        d.save()
        d2 = Donut.objects.get(name='Apple Fritter ')
        self.assertEqual(d2.name, 'Apple Fritter ')

    def test_trim_characters(self):
        d = Donut(trim_name='abc ')
        self.assertEqual(d.trim_name, 'abc ')
        d.save()
        d2 = Donut.objects.get(trim_name='abc')
        self.assertEqual(d2.trim_name, 'abc')

    def test_char_to_boolean_True(self):
        d = Donut(is_fresh=True)
        self.assertEqual(d.is_fresh, True)
        d.save()
        d2 = Donut.objects.get(is_fresh=True)
        self.assertEqual(d2.is_fresh, True)

    def test_char_to_boolean_False(self):
        d = Donut(is_fresh=False)
        self.assertEqual(d.is_fresh, False)
        d.save()
        d2 = Donut.objects.get(is_fresh=False)
        self.assertEqual(d2.is_fresh, False)

    def test_char_to_boolean_None(self):
        d = Donut(is_fresh=None)
        self.assertEqual(d.is_fresh, None)
        d.save()
        d2 = Donut.objects.get(is_fresh=None)
        self.assertEqual(d2.is_fresh, None)

    def test_char_to_boolean_default_value(self):
        d = Donut()
        self.assertEqual(d.is_fresh, False)
        d.save()
        d2 = Donut.objects.get(is_fresh=False)
        self.assertEqual(d2.is_fresh, False)

    def test_char_to_boolean_not_null(self):
        d = Donut(is_only_fresh=None)
        self.assertRaises(ValidationError, d.save)


@pytest.mark.django_db(transaction=True)
class TestDataTypesCharToBooleanRawSQL():
    def _get_raw_donut(self):
        raw_donut = None

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(f'select * from datatypes_donut')
                donut = cursor.fetchone()
                raw_donut = RawDonutResult(*donut)

        return raw_donut

    def test_char_to_boolean_check_empty_db_value(self):
        d = Donut()
        d.save()
        raw_donut = self._get_raw_donut()

        assert raw_donut.is_fresh == 'N'
        assert raw_donut.is_only_fresh == 'N'

    @pytest.mark.parametrize('model_value, raw_value', [
        (True, 'Y'),
        (False, 'N'),
    ])
    def test_char_to_boolean_check_db_values(self, model_value, raw_value):
        d = Donut(is_fresh=model_value, is_only_fresh=model_value)
        d.save()
        raw_donut = self._get_raw_donut()

        assert raw_donut.is_fresh == raw_value
        assert raw_donut.is_only_fresh == raw_value
