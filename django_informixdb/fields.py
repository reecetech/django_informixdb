from django.db import models
from django.core.exceptions import ValidationError


class TrimCharField(models.CharField):
    description = "CharField that ignores trailing spaces in data"

    def from_db_value(self, value, expression, connection, *ignore):
        if value:
            return value.rstrip()
        return value


class CharToBooleanField(models.CharField):
    def __init__(self, *args, null=True, **kwargs):
        kwargs['max_length'] = 1

        super().__init__(*args, null=null, **kwargs)

    def from_db_value(self, value, expression, connection, *ignore):
        if self.null and value is None:
            return None

        return value == 'Y'

    def get_db_prep_value(self, value, connection, prepared=False):
        if value is True:
            return 'Y'
        elif value is False:
            return 'N'

        elif value is None and self.null:
            return None

        # - Not sure if this is the right place/thing to do here
        raise ValidationError(
            self.error_messages['invalid_nullable' if self.null else 'null'],
            code='invalid',
            params={'value': value},
        )

    def to_python(self, value):
        return value

    def get_prep_value(self, value):
        return value
