from django.forms import ModelForm
from django.apps import apps

class DynamicModelForm:
    def __new__(cls, model_class, *args, **kwargs):
        class Meta:
            model = model_class
            fields = '__all__'

        form_class = type(
            f'{model_class.__name__}Form',
            (ModelForm,),
            {
                'Meta': Meta
            }
        )
        return form_class(*args, **kwargs)