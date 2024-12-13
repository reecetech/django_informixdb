from django.db.backends.base.creation import BaseDatabaseCreation
from django.db.utils import Error


class DatabaseCreation(BaseDatabaseCreation):

    def sql_table_creation_suffix(self):
        test_settings = self.connection.settings_dict['TEST']
        assert test_settings['COLLATION'] is None, (
            "Informix does not support collation setting at database creation time."
        )
        if test_settings['CHARSET']:
            return "WITH ENCODING '%s'" % test_settings['CHARSET']
        return 'WITH BUFFERED LOG'

    def create_test_db(self, verbosity=1, autoclobber=False, serialize=True, keepdb=False):
        """
        Forcing autoclobber because destroying test DB doesn't work

        The keepdb option still works
        """
        if self.connection.settings_dict.get('TEST', {}).get('CREATE_DB', True):
            super().create_test_db(verbosity, True, serialize, keepdb)

    def _destroy_test_db(self, test_database_name, verbosity):
        if self.connection.settings_dict.get('TEST', {}).get('CREATE_DB', True):
            try:
                super()._destroy_test_db(test_database_name, verbosity)
            except Error as e:
                print(f"Unable to destroy test database: {e.args[1]}")
