from django.db.backends.base.features import BaseDatabaseFeatures
from django.db.utils import InterfaceError


class DatabaseFeatures(BaseDatabaseFeatures):
    has_bulk_insert = False
    can_use_chunked_reads = True
    supports_microsecond_precision = False
    supports_regex_backreferencing = False
    supports_subqueries_in_group_by = False
    supports_transactions = True
    can_rollback_ddl = True
    uses_savepoints = True
    can_release_savepoints = True
    autocommits_when_autocommit_is_off = False
    supports_timezones = False
    supports_sequence_reset = False
    supports_tablespaces = True
    can_introspect_autofield = True
    has_select_for_update = True
    supports_select_for_update_with_limit = True
    closed_cursor_error_class = InterfaceError
