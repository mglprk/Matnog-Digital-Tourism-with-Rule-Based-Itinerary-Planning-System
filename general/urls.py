from django.urls import path
from . import views

app_name = 'general'

urlpatterns = [
    path('announcement/', views.announcement_view, name='announcement'),
    path('announcements/add', views.announcement_add, name='announcement_add'),
    path('announcements/<int:pk>', views.announcement_edit, name='announcement_edit'),
    path('announcements/api/announcements/', views.get_announcements, name='get_announcements'),
    path('announcements/delete/<int:pk>/', views.announcement_delete, name='announcement_delete'),


]

