from django.db import models


class Donut(models.Model):
    name = models.CharField(max_length=100)
    is_frosted = models.BooleanField(default=False)
    cost = models.DecimalField(decimal_places=2, max_digits=10, default=0)
