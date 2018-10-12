from decimal import Decimal

from django.test import TestCase

from django_informixdb.fields import TrimCharField
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
