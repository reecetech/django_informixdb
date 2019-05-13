"""
informix database backend for Django.

Requires informixdb
"""
import logging
import os
import sys
import platform
import time
import random
import re

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.base.validation import BaseDatabaseValidation
from django.core.exceptions import ImproperlyConfigured

from django.utils.six import binary_type, text_type
from django.utils.encoding import smart_str

from .client import DatabaseClient
from .creation import DatabaseCreation
from .introspection import DatabaseIntrospection
from .operations import DatabaseOperations
from .features import DatabaseFeatures
from .schema import DatabaseSchemaEditor

try:
    import pyodbc
except ImportError as e:
    e = sys.exc_info()[1]
    raise ImproperlyConfigured("Error loading pyodbc module:{}".format(e))


logger = logging.getLogger(__name__)


def decoder(value, encodings=('utf-8',)):
    """This decoder tries multiple encodings before giving up"""

    if not isinstance(value, binary_type):
        raise ValueError(f"Not a binary type: {value} {type(value)}")

    for enc in encodings:
        try:
            return value.decode(enc)
        except UnicodeDecodeError:
            pass

    raise UnicodeDecodeError("unable to decode `{value}`")


class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = 'informixdb'
    Database = pyodbc

    DRIVER_MAP = {
        'DARWIN': '/Applications/IBM/informix/lib/cli/iclit09b.dylib',
        'LINUX': '/opt/IBM/informix/lib/cli/iclit09b.so',
        'WINDOWS32bit': 'IBM INFORMIX ODBC DRIVER (32-bit)',
        'WINDOWS64bit': 'IBM INFORMIX ODBC DRIVER (64-bit)',
    }

    ISOLATION_LEVEL = {
        'READ_COMMITED': pyodbc.SQL_TXN_READ_COMMITTED,
        'READ_UNCOMMITTED': pyodbc.SQL_TXN_READ_UNCOMMITTED,  # Dirty Read
        'REPEATABLE_READ': pyodbc.SQL_TXN_REPEATABLE_READ,
        'SERIALIZABLE': pyodbc.SQL_TXN_SERIALIZABLE,
    }

    data_types = {
        'AutoField': 'serial',
        'BigAutoField': 'bigserial',
        'BinaryField': 'blob',
        'BooleanField': 'boolean',
        'CharField': 'lvarchar(%(max_length)s)',
        'CommaSeparatedIntegerField': 'lvarchar(%(max_length)s)',
        'DateField': 'date',
        'DateTimeField': 'datetime year to fraction(5)',
        'DecimalField': 'decimal',
        'DurationField': 'interval',
        'FileField': 'lvarchar(%(max_length)s)',
        'FilePathField': 'lvarchar(%(max_length)s)',
        'FloatField': 'smallfloat',
        'IntegerField': 'integer',
        'BigIntegerField': 'bigint',
        'IPAddressField': 'char(15)',
        'GenericIPAddressField': 'char(39)',
        'NullBooleanField': 'boolean',
        'OneToOneField': 'integer',
        'PositiveIntegerField': 'integer',
        'PositiveSmallIntegerField': 'smallint',
        'SlugField': 'lvarchar(%(max_length)s)',
        'SmallIntegerField': 'smallint',
        'TextField': 'lvarchar(%(max_length)s)',
        'TimeField': 'datetime hour to second',
        'UUIDField': 'char(32)',
    }

    data_type_check_constraints = {
        'PositiveIntegerField': '%(column)s >= 0',
        'PositiveSmallIntegerField': '%(column)s >= 0',
    }

    operators = {
        'exact': '= %s',
        'iexact': "= LOWER(%s)",
        'contains': "LIKE %s ESCAPE '\\'",
        'icontains': "LIKE LOWER(%s) ESCAPE '\\'",
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': "LIKE %s ESCAPE '\\'",
        'endswith': "LIKE %s ESCAPE '\\'",
        'istartswith': "LIKE LOWER(%s) ESCAPE '\\'",
        'iendswith': "LIKE LOWER(%s) ESCAPE '\\'",
        'regex': 'LIKE %s',
        'iregex': 'LIKE %s',
    }

    # The patterns below are used to generate SQL pattern lookup clauses when
    # the right-hand side of the lookup isn't a raw string (it might be an expression
    # or the result of a bilateral transformation).
    # In those cases, special characters for LIKE operators (e.g. \, *, _) should be
    # escaped on database side.
    #
    # Note: we use str.format() here for readability as '%' is used as a wildcard for
    # the LIKE operator.
    pattern_esc = r"REPLACE(REPLACE(REPLACE({}, '\', '\\'), '%%', '\%%'), '_', '\_')"
    pattern_ops = {
        'contains': "LIKE '%%' ESCAPE '\\' || {} || '%%'",
        'icontains': "LIKE '%%' ESCAPE '\\' || UPPER({}) || '%%'",
        'startswith': "LIKE {} ESCAPE '\\' || '%%'",
        'istartswith': "LIKE UPPER({}) ESCAPE '\\' || '%%'",
        'endswith': "LIKE '%%' ESCAPE '\\' || {}",
        'iendswith': "LIKE '%%' ESCAPE '\\' || UPPER({})",
    }
    client_class = DatabaseClient
    creation_class = DatabaseCreation
    features_class = DatabaseFeatures
    introspection_class = DatabaseIntrospection
    ops_class = DatabaseOperations
    SchemaEditorClass = DatabaseSchemaEditor
    validation_class = BaseDatabaseValidation

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        options = self.settings_dict.get('OPTIONS', {})

        self.encodings = options.get('encodings', ('utf-8', 'cp1252', 'iso-8859-1'))
        # make lookup operators to be collation-sensitive if needed
        self.collation = options.get('collation', None)
        if self.collation:
            self.operators = dict(self.__class__.operators)
            ops = {}
            for op in self.operators:
                sql = self.operators[op]
                if sql.startswith('LIKE '):
                    ops[op] = '%s COLLATE %s' % (sql, self.collation)
            self.operators.update(ops)

        self.features = self.features_class(self)
        self.ops = self.ops_class(self)
        self.client = self.client_class(self)
        self.creation = self.creation_class(self)
        self.introspection = self.introspection_class(self)
        self.validation = self.validation_class(self)

    def get_driver_path(self):
        system = platform.system().upper()
        if system == 'WINDOWS':
            system = system + platform.architecture()[0]
        try:
            return self.DRIVER_MAP[system]
        except KeyError:
            raise ImproperlyConfigured('cannot locate informix driver, please specify')

    def get_connection_params(self):
        settings = self.settings_dict

        if 'DSN' not in settings:
            for k in ['NAME', 'SERVER', 'USER', 'PASSWORD']:
                if k not in settings:
                    raise ImproperlyConfigured('{} is a required setting for an informix connection'.format(k))
        conn_params = settings.copy()

        # Ensure the driver is set in the options
        options = conn_params.get('OPTIONS', {})
        if 'DRIVER' not in options or options['DRIVER'] is None:
            options['DRIVER'] = self.get_driver_path()
        if platform.system().upper() != 'WINDOWS':
            sqlhosts = os.environ.get('INFORMIXSQLHOSTS')
            if not sqlhosts or not os.path.exists(sqlhosts):
                raise ImproperlyConfigured('Cannot find Informix sqlhosts at {}'.format(sqlhosts))
            if not os.path.exists(options['DRIVER']):
                raise ImproperlyConfigured('cannot find Informix driver at {}'.format(options['DRIVER']))
        conn_params['OPTIONS'] = options

        conn_params['AUTOCOMMIT'] = False if 'AUTOCOMMIT' not in conn_params else conn_params['AUTOCOMMIT']

        return conn_params

    def get_new_connection(self, conn_params):
        parts = [
            'Driver={{{}}}'.format(conn_params['OPTIONS']['DRIVER']),
        ]

        if 'DSN' in conn_params:
            parts.append('DSN={}'.format(conn_params['DSN']))
        if 'SERVER' in conn_params:
            parts.append('Server={}'.format(conn_params['SERVER']))
        if 'NAME' in conn_params and conn_params['NAME'] is not None:
            parts.append('Database={}'.format(conn_params['NAME']))
        elif conn_params['NAME'] is None:
            parts.append('CONNECTDATABASE=no')
        if 'USER' in conn_params:
            parts.append('Uid={}'.format(conn_params['USER']))
        if 'PASSWORD' in conn_params:
            parts.append('Pwd={}'.format(conn_params['PASSWORD']))
        if 'CPTIMEOUT' in conn_params['OPTIONS']:
            parts.append('CPTimeout={}'.format(conn_params['OPTIONS']['CPTIMEOUT']))

        connection_string = ';'.join(parts)
        logging.debug('Connecting to Informix')
        self.connection = self._get_connection_with_retries(connection_string, conn_params)
        self.connection.setencoding(encoding='UTF-8')

        # This will set database isolation level at connection level
        if 'ISOLATION_LEVEL' in conn_params['OPTIONS']:
            self.connection.set_attr(pyodbc.SQL_ATTR_TXN_ISOLATION,
                                     self.ISOLATION_LEVEL[conn_params['OPTIONS']['ISOLATION_LEVEL']])

        # This will set SQL_C_CHAR, SQL_C_WCHAR and SQL_BINARY to 32000
        # this max length is actually just what the database internally
        # supports. e.g. the biggest `LONGVARCHAR` field in informix is
        # 32000, you would need to split anything bigger over multiple fields
        # This limit will not effect schema defined lengths, which will just
        # truncate values greater than the limit.
        self.connection.maxwrite = 32000

        self.connection.add_output_converter(-101, lambda r: r.decode('utf-8'))  # Constraints
        self.connection.add_output_converter(-391, lambda r: r.decode('utf-16-be'))  # Integrity Error

        self.connection.add_output_converter(pyodbc.SQL_CHAR, self._output_converter)
        self.connection.add_output_converter(pyodbc.SQL_WCHAR, self._output_converter)
        self.connection.add_output_converter(pyodbc.SQL_VARCHAR, self._output_converter)
        self.connection.add_output_converter(pyodbc.SQL_WVARCHAR, self._output_converter)
        self.connection.add_output_converter(pyodbc.SQL_LONGVARCHAR, self._output_converter)
        self.connection.add_output_converter(pyodbc.SQL_WLONGVARCHAR, self._output_converter)

        if 'LOCK_MODE_WAIT' in conn_params['OPTIONS']:
            self.set_lock_mode(wait=conn_params['OPTIONS']['LOCK_MODE_WAIT'])

        return self.connection

    def _get_connection_with_retries(self, connection_string, conn_params):
        """
        Attempt to open a connection, retrying on failure with an exponential backoff.
        """
        retry_params = conn_params.get("CONNECTION_RETRY", {})
        max_attempts = retry_params.get("MAX_ATTEMPTS", 1)
        wait_min = retry_params.get("WAIT_MIN", 0)
        wait_max = retry_params.get("WAIT_MAX", 1000)
        multiplier = retry_params.get("WAIT_MULTIPLIER", 25)
        exp_base = retry_params.get("WAIT_EXP_BASE", 2)
        errors_to_retry = retry_params.get("ERRORS", ["-908", "-27001"])
        retryable = re.compile(r"\((" + "|".join(errors_to_retry) + r")\)")

        attempt = 0
        while True:
            attempt += 1
            try:
                conn = pyodbc.connect(connection_string, autocommit=conn_params["AUTOCOMMIT"])
            except pyodbc.Error as err:
                if attempt < max_attempts and retryable.search(err.args[1]):
                    wait = random.uniform(
                        wait_min,
                        max(wait_min, min(wait_max, multiplier * exp_base ** (attempt - 1))),
                    )
                    logger.info(
                        f'failed to connect to db on attempt {attempt}: "{err}"; '
                        f"waiting {wait:.1f} ms before trying again"
                    )
                    time.sleep(wait / 1000)
                    continue
                else:
                    raise
            else:
                return conn

    def _unescape(self, raw):
        """
        For some reason the Informix ODBC driver seems to double escape new line characters.

        This little handler converts them back.

        @todo: See if this applies to other escape characters
        """
        return raw.replace(b'\\n', b'\n')

    def _output_converter(self, raw):
        return decoder(self._unescape(raw), self.encodings)

    def init_connection_state(self):
        pass

    def create_cursor(self, name=None):
        logging.debug('Creating Informix cursor')
        return CursorWrapper(self.connection.cursor(), self)

    def _set_autocommit(self, autocommit):
        with self.wrap_database_errors:
            self.connection.autocommit = autocommit

    def check_constraints(self, table_names=None):
        """
        To check constraints, we set constraints to immediate. Then, when, we're done we must ensure they
        are returned to deferred.
        """
        self.cursor().execute('SET CONSTRAINTS ALL IMMEDIATE')
        self.cursor().execute('SET CONSTRAINTS ALL DEFERRED')

    def _start_transaction_under_autocommit(self):
        """
        Start a transaction explicitly in autocommit mode.
        """
        start_sql = self.ops.start_transaction_sql()
        self.cursor().execute(start_sql)

    def is_usable(self):
        try:
            # Use a cursor directly, bypassing Django's utilities.
            self.connection.cursor().execute("SELECT 1")
        except pyodbc.Error:
            return False
        else:
            return True

    def read_dirty(self):
        self.cursor().execute('set isolation to dirty read;')

    def read_committed(self):
        self.cursor().execute('set isolation to committed read;')

    def read_repeatable(self):
        self.cursor().execute('set isolation to repeatable read;')

    def read_committed_with_update_locks(self):
        self.cursor().execute('set isolation to committed read retain update locks;')

    def set_lock_mode(self, wait=None):
        """
        This will set database LOCK MODE WAIT at connection level
        Application can use this property to override the default server
        process for accessing a locked row or table.
        The default value is 0 (do not wait for the lock).
        Possible values:
           -1 - WAIT until the lock is released.
           0 - DO NOT WAIT, end the operation, and return with error.
           nn - WAIT for nn seconds for the lock to be released.
        """
        if wait == 0:
            sql = 'SET LOCK MODE TO NOT WAIT'
        elif wait == -1:
            sql = 'SET LOCK MODE TO WAIT'
        else:
            sql = 'SET LOCK MODE TO WAIT {}'.format(wait)

        self.cursor().execute(sql)

    def _commit(self):
        if self.connection is not None:
            with self.wrap_database_errors:
                return self.cursor().execute("COMMIT WORK")

    def _rollback(self):
        if self.connection is not None:
            with self.wrap_database_errors:
                return self.cursor().execute("ROLLBACK WORK")


class CursorWrapper(object):
    """
    A wrapper around the pyodbc's cursor that takes in account a) some pyodbc
    DB-API 2.0 implementation and b) some common ODBC driver particularities.
    """
    def __init__(self, cursor, connection):
        self.active = True
        self.cursor = cursor
        self.connection = connection
        self.driver_charset = False  # connection.driver_charset
        self.last_sql = ''
        self.last_params = ()

    def close(self):
        if self.active:
            self.active = False
            self.cursor.close()

    def format_sql(self, sql, params):
        if isinstance(sql, text_type):
            # FreeTDS (and other ODBC drivers?) doesn't support Unicode
            # yet, so we need to encode the SQL clause itself in utf-8
            sql = smart_str(sql, self.driver_charset)

        # pyodbc uses '?' instead of '%s' as parameter placeholder.
        if params is not None:
            pass
            # sql = sql % tuple('?' * len(params))

        return sql

    def format_params(self, params):
        fp = []
        if params is not None:
            for p in params:
                if isinstance(p, text_type):
                    if self.driver_charset:
                        # FreeTDS (and other ODBC drivers?) doesn't support Unicode
                        # yet, so we need to encode parameters in utf-8
                        fp.append(smart_str(p, self.driver_charset))
                    else:
                        fp.append(p)

                elif isinstance(p, binary_type):
                    fp.append(p)

                elif isinstance(p, type(True)):
                    if p:
                        fp.append(1)
                    else:
                        fp.append(0)

                else:
                    fp.append(p)

        return tuple(fp)

    def execute(self, sql, params=None):
        self.last_sql = sql
        sql = self.format_sql(sql, params)
        params = self.format_params(params)
        self.last_params = params
        return self.cursor.execute(sql, params)

    def executemany(self, sql, params_list=()):
        if not params_list:
            return None
        raw_pll = [p for p in params_list]
        sql = self.format_sql(sql, raw_pll[0])
        params_list = [self.format_params(p) for p in raw_pll]
        return self.cursor.executemany(sql, params_list)

    def format_rows(self, rows):
        return list(map(self.format_row, rows))

    def format_row(self, row):
        """
        Decode data coming from the database if needed and convert rows to tuples
        (pyodbc Rows are not sliceable).
        """
        if self.driver_charset:
            for i in range(len(row)):
                f = row[i]
                # FreeTDS (and other ODBC drivers?) doesn't support Unicode
                # yet, so we need to decode utf-8 data coming from the DB
                if isinstance(f, binary_type):
                    row[i] = f.decode(self.driver_charset)
        return tuple(row)

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is not None:
            row = self.format_row(row)
        # Any remaining rows in the current set must be discarded
        # before changing autocommit mode when you use FreeTDS
        self.cursor.nextset()
        return row

    def fetchmany(self, chunk):
        return self.format_rows(self.cursor.fetchmany(chunk))

    def fetchall(self):
        return self.format_rows(self.cursor.fetchall())

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        return getattr(self.cursor, attr)

    def __iter__(self):
        return iter(self.cursor)
