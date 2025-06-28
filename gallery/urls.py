from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    #path('admin/process_tar/<int:tar_id>/', views.process_tar_view, name='process_tar'),
    #path('', views.gallery_by_date, name='gallery'),
    #path('<str:date>/', views.gallery_by_date, name='gallery_by_date'),
    # path('gallery/async-ingest/<int:tar_id>/', views.async_ingest_tar, name='async_ingest_tar'),
    # path('gallery/async-status/<int:tar_id>/', views.get_tar_status, name='async_tar_status'),
    # path('gallery/stop-ingest/<int:tar_id>/', views.stop_tar_process, name='stop_tar_process'),
    path('gallery/async-ingest/<int:tar_id>/', views.async_ingest_view, name='async_ingest'),
    path('gallery/async-status/<int:tar_id>/', views.async_status_view, name='async_status'),
    path('gallery/stop-ingest/<int:tar_id>/', views.stop_ingest_view, name='stop_ingest'),
    path('preview/<int:image_id>/', views.preview_image_view, name='preview_image'),
    path('gallery/<int:year>/', views.year_view, name='year_view'),
    path('gallery/<int:year>/<int:month>/', views.month_view, name='month_view'),
    path('gallery/<int:year>/<int:month>/<int:day>/', views.day_gallery, name='day_gallery'),
]