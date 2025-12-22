from django.urls import path

from accommodation import views

urlpatterns = [
    path('', views.accommodation_view, name='accommodation'),
    path('add', views.accommodation_add, name='accommodation_add'),
    path('<int:pk>', views.accommodation_edit, name='accommodation_edit'),
    path('api/accommodations/', views.get_accommodations, name='get_accommodations'),
    path('delete/<int:pk>/', views.accommodation_delete, name='accommodation_delete'),
    path('image/delete/<int:pk>/', views.accommodation_image_delete, name='accommodation_image_delete'),

]
