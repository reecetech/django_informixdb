from django.db.models.sql import compiler
from django.db.models import Value
import django


IS_DJANGO_V4 = django.VERSION >= (4, 0)


class SQLCompiler(compiler.SQLCompiler):
    def get_select(self, with_col_aliases=False):
        if IS_DJANGO_V4:
            ret, klass_info, annotations = super().get_select(with_col_aliases)
            return [self.convert_select(node, sql, params) for node, sql, params in ret], klass_info, annotations
        else:
            return super().get_select()

    def convert_select(self, node, sql, params):
        # Informix does not handle field injection in SELECT statement
        if type(node) is Value and next(iter(sql), None) == '%s':
            sql = node.value, []
        return node, sql, params

    def as_sql(self, with_limits=True, with_col_aliases=False):
        raw_sql, fields = super(SQLCompiler, self).as_sql(False, with_col_aliases)

        # special dialect to return first n rows
        if with_limits:
            if self.query.high_mark is not None:
                _select = "SELECT"
                _first = self.query.high_mark
                if self.query.low_mark:
                    _select += " SKIP %s" % self.query.low_mark
                    _first -= self.query.low_mark
                _select += " FIRST %s" % _first
                raw_sql = raw_sql.replace("SELECT", _select, 1)

        return raw_sql.replace(r'%s', '?'), fields


def _list2tuple(arg):
    return tuple(arg) if isinstance(arg, list) else arg


class SQLInsertCompiler(compiler.SQLInsertCompiler, SQLCompiler):
    def as_sql(self):
        result = super(SQLInsertCompiler, self).as_sql()
        return [(ret[0].replace(r'%s', '?'), _list2tuple(ret[1])) for ret in result]


class SQLAggregateCompiler(compiler.SQLAggregateCompiler, SQLCompiler):
    def as_sql(self):
        result = super(SQLAggregateCompiler, self).as_sql()
        return result[0].replace(r'%s', '?'), result[1]


class SQLDeleteCompiler(compiler.SQLDeleteCompiler, SQLCompiler):
    def as_sql(self):
        result = super(SQLDeleteCompiler, self).as_sql()
        return result[0].replace(r'%s', '?'), result[1]


class SQLUpdateCompiler(compiler.SQLUpdateCompiler, SQLCompiler):
    def as_sql(self):
        result = super(SQLUpdateCompiler, self).as_sql()
        return result[0].replace(r'%s', '?'), result[1]
