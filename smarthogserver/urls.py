from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('auth.urls')),
    path('batch/', include('batch.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('device/', include('device.urls')),
    path('feeding/', include('feeding.urls')),
    path('growth/', include('growth.urls')),
    path('pen/', include('pen.urls')),
    path('record/', include('record.urls')),
    # Keep legacy routes and expose the API-prefixed paths used by the client/tests.
    path('datamining/', include('datamining.urls')),
    path('api/datamining/', include('datamining.urls')),
    path('api/dashboard/', include('dashboard.urls')),
]
