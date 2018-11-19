from django.db import models


class TrimCharField(models.CharField):
    description = "CharField that ignores trailing spaces in data"

    def from_db_value(self, value, expression, connection, *ignore):
        if value:
            return value.rstrip()
        return value
