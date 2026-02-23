from django.urls import path
from .controller.device_controller import (
    DeviceController,
    GetDeviceController,
    DeleteDeviceController, UpdateDeviceController
)

urlpatterns = [
    path('add/', DeviceController.as_view(), name='add'),
    path('all/', GetDeviceController.as_view(), name='get'),
    path('delete/<str:device_code>/', DeleteDeviceController.as_view(), name='delete'),
    path('update/<str:device_code>/', UpdateDeviceController.as_view(), name='delete'),
]


