from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.utils import IntegrityError
from django.http import Http404, HttpResponseNotFound, HttpResponse, HttpResponseNotAllowed
from django.template import loader
from django.db import connection
import re
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import os
from datetime import datetime
from django.conf import settings
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.http import Http404, HttpResponse
import matplotlib
import base64
from io import BytesIO
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.apps import apps
from django.db.models import Count, Sum, F, Q
from django.db.models.functions import TruncMonth
from django.core.exceptions import ObjectDoesNotExist
from django.utils.dateparse import parse_date
import matplotlib.pyplot as plt
import logging
from django.db.models.functions import Cast, Lower
from django.db.models import TextField, F
from .forms import DynamicModelForm
import numpy as np
from django.db.models import Max

matplotlib.use('Agg')
logger = logging.getLogger(__name__)
SAFE_PRESET_QUERIES = {
    'emp_count_by_dept': "SELECT department.name, COUNT(employee.id) FROM employee JOIN employment_record ON employee.id = employment_record.employee_id JOIN department ON employment_record.department_id = department.id GROUP BY department.name;",
    'contracts_with_clients': "SELECT contract.contract_number, client.name FROM contract JOIN client ON contract.client_id = client.id;",
    'estimates_for_requests': "SELECT request.id, materials.name, estimate.material_quantity FROM estimate JOIN request ON estimate.request_id = request.id JOIN materials ON estimate.material_id = materials.id;"
}
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        if not username or not password:
            logger.warning(f"Попытка входа с пустыми полями с IP: {request.META.get('REMOTE_ADDR')}")
            return render(request, 'login.html', {'error': 'Пожалуйста, заполните все поля.'})
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            logger.info(f"Пользователь {user.username} вошёл в систему с IP: {request.META.get('REMOTE_ADDR')}")
            return redirect('main_menu')
        else:
            logger.warning(f"Неудачная попытка входа для пользователя '{username}' с IP: {request.META.get('REMOTE_ADDR')}")
            return render(request, 'login.html', {'error': 'Неверный логин или пароль.'})
    else:
        return render(request, 'login.html')
@login_required
def main_menu(request):
    return render(request, 'main_menu.html')
@login_required
def model_list(request):
    all_models = apps.get_models()
    core_models = [model for model in all_models if model._meta.app_label == 'core']
    allowed_models = []
    for model in core_models:
        perm = f'{model._meta.app_label}.view_{model._meta.model_name}'
        if request.user.has_perm(perm):
            has_fk = any(
                field.is_relation and field.many_to_one
                for field in model._meta.get_fields()
            )
            is_referenced = any(
                field.related_model == model and field.many_to_one
                for other_model in core_models
                for field in other_model._meta.get_fields()
                if field.is_relation
            )
            if has_fk and is_referenced:
                allowed_models.append((model, model._meta.model_name, model._meta.verbose_name_plural))
    return render(request, 'model_list.html', {'models': allowed_models})

def get_object_field_values(obj):
    field_values = {}
    for field in obj._meta.get_fields():
        if field.many_to_many or field.one_to_many:
            continue
        try:
            value = getattr(obj, field.name)
            if hasattr(field, 'related_model') and value is not None:
                value = str(value)
            field_values[field.verbose_name or field.name] = value
        except AttributeError:
            pass
    return field_values

@login_required
def model_detail(request, model_name):
    model_class = apps.get_model('core', model_name)
    if not request.user.has_perm(f'{model_class._meta.app_label}.view_{model_class._meta.model_name}'):
        return render(request, '403.html', {'message': 'У вас нет прав на просмотр этой модели.'})

    search_query = request.GET.get('search', '').strip()
    sort_param = request.GET.get('sort', '')
    objects = model_class.objects.all()

    if search_query:
        db_fields = []
        for f in model_class._meta.get_fields():
            if getattr(f, 'many_to_many', False) or getattr(f, 'one_to_many', False):
                continue
            if not hasattr(f, 'name') and not hasattr(f, 'attname'):
                continue
            db_fields.append(f)

        cast_annotations = {}
        for f in db_fields:
            if getattr(f, 'is_relation', False) and getattr(f, 'many_to_one', False) and hasattr(f, 'related_model'):
                related = f.related_model
                rel_text_field = None
                for rf in related._meta.get_fields():
                    if hasattr(rf, 'get_internal_type'):
                        if rf.get_internal_type() in ['CharField', 'TextField']:
                            rel_text_field = rf.name
                            break
                if rel_text_field:
                    source = f"{f.name}__{rel_text_field}"
                else:
                    source = f.attname if hasattr(f, 'attname') else f.name
            else:
                source = f.name if hasattr(f, 'name') else (f.attname if hasattr(f, 'attname') else None)
            if not source:
                continue
            annotated_name = f"{source.replace('__', '_')}_text_lc"
            try:
                cast_annotations[annotated_name] = Lower(Cast(F(source), TextField()))
            except Exception:
                continue

        if cast_annotations:
            objects = objects.annotate(**cast_annotations)
            q_objects = Q()
            sq = search_query.lower()
            for ann in cast_annotations.keys():
                q_objects |= Q(**{f"{ann}__contains": sq})
            if q_objects:
                objects = objects.filter(q_objects)

    if sort_param:
        try:
            field_name = sort_param.lstrip('-')
            try:
                model_class._meta.get_field(field_name)
                objects = objects.order_by(sort_param)
            except Exception:
                pass
        except Exception:
            pass

    sortable_fields = []
    for field in model_class._meta.get_fields():
        if (hasattr(field, 'get_internal_type') and
            not getattr(field, 'many_to_many', False) and
            not getattr(field, 'one_to_many', False) and
            field.get_internal_type() in ['CharField', 'TextField', 'IntegerField', 'FloatField', 'DateField', 'DateTimeField', 'BooleanField']):
            sortable_fields.append({
                'name': field.name,
                'verbose_name': field.verbose_name or field.name
            })

    objects_with_fields = []
    for obj in objects:
        field_values = get_object_field_values(obj)
        objects_with_fields.append({
            'obj': obj,
            'fields': field_values
        })

    return render(request, 'model_detail.html', {
        'objects_with_fields': objects_with_fields,
        'model_name': model_name,
        'verbose_name': model_class._meta.verbose_name_plural,
        'search_query': search_query,
        'current_sort': sort_param,
        'sortable_fields': sortable_fields,
    })

@login_required
def model_edit(request, model_name, pk=None):
    try:
        model_class = apps.get_model('core', model_name)
    except LookupError:
        logger.error(f"Модель '{model_name}' не найдена.")
        messages.error(request, f"Модель '{model_name}' не найдена.")
        return redirect('model_list')
    if pk:
        try:
            instance = get_object_or_404(model_class, pk=pk)
        except Exception as e:
            logger.error(f"Ошибка получения объекта {model_name} (ID: {pk}) пользователем {request.user.username}: {e}")
            messages.error(request, f"Ошибка получения объекта: {e}")
            return redirect('model_list')
        perm = f'{model_class._meta.app_label}.change_{model_class._meta.model_name}'
        action = "Редактировать"
        object_pk = pk
        initial_data = None
    else:
        instance = None
        perm = f'{model_class._meta.app_label}.add_{model_class._meta.model_name}'
        action = "Создать"
        object_pk = None
        initial_data = {}
        for field in model_class._meta.get_fields():
            if hasattr(field, 'default') and field.default is not None and field.default != '':
                if callable(field.default):
                    initial_data[field.name] = field.default()
                else:
                    initial_data[field.name] = field.default
    if not request.user.has_perm(perm):
        logger.warning(f"Пользователь {request.user.username} попытался {action.lower()} {model_name}, но не имеет прав.")
        return render(request, '403.html', {'message': 'У вас нет прав на изменение этой модели.'})
    if request.method == 'POST':
        form = DynamicModelForm(model_class, request.POST, instance=instance)
        if form.is_valid():
            try:
                obj_name = str(form.instance) if instance else "Запись"
                form.save()
                if instance:
                    logger.info(f"Пользователь {request.user.username} изменил {model_name} '{obj_name}' (ID: {pk})")
                    messages.success(request, f'{obj_name} успешно изменена.')
                else:
                    logger.info(f"Пользователь {request.user.username} создал {model_name} '{obj_name}' (ID: {form.instance.pk})")
                    messages.success(request, f'{obj_name} успешно создана.')
                return redirect('model_detail', model_name=model_name)
            except ValidationError as e:
                logger.error(f"Ошибка валидации модели при {action.lower()} {model_name} пользователем {request.user.username}: {e}")
                messages.error(request, f"Ошибка валидации модели: {e}")
            except IntegrityError as e:
                logger.error(f"Ошибка целостности при {action.lower()} {model_name} пользователем {request.user.username}: {e}")
                messages.error(request, f"Ошибка целостности данных: {e}")
            except Exception as e:
                logger.error(f"Неизвестная ошибка при сохранении объекта {model_name} пользователем {request.user.username}: {e}")
                messages.error(request, f"Ошибка при сохранении: {e}")
        else:
            logger.error(f"Ошибка валидации формы при {action.lower()} {model_name} пользователем {request.user.username}: {form.errors}")
    else:
        form = DynamicModelForm(model_class, instance=instance, initial=initial_data)
    verbose_name = model_class._meta.verbose_name
    return render(request, 'model_edit.html', {
        'form': form,
        'action': action,
        'model_name': model_name,
        'verbose_name': verbose_name,
        'object': instance,
        'object_pk': object_pk,
    })

@login_required
def model_view(request, model_name, pk):
    try:
        model_class = apps.get_model('core', model_name)
    except LookupError:
        logger.error(f"Модель '{model_name}' не найдена.")
        messages.error(request, f"Модель '{model_name}' не найдена.")
        return redirect('model_list')
    perm = f'{model_class._meta.app_label}.view_{model_class._meta.model_name}'
    if not request.user.has_perm(perm):
        logger.warning(f"Пользователь {request.user.username} попытался посмотреть {model_name} (ID: {pk}), но не имеет прав.")
        return render(request, '403.html', {'message': 'У вас нет прав на просмотр этой модели.'})
    try:
        obj = get_object_or_404(model_class, pk=pk)
    except Exception as e:
        logger.error(f"Ошибка получения объекта {model_name} (ID: {pk}) для просмотра пользователем {request.user.username}: {e}")
        messages.error(request, f"Ошибка получения объекта: {e}")
        return redirect('model_list')
    fields = []
    for field in model_class._meta.get_fields():
        if field.many_to_many or field.one_to_many:
             continue
        try:
            field_value = getattr(obj, field.name)
            if hasattr(field, 'related_model') and field_value is not None:
                 field_value = str(field_value)
            fields.append({'name': field.name, 'verbose_name': field.verbose_name or field.name, 'value': field_value})
        except AttributeError:
            pass
    return render(request, 'model_view.html', {
        'object': obj,
        'model_name': model_name,
        'verbose_name': model_class._meta.verbose_name,
        'fields': fields,
    })
@login_required
def model_delete(request, model_name, pk):
    try:
        model_class = apps.get_model('core', model_name)
    except LookupError:
        logger.error(f"Модель '{model_name}' не найдена.")
        messages.error(request, f"Модель '{model_name}' не найдена.")
        return redirect('model_list')
    perm = f'{model_class._meta.app_label}.change_{model_class._meta.model_name}'
    if not request.user.has_perm(perm):
        logger.warning(f"Пользователь {request.user.username} попытался удалить {model_name} (ID: {pk}), но не имеет прав.")
        return render(request, '403.html', {'message': 'У вас нет прав на удаление этой модели.'})
    try:
        obj = model_class.objects.get(pk=pk)
    except model_class.DoesNotExist:
        logger.warning(f"Пользователь {request.user.username} попытался удалить несуществующий объект {model_name} (ID: {pk}).")
        template = loader.get_template('404.html')
        return HttpResponseNotFound(template.render(request=request))
    except Exception as e:
        logger.error(f"Ошибка получения объекта {model_name} (ID: {pk}) для удаления пользователем {request.user.username}: {e}")
        messages.error(request, f"Ошибка получения объекта: {e}")
        return redirect('model_list')
    if request.method == 'POST':
        obj_name = str(obj)
        try:
            obj.delete()
            logger.info(f"Пользователь {request.user.username} удалил {model_name} '{obj_name}' (ID: {pk})")
            messages.success(request, f'Объект "{obj_name}" успешно удалён.')
            return redirect('model_detail', model_name=model_name)
        except IntegrityError as e:
            logger.error(f"Ошибка целостности при удалении {model_name} (ID: {pk}) пользователем {request.user.username}: {e}")
            messages.error(request, f'Невозможно удалить объект "{obj_name}", потому что на него ссылаются другие записи. Пожалуйста, удалите или измените связанные записи сначала.')
            return render(request, 'model_delete_confirm.html', {
                'object': obj,
                'model_name': model_name,
                'verbose_name': model_class._meta.verbose_name,
            })
        except Exception as e:
            logger.error(f"Неизвестная ошибка при удалении {model_name} (ID: {pk}) пользователем {request.user.username}: {e}")
            messages.error(request, f'Произошла ошибка при удалении: {e}')
            return render(request, 'model_delete_confirm.html', {
                'object': obj,
                'model_name': model_name,
                'verbose_name': model_class._meta.verbose_name,
            })
    return render(request, 'model_delete_confirm.html', {
        'object': obj,
        'model_name': model_name,
        'verbose_name': model_class._meta.verbose_name,
    })
def generate_chart_image(data, chart_type='bar', title='График', xlabel='X', ylabel='Y'):
    fig, ax = plt.subplots(figsize=(20, 6))

    if not data:
        ax.text(0.5, 0.5, 'Нет данных', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes, fontsize=14)
        ax.set_title(title, fontsize=16)
        if chart_type in ['bar', 'line']:
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
    else:
        if chart_type == 'bar':
            if isinstance(data[0], dict):
                labels = [item['label'] for item in data]
                values = [item['value'] for item in data]
            else:
                x_vals, y_vals = zip(*data)
                labels, values = x_vals, y_vals

            bars = ax.bar(labels, values)
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=45, ha="right")
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2., height,
                        f'{value}',
                        ha='center', va='bottom', fontsize=10)

        elif chart_type == 'line':
            if isinstance(data[0], dict):
                labels = [item['label'] for item in data]
                values = [item['value'] for item in data]
            else:
                x_vals, y_vals = zip(*data)
                labels, values = x_vals, y_vals

            ax.plot(labels, values, marker='o', linestyle='-')
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=45, ha="right")

        elif chart_type == 'pie':
            if isinstance(data[0], dict):
                labels = [item['label'] for item in data]
                values = [item['value'] for item in data]
            else:
                x_vals, y_vals = zip(*data)
                labels, values = x_vals, y_vals

            if all(v == 0 for v in values):
                ax.text(0.5, 0.5, 'Нет данных', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes, fontsize=14)
            else:
                non_zero_data = [(l, v) for l, v in zip(labels, values) if v != 0]
                if non_zero_data:
                    filtered_labels, filtered_values = zip(*non_zero_data)
                    colors_list = plt.cm.Set3(np.linspace(0, 1, len(filtered_labels)))
                    wedges, texts, autotexts = ax.pie(filtered_values, labels=filtered_labels, autopct='%1.1f%%', startangle=140, colors=colors_list)
                    plt.setp(autotexts, size=10, weight="bold")
                else:
                    ax.text(0.5, 0.5, 'Нет данных', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes, fontsize=14)

        else:
            ax.text(0.5, 0.5, f'Тип графика {chart_type} не поддерживается', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes, fontsize=14)

        ax.set_title(title, fontsize=16)
        if chart_type in ['bar', 'line']:
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
    plt.close(fig)
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    graphic = base64.b64encode(image_png)
    graphic = graphic.decode('utf-8')
    return graphic
def generate_all_chart_types(data, title='График', xlabel='X', ylabel='Y'):
    chart_images = {}
    for chart_type in ['bar', 'line', 'pie']:
        specific_title = f"{title} ({chart_type.capitalize()})"
        chart_images[chart_type] = generate_chart_image(
            data=data,
            chart_type=chart_type,
            title=specific_title,
            xlabel=xlabel,
            ylabel=ylabel
        )
    return chart_images
@login_required
def analytics_select(request):
    available_analytics = [
        ('requests_by_date', 'Заявки по месяцам'),
        ('estimates_by_date', 'Сметы по месяцам'),
        ('top_materials_used', 'Топ-5 материалов по использованию'),
        ('employees_hired_by_date', 'Новые сотрудники по месяцам'),
        ('employees_by_department', 'Сотрудники по отделам'),
        ('supplies_by_date', 'Поставки по месяцам'),
        ('tasks_by_date', 'Задачи по месяцам'),
        ('contracts_by_construction_management', 'Контракты по стройуправлениям'),
        ('sites_by_city', 'Объекты по городам'),
        ('crew_sizes', 'Размеры бригад'),
    ]
    permissions = {
        'can_view_contracts': request.user.has_perm('core.view_contract'),
        'can_view_requests': request.user.has_perm('core.view_request'),
        'can_view_employees': request.user.has_perm('core.view_employee'),
        'can_view_departments': request.user.has_perm('core.view_department'),
        'can_view_materials': request.user.has_perm('core.view_materials'),
        'can_view_estimates': request.user.has_perm('core.view_estimate'),
        'can_view_clients': request.user.has_perm('core.view_client'),
        'can_view_employment_records': request.user.has_perm('core.view_employmentrecord'),
        'can_view_supplies': request.user.has_perm('core.view_supply'),
        'can_view_tasks': request.user.has_perm('core.view_tasks'),
        'can_view_construction_sites': request.user.has_perm('core.view_constructionsite'),
        'can_view_construction_managements': request.user.has_perm('core.view_constructionmanagement'),
        'can_view_cities': request.user.has_perm('core.view_city'),
        'can_view_crews': request.user.has_perm('core.view_crew'),
        'can_view_crew_compositions': apps.get_model('core', 'CrewComposition') is not None and request.user.has_perm('core.view_crew'),
    }
    filter_date_from = request.GET.get('date_from', '')
    filter_date_to = request.GET.get('date_to', '')
    selected_type = request.GET.get('type', '')
    return render(request, 'analytics_select.html', {
        'available_analytics': available_analytics,
        'permissions': permissions,
        'selected_type': selected_type,
        'filter_date_from': filter_date_from,
        'filter_date_to': filter_date_to,
    })
@login_required
def analytics_generate(request):
    chart_type_param = request.GET.get('type', '')
    filter_date_from_str = request.GET.get('date_from', '')
    filter_date_to_str = request.GET.get('date_to', '')

    allowed_types = [
        'requests_by_date', 'estimates_by_date', 'top_materials_used',
        'employees_hired_by_date', 'employees_by_department', 'supplies_by_date',
        'tasks_by_date', 'contracts_by_construction_management', 'sites_by_city',
        'crew_sizes'
    ]

    if chart_type_param not in allowed_types:
        messages.error(request, "Неверный тип аналитики.")
        return render(request, 'analytics_result.html', {'error': 'Неверный тип аналитики.'})

    filter_date_from = None
    filter_date_to = None
    try:
        if filter_date_from_str:
            filter_date_from = parse_date(filter_date_from_str)
        if filter_date_to_str:
            filter_date_to = parse_date(filter_date_to_str)
    except ValueError:
        messages.error(request, "Неверный формат даты. Используйте ГГГГ-ММ-ДД.")
        return render(request, 'analytics_result.html', {'error': 'Неверный формат даты.'})

    try:
        all_models = apps.get_models()
        core_models = {model._meta.label_lower: model for model in all_models if model._meta.app_label == 'core'}

        Contract = core_models.get('core.contract')
        Request = core_models.get('core.request')
        Employee = core_models.get('core.employee')
        Department = core_models.get('core.department')
        Materials = core_models.get('core.materials')
        Estimate = core_models.get('core.estimate')
        Client = core_models.get('core.client')
        EmploymentRecord = core_models.get('core.employmentrecord')
        Supply = core_models.get('core.supply')
        Tasks = core_models.get('core.tasks')
        ConstructionSite = core_models.get('core.constructionsite')
        ConstructionManagement = core_models.get('core.constructionmanagement')
        Equipment = core_models.get('core.equipment')
        Crew = core_models.get('core.crew')
        City = core_models.get('core.city')
        Street = core_models.get('core.street')
        Region = core_models.get('core.region')

        data = []
        title = ""
        xlabel = "X"
        ylabel = "Y"

        if chart_type_param == 'requests_by_date':
            if not request.user.has_perm('core.view_request'):
                raise PermissionError("Нет прав на просмотр заявок.")

            queryset = Request.objects.all()
            if filter_date_from:
                queryset = queryset.filter(request_date__gte=filter_date_from)
            if filter_date_to:
                queryset = queryset.filter(request_date__lte=filter_date_to)

            requests_by_date_raw = (
                queryset
                .annotate(day=TruncMonth('request_date'))
                .values('day')
                .annotate(count=Count('id'))
                .order_by('day')
            )
            data = [
                {'label': item['day'].strftime('%Y-%m'), 'value': item['count']}
                for item in requests_by_date_raw
            ]
            title = 'Заявки по месяцам'
            xlabel = 'Месяц'
            ylabel = 'Количество'

        elif chart_type_param == 'estimates_by_date':
            if not request.user.has_perm('core.view_estimate'):
                raise PermissionError("Нет прав на просмотр смет.")

            estimate_queryset = Estimate.objects.all()
            if filter_date_from or filter_date_to:
                request_filter = Q()
                if filter_date_from:
                    request_filter &= Q(request__request_date__date__gte=filter_date_from)
                if filter_date_to:
                    request_filter &= Q(request__request_date__date__lte=filter_date_to)
                estimate_queryset = estimate_queryset.filter(request_filter)

            estimates_by_date_raw = (
                estimate_queryset
                .annotate(month=TruncMonth('request__request_date'))
                .values('month')
                .annotate(count=Count('id'))
                .order_by('month')
            )
            data = [
                {'label': item['month'].strftime('%Y-%m'), 'value': item['count']}
                for item in estimates_by_date_raw
            ]
            title = 'Сметы по месяцам'
            xlabel = 'Месяц'
            ylabel = 'Количество'

        elif chart_type_param == 'top_materials_used':
            if not (request.user.has_perm('core.view_estimate') and request.user.has_perm('core.view_materials')):
                raise PermissionError("Нет прав на просмотр смет или материалов.")

            estimate_queryset = Estimate.objects.all()
            if filter_date_from or filter_date_to:
                request_filter = Q()
                if filter_date_from:
                    request_filter &= Q(request__request_date__date__gte=filter_date_from)
                if filter_date_to:
                    request_filter &= Q(request__request_date__date__lte=filter_date_to)
                estimate_queryset = estimate_queryset.filter(request_filter)

            top_materials_raw = (
                estimate_queryset
                .values(material_name=F('material__name'))
                .annotate(total_quantity=Sum('material_quantity'))
                .order_by('-total_quantity')[:5]
            )
            data = [
                {'label': item['material_name'], 'value': item['total_quantity'] or 0}
                for item in top_materials_raw
            ]
            title = 'Топ-5 материалов'
            xlabel = 'Материал'
            ylabel = 'Количество'

        elif chart_type_param == 'employees_hired_by_date':
            if not request.user.has_perm('core.view_employmentrecord'):
                raise PermissionError("Нет прав на просмотр трудовых книжек.")

            queryset = EmploymentRecord.objects.filter(event_type='Приём')
            if filter_date_from:
                queryset = queryset.filter(hire_date__date__gte=filter_date_from)
            if filter_date_to:
                queryset = queryset.filter(hire_date__date__lte=filter_date_to)

            employees_by_date_raw = (
                queryset
                .annotate(month=TruncMonth('hire_date'))
                .values('month')
                .annotate(count=Count('employee_id', distinct=True))
                .order_by('month')
            )
            data = [
                {'label': item['month'].strftime('%Y-%m'), 'value': item['count']}
                for item in employees_by_date_raw
            ]
            title = 'Новые сотрудники по месяцам'
            xlabel = 'Месяц'
            ylabel = 'Количество'

        elif chart_type_param == 'employees_by_department':
            if not (request.user.has_perm('core.view_employmentrecord') and request.user.has_perm('core.view_department')):
                raise PermissionError("Нет прав на просмотр трудовых книжек или отделов.")
            latest_employees = EmploymentRecord.objects.filter(
                id__in=EmploymentRecord.objects.filter(event_type='Приём')
                .values('employee_id')
                .annotate(max_id=Max('id'))
                .values_list('max_id', flat=True)
            ).select_related('department')

            if filter_date_from:
                latest_employees = latest_employees.filter(hire_date__date__gte=filter_date_from)
            if filter_date_to:
                latest_employees = latest_employees.filter(hire_date__date__lte=filter_date_to)

            employees_by_dept_raw = (
                latest_employees
                .values(dept_name=F('department__name'))
                .annotate(count=Count('employee_id', distinct=True))
                .exclude(dept_name__isnull=True)
                .order_by('-count')
            )
            data = [
                {'label': item['dept_name'], 'value': item['count']}
                for item in employees_by_dept_raw
            ]
            title = 'Сотрудники по отделам'
            xlabel = 'Отдел'
            ylabel = 'Количество'

        elif chart_type_param == 'supplies_by_date':
            if not request.user.has_perm('core.view_supply'):
                raise PermissionError("Нет прав на просмотр поставок.")

            queryset = Supply.objects.all()
            if filter_date_from:
                queryset = queryset.filter(supply_date__date__gte=filter_date_from)
            if filter_date_to:
                queryset = queryset.filter(supply_date__date__lte=filter_date_to)

            supplies_by_date_raw = (
                queryset
                .annotate(month=TruncMonth('supply_date'))
                .values('month')
                .annotate(count=Count('id'))
                .order_by('month')
            )
            data = [
                {'label': item['month'].strftime('%Y-%m'), 'value': item['count']}
                for item in supplies_by_date_raw
            ]
            title = 'Поставки по месяцам'
            xlabel = 'Месяц'
            ylabel = 'Количество'

        elif chart_type_param == 'tasks_by_date':
            if not request.user.has_perm('core.view_tasks'):
                raise PermissionError("Нет прав на просмотр задач.")

            queryset = Tasks.objects.all()
            if filter_date_from:
                queryset = queryset.filter(work_date__gte=filter_date_from)
            if filter_date_to:
                queryset = queryset.filter(work_date__lte=filter_date_to)

            tasks_by_date_raw = (
                queryset
                .annotate(month=TruncMonth('work_date'))
                .values('month')
                .annotate(count=Count('id'))
                .order_by('month')
            )
            data = [
                {'label': item['month'].strftime('%Y-%m'), 'value': item['count']}
                for item in tasks_by_date_raw
            ]
            title = 'Задачи по месяцам'
            xlabel = 'Месяц'
            ylabel = 'Количество'

        elif chart_type_param == 'contracts_by_construction_management':
            if not (request.user.has_perm('core.view_contract') and request.user.has_perm('core.view_constructionmanagement')):
                raise PermissionError("Нет прав на просмотр контрактов или стройуправлений.")

            contracts_by_cm_raw = (
                Contract.objects
                .values(cm_name=F('construction_management__name'))
                .annotate(count=Count('id'))
                .order_by('-count')
            )
            data = [
                {'label': item['cm_name'], 'value': item['count']}
                for item in contracts_by_cm_raw
            ]
            title = 'Контракты по строительным управлениям'
            xlabel = 'Стройуправление'
            ylabel = 'Количество'

        elif chart_type_param == 'sites_by_city':
            if not (request.user.has_perm('core.view_constructionsite') and request.user.has_perm('core.view_city')):
                raise PermissionError("Нет прав на просмотр объектов или городов.")

            sites_by_city_raw = (
                ConstructionSite.objects
                .values(city_name=F('city__city_name'))
                .annotate(count=Count('id'))
                .exclude(city_name__isnull=True)
                .order_by('-count')
            )
            data = [
                {'label': item['city_name'], 'value': item['count']}
                for item in sites_by_city_raw
            ]
            title = 'Объекты по городам'
            xlabel = 'Город'
            ylabel = 'Количество'

        elif chart_type_param == 'crew_sizes':
            if not request.user.has_perm('core.view_crew'):
                raise PermissionError("Нет прав на просмотр бригад.")

            CrewComposition = apps.get_model('core', 'CrewComposition')
            if not CrewComposition:
                raise ObjectDoesNotExist("Модель CrewComposition не найдена.")

            crew_sizes_raw = (
                CrewComposition.objects
                .values(crew_name=F('crew__name'))
                .annotate(count=Count('employee_id'))
                .order_by('-count')
            )
            data = [
                {'label': item['crew_name'], 'value': item['count']}
                for item in crew_sizes_raw
            ]
            title = 'Размеры бригад'
            xlabel = 'Бригада'
            ylabel = 'Количество сотрудников'

        chart_images_dict = {}
        for chart_type in ['bar', 'line', 'pie']:  # Проходим по трём типам
            chart_images_dict[chart_type] = generate_chart_image(
                data=data,
                chart_type=chart_type,
                title=title,
                xlabel=xlabel,
                ylabel=ylabel
            )

        return render(request, 'analytics_result.html', {
            'chart_images': chart_images_dict,
            'title': title,
            'filter_date_from': filter_date_from_str,
            'filter_date_to': filter_date_to_str,
            'chart_type_display': dict([
                ('requests_by_date', 'Заявки по месяцам'),
                ('estimates_by_date', 'Сметы по месяцам'),
                ('top_materials_used', 'Топ-5 материалов по использованию'),
                ('employees_hired_by_date', 'Новые сотрудники по месяцам'),
                ('employees_by_department', 'Сотрудники по отделам'),
                ('supplies_by_date', 'Поставки по месяцам'),
                ('tasks_by_date', 'Задачи по месяцам'),
                ('contracts_by_construction_management', 'Контракты по стройуправлениям'),
                ('sites_by_city', 'Объекты по городам'),
                ('crew_sizes', 'Размеры бригад'),
            ]).get(chart_type_param, 'Неизвестный тип'),
        })

    except PermissionError as e:
        messages.error(request, str(e))
        return render(request, 'analytics_result.html', {'error': str(e)})
    except Exception as e:
        logger.error(f"Ошибка при генерации аналитики пользователем {request.user.username}: {e}")
        messages.error(request, f"Ошибка при генерации аналитики: {e}")
        return render(request, 'analytics_result.html', {'error': 'Произошла ошибка сервера.'})

@login_required
def manual_query_view(request):
    result_columns = []
    result_rows = []
    error_message = ""
    success_message = ""
    sql_query = ""
    query_executed = False
    preset_query_id = None
    allowed_models = apps.get_models()
    allowed_tables = []
    for model in allowed_models:
        app_label = model._meta.app_label
        model_name = model._meta.model_name
        perm = f'{app_label}.view_{model_name}'
        if request.user.has_perm(perm):
            allowed_tables.append(model._meta.db_table)
    preset_query_id = request.GET.get('preset_query_id')
    if preset_query_id:
        sql_query = SAFE_PRESET_QUERIES.get(preset_query_id)
        if not sql_query:
            error_message = "Недопустимый идентификатор готового запроса."
            logger.warning(f"Пользователь {request.user.username} передал недопустимый preset_query_id: {preset_query_id}")
        else:
            if not sql_query.lower().startswith('select'):
                error_message = "Готовый запрос не является SELECT-запросом."
                logger.error(f"Готовый запрос с ID {preset_query_id} не является SELECT-запросом.")
            else:
                tables_in_query = set()
                pattern = r'(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
                matches = re.findall(pattern, sql_query, re.IGNORECASE)
                tables_in_query.update([m.lower() for m in matches])
                forbidden_tables = [t for t in tables_in_query if t not in allowed_tables]
                if forbidden_tables:
                    error_message = f"Готовый запрос использует запрещённые таблицы: {', '.join(forbidden_tables)}"
                    logger.warning(f"Готовый запрос с ID {preset_query_id} использует запрещённые таблицы: {forbidden_tables}")
                else:
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(sql_query)
                            result_columns = [col[0] for col in cursor.description]
                            result_rows = cursor.fetchall()
                        query_executed = True
                        success_message = "Готовый запрос выполнен успешно."
                    except Exception as e:
                        error_message = f"Ошибка выполнения готового запроса: {e}"
                        logger.error(f"Ошибка выполнения готового запроса с ID {preset_query_id} пользователем {request.user.username}: {e}")
    if request.method == 'POST':
        action = request.POST.get('action')
        sql_query = request.POST.get('sql_query', '').strip()
        if not sql_query:
            error_message = "Поле запроса не может быть пустым."
        elif len(sql_query) > 2000:
            error_message = "Запрос слишком длинный."
        elif action == 'execute_query':
            if not sql_query.lower().startswith('select'):
                error_message = "Разрешены только запросы SELECT."
            else:
                tables_in_query = set()
                pattern = r'(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
                matches = re.findall(pattern, sql_query, re.IGNORECASE)
                tables_in_query.update([m.lower() for m in matches])
                forbidden_tables = [t for t in tables_in_query if t not in allowed_tables]
                if forbidden_tables:
                    error_message = f"Запрос использует запрещённые таблицы: {', '.join(forbidden_tables)}"
                    logger.warning(f"Пользователь {request.user.username} пытался использовать запрещённые таблицы: {forbidden_tables}")
                else:
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(sql_query)
                            result_columns = [col[0] for col in cursor.description]
                            result_rows = cursor.fetchall()
                        query_executed = True
                        success_message = "Запрос выполнен успешно."
                    except Exception as e:
                        error_message = f"Ошибка выполнения запроса: {e}"
                        logger.error(f"Ошибка выполнения SQL-запроса пользователем {request.user.username}: {e}")
    return render(request, 'manual_query.html', {
        'sql_query': sql_query,
        'preset_query_id': preset_query_id,
        'result_columns': result_columns,
        'result_rows': result_rows,
        'error_message': error_message,
        'success_message': success_message,
        'query_executed': query_executed,
    })
@login_required
def generate_pdf_file(request):
    if request.method != 'POST':
        logger.warning(f"Пользователь {request.user.username} попытался вызвать generate_pdf_file с методом {request.method}")
        return HttpResponse("Метод не разрешён", status=405)
    sql_query = request.POST.get('sql_query', '').strip()
    if not sql_query:
        messages.error(request, "Пустой SQL-запрос.")
        logger.warning(f"Пользователь {request.user.username} передал пустой SQL-запрос для экспорта в PDF.")
        return redirect('manual_query')
    elif len(sql_query) > 2000:
        messages.error(request, "SQL-запрос слишком длинный.")
        logger.warning(f"Пользователь {request.user.username} передал слишком длинный SQL-запрос для экспорта в PDF.")
        return redirect('manual_query')
    if not sql_query.lower().startswith('select'):
        messages.error(request, "Разрешены только запросы SELECT для экспорта.")
        logger.warning(f"Пользователь {request.user.username} передал не-SELECT запрос для экспорта в PDF: {sql_query[:50]}...")
        return redirect('manual_query')
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            result_columns = [col[0] for col in cursor.description]
            result_rows = cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка выполнения SQL-запроса для экспорта в PDF пользователем {request.user.username}: {e}")
        messages.error(request, f"Ошибка выполнения запроса для экспорта: {e}")
        return redirect('manual_query')
    if not result_columns and not result_rows:
        messages.warning(request, "Нет данных для экспорта в PDF.")
        logger.info(f"Пользователь {request.user.username} запросил PDF для пустого результата.")
        return redirect('manual_query')
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans.ttf')
    try:
        pdfmetrics.registerFont(TTFont('DejaVu', font_path))
        font_registered = True
    except Exception as e_font:
        logger.error(f"Ошибка регистрации шрифта DejaVuSans для PDF пользователем {request.user.username}: {e_font}")
        font_registered = False
    timestamp = datetime.now().strftime("%d.%m.%Y %H.%M.%S")
    filename = f"document_{timestamp}.pdf"
    documents_dir = os.path.join(settings.BASE_DIR, 'documents')
    os.makedirs(documents_dir, exist_ok=True)
    filepath = os.path.join(documents_dir, filename)
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    elements = []
    table_data = [result_columns]
    for row in result_rows:
        formatted_row = [str(cell) if cell is not None else '' for cell in row]
        table_data.append(formatted_row)
    table = Table(table_data)
    style_commands = [
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]
    if font_registered:
        style_commands.extend([
            ('FONTNAME', (0, 0), (-1, 0), 'DejaVu'),
            ('FONTNAME', (0, 1), (-1, -1), 'DejaVu'),
        ])
    else:
        style_commands.extend([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ])
    table_style = TableStyle(style_commands)
    table.setStyle(table_style)
    elements.append(table)
    try:
        doc.build(elements)
        logger.info(f"PDF-файл '{filename}' успешно создан в папке 'documents' пользователем {request.user.username}.")
    except Exception as e_build:
        logger.error(f"Ошибка при генерации PDF-файла '{filename}' пользователем {request.user.username}: {e_build}")
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                logger.warning(f"Не удалось удалить частично созданный файл '{filename}'.")
        messages.error(request, f"Ошибка при создании PDF-файла: {e_build}")
        return redirect('manual_query')
    messages.success(request, f'PDF-файл "{filename}" успешно создан в папке "documents".')
    return redirect('manual_query')
def help_index(request):
    help_topics = [
        {'name': 'about', 'title': 'О программе', 'url': 'about'},
    ]
    return render(request, 'help_index.html', {'topics': help_topics})
def about_view(request):
    return render(request, 'about.html')
@login_required
def help_contents(request):
    return render(request, 'help_contents.html',)
@login_required
def miscellaneous_menu_view(request):
    return render(request, 'miscellaneous_menu.html')
@login_required
def settings_page(request):
    return render(request, 'settings.html')
@login_required
def reference_list(request):
    all_models = apps.get_models()
    core_models = [model for model in all_models if model._meta.app_label == 'core']
    reference_models = []
    for model in core_models:
        perm = f'{model._meta.app_label}.view_{model._meta.model_name}'
        if request.user.has_perm(perm):
            has_fk = any(
                field.is_relation and field.many_to_one
                for field in model._meta.get_fields()
            )
            is_referenced = any(
                field.related_model == model and field.many_to_one
                for other_model in core_models
                for field in other_model._meta.get_fields()
                if field.is_relation
            )
            if not has_fk or (has_fk and not is_referenced):
                reference_models.append((model, model._meta.model_name, model._meta.verbose_name_plural))
    return render(request, 'reference_list.html', {'reference_models': reference_models})
@login_required
def update_settings(request):
    if request.method == 'POST':
        font_size = request.POST.get('font_size')
        if font_size in ['small', 'normal', 'large']:
            request.session['preferred_font_size'] = font_size
        music_enabled = request.POST.get('music_enabled') == 'on'
        request.session['music_enabled'] = music_enabled
    return redirect(request.META.get('HTTP_REFERER', 'main_menu'))