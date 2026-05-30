import ast
import threading
import time
import traceback
import decimal
import datetime

from django.apps import apps
from django.conf import settings
from django.db import connection
from django.db.models import (
    Q, F, Count, Sum, Avg, Max, Min, Value,
    Case, When, CharField, IntegerField, FloatField,
    DecimalField, BooleanField, DateField, DateTimeField,
    Prefetch, Subquery, OuterRef, Exists,
)
from django.db.models.functions import (
    Coalesce, Concat, Lower, Upper, Length, Now,
    TruncDate, TruncMonth, TruncYear,
)


SAFE_BUILTINS = {
    'abs': abs, 'all': all, 'any': any, 'bool': bool,
    'dict': dict, 'dir': dir, 'divmod': divmod,
    'enumerate': enumerate, 'filter': filter, 'float': float,
    'format': format, 'frozenset': frozenset, 'getattr': getattr,
    'hasattr': hasattr, 'hash': hash, 'hex': hex, 'id': id,
    'int': int, 'isinstance': isinstance, 'issubclass': issubclass,
    'iter': iter, 'len': len, 'list': list, 'map': map,
    'max': max, 'min': min, 'next': next, 'oct': oct, 'ord': ord,
    'pow': pow, 'print': print, 'range': range, 'repr': repr,
    'reversed': reversed, 'round': round, 'set': set, 'setattr': setattr,
    'slice': slice, 'sorted': sorted, 'str': str, 'sum': sum,
    'tuple': tuple, 'type': type, 'vars': vars, 'zip': zip,
    'None': None, 'True': True, 'False': False,
}

ORM_HELPERS = {
    'Q': Q, 'F': F,
    'Count': Count, 'Sum': Sum, 'Avg': Avg, 'Max': Max, 'Min': Min,
    'Value': Value, 'Case': Case, 'When': When,
    'CharField': CharField, 'IntegerField': IntegerField,
    'FloatField': FloatField, 'DecimalField': DecimalField,
    'BooleanField': BooleanField, 'DateField': DateField,
    'DateTimeField': DateTimeField,
    'Coalesce': Coalesce, 'Concat': Concat, 'Lower': Lower,
    'Upper': Upper, 'Length': Length, 'Now': Now,
    'TruncDate': TruncDate, 'TruncMonth': TruncMonth, 'TruncYear': TruncYear,
    'Prefetch': Prefetch, 'Subquery': Subquery,
    'OuterRef': OuterRef, 'Exists': Exists,
}


def _serialize_value(val):
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, decimal.Decimal):
        return float(val)
    if isinstance(val, (datetime.datetime, datetime.date, datetime.time)):
        return str(val)
    return str(val)


def _is_values_queryset(qs):
    return qs._iterable_class.__name__ in ('ValuesIterable', 'ValuesListIterable')


def _queryset_to_table(qs):
    if _is_values_queryset(qs):
        rows = list(qs)
        if not rows:
            return [], []
        if isinstance(rows[0], dict):
            columns = list(rows[0].keys())
            serialized = [[_serialize_value(r[c]) for c in columns] for r in rows]
        else:
            # ValuesListIterable → tuples
            columns = [f'col_{i}' for i in range(len(rows[0]))]
            serialized = [[_serialize_value(v) for v in r] for r in rows]
        return columns, serialized

    # Regular QuerySet — try to get concrete fields
    rows = list(qs)
    if not rows:
        return [], []

    model = rows[0].__class__
    fields = [f.name for f in model._meta.get_fields()
              if hasattr(f, 'column') and not f.many_to_many]
    columns = fields

    serialized = []
    for obj in rows:
        row = []
        for f in fields:
            try:
                row.append(_serialize_value(getattr(obj, f)))
            except Exception:
                row.append(None)
        serialized.append(row)

    return columns, serialized


def _serialize_result(result):
    from django.db.models.query import QuerySet

    if isinstance(result, QuerySet):
        columns, rows = _queryset_to_table(result)
        sql = ''
        try:
            sql = str(result.query)
        except Exception:
            pass
        return {
            'type': 'queryset',
            'columns': columns,
            'rows': rows,
            'count': len(rows),
            'sql': sql,
        }

    if isinstance(result, (list, tuple)):
        if not result:
            return {'type': 'list', 'columns': [], 'rows': [], 'count': 0, 'sql': ''}
        first = result[0]
        if isinstance(first, dict):
            columns = list(first.keys())
            rows = [[_serialize_value(item.get(c)) for c in columns] for item in result]
            return {'type': 'list', 'columns': columns, 'rows': rows, 'count': len(rows), 'sql': ''}
        # List of model instances
        from django.db.models import Model
        if isinstance(first, Model):
            qs_like = result
            model = first.__class__
            fields = [f.name for f in model._meta.get_fields()
                      if hasattr(f, 'column') and not f.many_to_many]
            columns = fields
            rows = []
            for obj in qs_like:
                rows.append([_serialize_value(getattr(obj, f, None)) for f in fields])
            return {'type': 'list', 'columns': columns, 'rows': rows, 'count': len(rows), 'sql': ''}
        # Primitive list
        columns = ['value']
        rows = [[_serialize_value(v)] for v in result]
        return {'type': 'list', 'columns': columns, 'rows': rows, 'count': len(rows), 'sql': ''}

    if isinstance(result, dict):
        columns = list(result.keys())
        rows = [[_serialize_value(result[c]) for c in columns]]
        return {'type': 'dict', 'columns': columns, 'rows': rows, 'count': 1, 'sql': ''}

    # Scalar
    return {
        'type': 'scalar',
        'columns': ['result'],
        'rows': [[_serialize_value(result)]],
        'count': 1,
        'sql': '',
    }


def _build_exec_globals():
    g = {'__builtins__': SAFE_BUILTINS}
    g.update(ORM_HELPERS)
    for model in apps.get_models():
        g[model.__name__] = model
    return g


def _extract_last_expr(code):
    """If the last statement is an expression, compile it separately so we can eval it."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code, None

    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last_expr = tree.body[-1]
        rest = tree.body[:-1]
        rest_code = ast.unparse(ast.Module(body=rest, type_ignores=[]))
        expr_code = ast.unparse(last_expr.value)
        return rest_code, expr_code

    return code, None


def run_orm_code(code: str) -> dict:
    if not settings.DEBUG:
        return {
            'error': 'ORM Tool solo está disponible con DEBUG=True.',
            'columns': [], 'rows': [], 'count': 0, 'sql': '',
            'execution_time_ms': 0,
        }

    result_holder = {'result': None, 'error': None, 'done': False}
    rest_code, expr_code = _extract_last_expr(code)
    exec_globals = _build_exec_globals()

    initial_queries = len(connection.queries)
    start = time.perf_counter()

    def _run():
        try:
            if rest_code.strip():
                exec(compile(rest_code, '<orm_tool>', 'exec'), exec_globals)  # noqa: S102
            if expr_code:
                val = eval(compile(expr_code, '<orm_tool>', 'eval'), exec_globals)  # noqa: S307
                result_holder['result'] = val
            elif 'result' in exec_globals:
                result_holder['result'] = exec_globals['result']
        except Exception:
            result_holder['error'] = traceback.format_exc()
        finally:
            result_holder['done'] = True

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=5)

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    if not result_holder['done']:
        return {
            'error': 'Timeout: la query tardó más de 5 segundos.',
            'columns': [], 'rows': [], 'count': 0, 'sql': '',
            'execution_time_ms': elapsed_ms,
        }

    if result_holder['error']:
        return {
            'error': result_holder['error'],
            'columns': [], 'rows': [], 'count': 0, 'sql': '',
            'execution_time_ms': elapsed_ms,
        }

    try:
        data = _serialize_result(result_holder['result'])
    except Exception:
        data = {
            'error': traceback.format_exc(),
            'columns': [], 'rows': [], 'count': 0, 'sql': '',
        }

    data['execution_time_ms'] = elapsed_ms
    data.setdefault('error', None)
    return data
