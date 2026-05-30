# Django ORM Tool

Panel web para ejecutar código ORM de Django directamente desde el browser. Sin shell, sin consola — escribe tu query, presiona `Ctrl+Enter` y ve los resultados como tabla, JSON o SQL generado.

> **Solo para entornos de desarrollo** (`DEBUG=True`). Nunca expongas esto en producción.

---

## Uso en tu proyecto (clonar dentro del proyecto)

### 1. Copiar la carpeta `orm_tool`

Clona el repo y copia **solo la carpeta `orm_tool`** a la raíz de tu proyecto Django (donde está tu `manage.py`):

```bash
# Desde la raíz de tu proyecto Django
git clone https://github.com/tu-usuario/django-orm-tool.git
cp -r django-orm-tool/orm_tool ./orm_tool
```

La estructura debe quedar así:

```
tu-proyecto/
├── manage.py
├── orm_tool/          ← carpeta copiada aquí
│   ├── __init__.py
│   ├── executor.py
│   ├── views.py
│   └── ...
├── tu_app/
└── ...
```

> **Error común:** si dejas `orm_tool` dentro de `django-orm-tool/orm_tool/` sin copiarla,
> Django lanzará `ModuleNotFoundError: No module named 'orm_tool'`.
> La carpeta debe quedar al mismo nivel que `manage.py`.

### 2. Agregar a `INSTALLED_APPS`

En tu `settings.py`:

```python
INSTALLED_APPS = [
    # ... tus apps existentes ...
    'orm_tool',
]
```

### 3. Agregar la URL

En el `urls.py` principal de tu proyecto:

```python
from django.urls import path, include
from django.conf import settings

urlpatterns = [
    # ... tus URLs existentes ...
]

# Solo disponible en desarrollo
if settings.DEBUG:
    urlpatterns += [
        path('orm-tool/', include('orm_tool.urls')),
    ]
```

### 4. Listo

```bash
python manage.py runserver
```

Abre `http://localhost:8000/orm-tool/`

---

## Qué verás

```
┌──────────────────┬────────────────────────────────────────┐
│ Modelos │ Historial │  EDITOR (CodeMirror · Python)        │
│                  │  result = Order.objects                 │
│ ▸ Product        │    .values('customer__name')            │
│   - name         │    .annotate(total=Sum('total'))        │
│   - price        │    .order_by('-total')                  │
│   - stock        │                                        │
│ ▸ Customer       │  [▶ Ejecutar  Ctrl+Enter]              │
│ ▸ Order          ├────────────────────────────────────────┤
│                  │  ✓ 12 filas · 8ms  [Tabla][JSON][SQL]  │
│                  │  ┌──────────────┬──────────┐           │
│                  │  │ customer__name│ total    │           │
│                  │  ├──────────────┼──────────┤           │
│                  │  │ Valentina R. │ 8799.69  │           │
└──────────────────┴────────────────────────────────────────┘
```

---

## Modelos disponibles

Todos los modelos de **todos los apps** instalados en tu proyecto están disponibles directamente por nombre, sin necesidad de importar nada:

```python
# Tus modelos están listos para usar
Product.objects.filter(active=True)
Order.objects.select_related('customer', 'product')
User.objects.filter(is_staff=True)
```

## Helpers ORM incluidos

```python
Q, F,
Count, Sum, Avg, Max, Min, Value,
Case, When,
Coalesce, Concat, Lower, Upper, Length, Now,
TruncDate, TruncMonth, TruncYear,
Prefetch, Subquery, OuterRef, Exists
```

## Cómo escribir queries

Tienes dos formas de retornar resultados:

**1. Última expresión (estilo REPL):**
```python
Product.objects.filter(price__gt=100)[:20]
```

**2. Asignar a `result`:**
```python
qs = Product.objects.filter(price__gt=100)
result = qs.order_by('-price')[:20]
```

Ambas funcionan igual.

---

## Ejemplos

```python
# Filtro básico
Product.objects.filter(stock=0)

# Con relaciones
Order.objects.select_related('customer', 'product').filter(status='pending')

# Agregación
Order.objects.values('status').annotate(cantidad=Count('id'), monto=Sum('total'))

# Búsqueda con Q
Product.objects.filter(Q(name__icontains='pro') | Q(price__gt=500))

# Anotar y filtrar (having)
Customer.objects.annotate(n=Count('orders')).filter(n__gt=3).order_by('-n')

# Subconsulta
from django.db.models import OuterRef, Subquery
last_order = Order.objects.filter(customer=OuterRef('pk')).order_by('-date').values('date')[:1]
Customer.objects.annotate(ultimo_pedido=Subquery(last_order))
```

---

## Tabs de resultados

| Tab | Qué muestra |
|-----|-------------|
| **Tabla** | DataTable con paginación, búsqueda y ordenamiento por columna |
| **JSON** | Array de objetos con syntax highlight |
| **SQL** | La query SQL exacta que Django envía a la base de datos |

---

## Seguridad

- El panel **solo funciona si `DEBUG=True`**. Con `DEBUG=False` lanza un error y no ejecuta nada.
- No están disponibles: `import`, `open`, `os`, `subprocess`, `exec`, `eval`, ni ningún acceso al filesystem.
- Las queries tienen un **timeout de 5 segundos**.
- Usa siempre el guardia en `urls.py` (`if settings.DEBUG`) para asegurarte de que la URL no quede expuesta en producción.

---

## Estructura de la app

```
orm_tool/
├── __init__.py
├── apps.py
├── executor.py      # Motor de ejecución y sandbox de seguridad
├── urls.py
├── views.py
└── templates/
    └── orm_tool/
        └── index.html   # UI completa (sin archivos estáticos propios)
```

No requiere `collectstatic` ni ninguna dependencia extra más allá de Django.

---

## Roadmap

- [ ] Publicar como paquete pip (`pip install django-orm-tool`)
- [ ] Soporte para múltiples bases de datos
- [ ] Exportar resultados a CSV
- [ ] Snippets guardados (persistidos en DB)
- [ ] Modo read-only configurable
