from django.test import TestCase

from test.datatypes.models import Donut


class CompilerCase(TestCase):
    def test_not_exists(self):
        d = Donut(name='Apple Fritter')
        d.save()
        exists = Donut.objects.filter(name="test").exists()
        self.assertFalse(exists)
        exists = Donut.objects.filter(name="Apple Fritter").exists()
        self.assertTrue(exists)



