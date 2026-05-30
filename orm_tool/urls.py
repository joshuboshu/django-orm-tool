from django.urls import path
from . import views

app_name = 'orm_tool'

urlpatterns = [
    path('', views.index, name='index'),
    path('execute/', views.execute, name='execute'),
]
