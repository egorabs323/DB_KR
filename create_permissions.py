import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

import django
from django.conf import settings

django.setup()

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps

app_models = apps.get_app_config('core').get_models()

for model in app_models:
    content_type = ContentType.objects.get_for_model(model)
    permissions = [
        ('add_' + model._meta.model_name, f'Can add {model._meta.verbose_name}'),
        ('change_' + model._meta.model_name, f'Can change {model._meta.verbose_name}'),
        ('delete_' + model._meta.model_name, f'Can delete {model._meta.verbose_name}'),
        ('view_' + model._meta.model_name, f'Can view {model._meta.verbose_name}'),
    ]
    for codename, name in permissions:
        Permission.objects.get_or_create(
            codename=codename,
            name=name,
            content_type=content_type,
        )

print("core успешно созданы!")