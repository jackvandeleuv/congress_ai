from django.urls import path
from congressgpt import views

urlpatterns = [
    path('csrf', views.get_csrf_token, name='get_csrf_token'),
    path('ask', views.ask_congressgpt, name='ask'),
    path('search', views.search_congressgpt, name='search'),
    path('get_history', views.get_history_congressgpt, name='get_history'),
    path('get_historybar', views.get_historybar_congressgpt, name='get_historybar'),
]