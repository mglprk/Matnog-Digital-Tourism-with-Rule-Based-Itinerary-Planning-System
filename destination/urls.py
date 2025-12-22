from django.urls import path

from destination import views
urlpatterns = [
    path('', views.destination_view, name='destination'),
    path('add', views.destination_add, name='destination_add'),
    path('<int:pk>', views.destination_edit, name='destination_edit'),
    path('delete/<int:pk>/', views.destination_delete, name='destination_delete'),
    path('image/delete/<int:pk>/', views.destination_image_delete, name='destination_image_delete'),

]
