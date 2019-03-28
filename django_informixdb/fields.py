from django.db import models
from django.core.exceptions import ValidationError


class TrimCharField(models.CharField):
    description = "CharField that ignores trailing spaces in data"

    def from_db_value(self, value, expression, connection, *ignore):
        if value:
            return value.rstrip()
        return value


class CharToBooleanField(models.CharField):
    """Copied most of this code from the Django BooleanField object:
    https://docs.djangoproject.com/en/2.1/_modules/django/db/models/fields/#BooleanField
    """
    description = "CharField that hides the Y/N implementation and converts to Booleans"

    def __init__(self, *args, null=True, **kwargs):
        kwargs['max_length'] = 1

        super().__init__(*args, null=null, **kwargs)

    def to_python(self, value):
        if self.null and value in self.empty_values:
            return None
        if value in (True, False):
            # 1/0 are equal to True/False. bool() converts former to latter.
            return bool(value)
        if value in ('t', 'True', '1', 'Y'):
            return True
        if value in ('f', 'False', '0', 'N'):
            return False

        raise ValidationError(
            self.error_messages['invalid_nullable' if self.null else 'invalid'],
            code='invalid',
            params={'value': value},
        )

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return None
        return self.to_python(value)

    def from_db_value(self, value, expression, connection, *ignore):
        return self.to_python(value)

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
