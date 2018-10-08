from django.db import models

from django_informixdb.fields import TrimCharField


class Donut(models.Model):
    name = models.CharField(max_length=100)
    trim_name = TrimCharField(max_length=100)
    is_frosted = models.BooleanField(default=False)
    cost = models.DecimalField(decimal_places=2, max_digits=10, default=0)
