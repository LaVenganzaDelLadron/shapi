from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('auth.urls')),
    path('pen/', include('pen.urls')),
    path('growth/', include('growth.urls')),
    path('batch/', include('batch.urls')),
    path('device/', include('device.urls')),
    path('feeding/', include('feeding.urls')),
    path('record/', include('record.urls')),
    path('datamining/', include('datamining.urls')),
    path('dashboard/', include('dashboard.urls')),
]
