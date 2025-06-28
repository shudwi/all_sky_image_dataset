from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    #path('admin/process_tar/<int:tar_id>/', views.process_tar_view, name='process_tar'),
    #path('', views.gallery_by_date, name='gallery'),
    #path('<str:date>/', views.gallery_by_date, name='gallery_by_date'),
    path('preview/<int:image_id>/', views.preview_image_view, name='preview_image'),
    path('gallery/<int:year>/', views.year_view, name='year_view'),
    path('gallery/<int:year>/<int:month>/', views.month_view, name='month_view'),
    path('gallery/<int:year>/<int:month>/<int:day>/', views.day_gallery, name='day_gallery'),
]