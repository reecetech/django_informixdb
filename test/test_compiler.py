from django.test import TestCase

from test.datatypes.models import Donut


class CompilerCase(TestCase):
    def test_exists_returns_True_if_exists(self):
        d = Donut(name='Apple Fritter')
        d.save()
        exists = Donut.objects.filter(name="Apple Fritter").exists()
        self.assertTrue(exists)

    def test_exists_returns_False_if_not_exists(self):
        exists = Donut.objects.filter(name="test").exists()
        self.assertFalse(exists)
