from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(success_url='/menu/'), name='password_change'),
    path('menu/', views.main_menu, name='main_menu'),
    path('analytics/', views.analytics_select, name='analytics_select'),  # Выбор типа
    path('analytics/generate/', views.analytics_generate, name='analytics_generate'),
    path('miscellaneous/', views.miscellaneous_menu_view, name='miscellaneous_menu'),
    path('update-settings/', views.update_settings, name='update_settings'),
    path('reference-list/', views.reference_list, name='reference_list'),
    path('settings/', views.settings_page, name='settings_page'),
    path('help/', views.help_index, name='help_index'),
    path('help/about/', views.about_view, name='about'),
    path('help/contents/', views.help_contents, name='help_contents'),
    path('manual-query/', views.manual_query_view, name='manual_query'),
    path('manual-query/generate-pdf/', views.generate_pdf_file, name='generate_pdf_file'),
    path('tables/', views.model_list, name='model_list'),
    path('<str:model_name>/view/<int:pk>/', views.model_view, name='model_view'),
    path('<str:model_name>/', views.model_detail, name='model_detail'),
    path('<str:model_name>/edit/', views.model_edit, name='model_create'),
    path('<str:model_name>/edit/<int:pk>/', views.model_edit, name='model_edit'),
    path('<str:model_name>/delete/<int:pk>/', views.model_delete, name='model_delete'),
]