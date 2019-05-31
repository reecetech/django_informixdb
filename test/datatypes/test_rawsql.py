from decimal import Decimal

from django.test import TestCase

from .models import Donut


def test_cursor_select(db):
    Donut(name='Apple Fritter').save()

    with connection.cursor() as cursor:
        cursor.execute("select * from donut")
        desc = cursor.description
        nt_result = namedtuple("Result", [col[0] for col in desc])
        r = [nt_result(*row) for row in cursor.fetchall()]

    assert r.name == 'Apple Fritter'
