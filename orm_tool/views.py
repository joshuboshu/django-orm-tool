import json

from django.apps import apps
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .executor import run_orm_code


def _get_model_info():
    result = []
    for model in apps.get_models():
        fields = []
        for f in model._meta.get_fields():
            if hasattr(f, 'column'):
                field_type = f.get_internal_type() if hasattr(f, 'get_internal_type') else type(f).__name__
                fields.append({'name': f.name, 'type': field_type})
        result.append({
            'app': model._meta.app_label,
            'name': model.__name__,
            'verbose': str(model._meta.verbose_name_plural).title(),
            'fields': fields,
        })
    result.sort(key=lambda m: (m['app'], m['name']))
    return result


def index(request):
    models = _get_model_info()
    models_json = json.dumps({m['name']: m['fields'] for m in models})
    return render(request, 'orm_tool/index.html', {'models': models, 'models_json': models_json})


@csrf_exempt
@require_http_methods(['POST'])
def execute(request):
    try:
        body = json.loads(request.body)
        code = body.get('code', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    if not code:
        return JsonResponse({'error': 'No hay código para ejecutar'}, status=400)

    result = run_orm_code(code)
    return JsonResponse(result)
