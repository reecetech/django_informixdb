from decimal import Decimal

from django.test import TestCase
from django.core.exceptions import ValidationError

from .models import Donut


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
