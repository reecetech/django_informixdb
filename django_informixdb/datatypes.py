from enum import Enum
"""
    0 = CHAR
    1 = SMALLINT
    2 = INTEGER
    3 = FLOAT
    4 = SMALLFLOAT
    5 = DECIMAL
    6 = SERIAL 1
    7 = DATE
    8 = MONEY
    9 = NULL
    10 = DATETIME
    11 = BYTE
    12 = TEXT
    13 = VARCHAR
    14 = INTERVAL
    15 = NCHAR
    16 = NVARCHAR
    17 = INT8
    18 = SERIAL8 1
    19 = SET
    20 = MULTISET
    21 = LIST
    22 = ROW (unnamed)
    23 = COLLECTION
    40 = LVARCHAR fixed-length opaque types 2
    41 = BLOB, BOOLEAN, CLOB variable-length opaque types 2
    43 = LVARCHAR (client-side only)
    45 = BOOLEAN
    52 = BIGINT
    53 = BIGSERIAL 1
    2061 = IDSSECURITYLABEL 2, 3
    4118 = ROW (named)
"""

class InformixTypes(Enum):
    SQL_TYPE_CHAR = 0, 'CharField'
    SQL_TYPE_SMALLINT = 1, 'SmallIntegerField'
    SQL_TYPE_INTEGER = 2, 'IntegerField'
    SQL_TYPE_FLOAT = 3, 'FloatField'
    SQL_TYPE_DOUBLE = 3, 'FloatField'
    SQL_TYPE_REAL = 4, 'FloatField'
    SQL_TYPE_SMFLOAT = 4, 'FloatField'
    SQL_TYPE_DECIMAL = 5, 'DecimalField'
    SQL_TYPE_NUMERIC = 5, 'DecimalField'
    SQL_TYPE_SERIAL = 6, 'AutoField'
    SQL_TYPE_DATE = 7, 'DateField'
    SQL_TYPE_MONEY = 8, 'DecimalField'
    SQL_TYPE_NULL = 9, None
    SQL_TYPE_DATETIME = 10, 'DateTimeField'
    SQL_TYPE_BYTE = 11, 'BinaryField'
    SQL_TYPE_TEXT = 12, 'TextField'
    SQL_TYPE_VARCHAR = 13, 'CharField'
    SQL_TYPE_INTERVAL = 14, 'DurationField'
    SQL_TYPE_NCHAR = 15, 'CharField'
    SQL_TYPE_NVARCHAR = 16, 'CharField'
    SQL_TYPE_INT8 = 17, 'IntegerField'
    SQL_TYPE_SERIAL8 = 18, 'AutoField'
    SQL_TYPE_SET = 19, None
    SQL_TYPE_MASK = 31, None
    SQL_TYPE_UDTVAR = 40, 'CharField'
    SQL_TYPE_UDTFIXED = 41, None
    SQL_TYPE_LVARCHAR = 43, 'CharField'
    SQL_TYPE_BOOLEAN = 45, 'BoolField'
    SQL_TYPE_BIGINT = 52, 'BigIntegerField'
    SQL_TYPE_BIG_SERIAL = 53, 'AutoField'

    def __init__(self, num, field = None):
        self.num = num
        self.field = field


    @classmethod
    def field_map(cls):
        return {e.num: e.field for e in cls}
