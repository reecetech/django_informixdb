from django.db.backends.base.introspection import BaseDatabaseIntrospection, FieldInfo, TableInfo

from .datatypes import InformixTypes
from .tableignore import EXCLUDED_TABLES


class DatabaseIntrospection(BaseDatabaseIntrospection):
    # Map type codes to Django Field types.
    data_types_reverse = InformixTypes.field_map()

    def get_table_list(self, cursor):
        cursor.execute('SELECT tabname, tabtype FROM systables')
        # We want to ignore all the internal 'sys' tables in the exclude list
        return [
            TableInfo(x[0], x[1].lower()) for x in cursor.fetchall()
            if x[0] not in EXCLUDED_TABLES
        ]

    def get_table_description(self, cursor, table_name):
        "Returns a description of the table, with the DB-API cursor.description interface."
        query_format = """
            SELECT c.*
            FROM syscolumns c
            JOIN systables t
            ON c.tabid=t.tabid
            WHERE t.tabname='{}'
        """

        cursor.execute(query_format.format(table_name))
        columns = [[c[0], c[3] % 256, None, c[4], c[4], None, 0 if c[3] > 256 else 1, None]
                   for c in cursor.fetchall()]
        items = []
        for column in columns:
            if column[1] in (InformixTypes.SQL_TYPE_NUMERIC.num, InformixTypes.SQL_TYPE_DECIMAL.num):
                column[4] = int(column[3] / 256)
                column[5] = column[3] - column[4] * 256
            # FieldInfo:
            #   name, type_code, display_size, internal_size, precision, scale, null_ok, default
            items.append(FieldInfo(*column))

        return items

    def get_key_columns(self, cursor, table_name):
        key_columns_query = """
            SELECT col1.colname AS column_name,
                   t2.tabname AS referenced_table_name,
                   col2.colname AS referenced_column
            FROM systables t1
            JOIN syscolumns col1 ON t1.tabid = col1.tabid
            JOIN sysindexes idx1 ON idx1.tabid=t1.tabid AND col1.colno = idx1.part1
            JOIN sysconstraints const1 ON idx1.idxname = const1.idxname AND const1.tabid = t1.tabid
            JOIN sysreferences  ref ON ref.constrid = const1.constrid
            JOIN sysconstraints const2 ON ref.primary = const2.constrid
            JOIN sysindexes idx2 ON idx2.idxname = const2.idxname
            JOIN syscolumns col2 ON col2.colno = idx2.part1 AND col2.tabid = idx2.tabid
            JOIN systables t2 ON t2.tabid = idx2.tabid
            WHERE const1.constrtype='R' AND t1.tabname ='{}'
        """
        cursor.execute(key_columns_query.format(table_name))
        return cursor.fetchall()

    def get_indexes(self, cursor, table_name):
        """ This query retrieves each index ON the given table, including the
            first associated field name """
        index_query = """
            SELECT
                sc.colname, idx.idxtype, scs.constrtype
            FROM systables st JOIN sysindexes idx  ON st.tabid = idx.tabid
            JOIN syscolumns sc ON idx.part1=sc.colno AND sc.tabid = st.tabid
            LEFT JOIN sysconstraints scs ON idx.idxname = scs.idxname
            WHERE st.tabname='{}' AND idx.part2 = 0
        """
        cursor.execute(index_query.format(table_name))
        indexes = {}
        for row in cursor.fetchall():
            indexes[row[0]] = {
                'primary_key': True if row[2] == 'P' else False,
                'unique': True if row[1] == 'U' else False
            }
        return indexes

    def _get_col_index(self, cursor, table_name):
        """Private method. Getting Index position of column by its name"""
        col_query = """
            SELECT colno, colname FROM syscolumns sc
            JOIN systables st ON sc.tabid=st.tabid
            WHERE st.tabname='{}'
        """
        cursor.execute(col_query.format(table_name))
        return {row[1]: int(row[0]) - 1 for row in cursor.fetchall()}

    def get_relations(self, cursor, table_name):
        """
        Returns a dictionary of {field_index: (field_index_other_table, other_table)}
        representing all relationships to the given table. Indexes are 0-based.
        """
        relations = {}
        key_columns = self.get_key_columns(cursor, table_name)
        for rel in key_columns:
            row0 = self._get_col_index(cursor, table_name)[rel[0]]
            row1 = self._get_col_index(cursor, rel[1])[rel[2]]
            row2 = rel[1]
            relations[row0] = (row1, row2)
        return relations

    def get_constraints(self, cursor, table_name):
        constraints = {}
        index_query = """
            SELECT idxname, idxtype, indexkeys
            FROM sysindices idx
            JOIN systables st ON idx.tabid = st.tabid
            WHERE st.tabname = '{}'
        """

        # reverse name, AND index here
        all_columns = {v: k for k, v in self._get_col_index(cursor, table_name).items()}
        cursor.execute(index_query.format(table_name))
        for name, idx_type, keys in cursor.fetchall():
            # keys are in the format like "1 [1], 4 [1], 7 [1]",
            # which means including column #1, #4, AND #7
            columns = [all_columns[int(k.strip().split()[0]) - 1] for k in keys.split(',')]
            constraints[name] = {
                'columns': columns,
                'primary_key': len(columns) == 1 and idx_type == 'U',
                'unique': idx_type == 'U',
                'foreign_key': None,
                'check': True,
                'index': idx_type == 'D'
            }
        return constraints
