from django.urls import path
from .controller.pen_controller import (
    PenController,
    GetPenController,
    DeletePenController,
    UpdatePenController,
)

urlpatterns = [
    path('add/', PenController.as_view(), name='addPen'),
    path('all/', GetPenController.as_view(), name='getAllPens'),
    path('delete/<str:pen_code>/', DeletePenController.as_view(), name='deletePenCode'),
    path('update/<str:pen_code>/', UpdatePenController.as_view(), name='updatePenCode'),
]
