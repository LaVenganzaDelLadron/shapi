from django.urls import path

from .controller.record_controller import (
    RecordController,
    GetRecordController,
    DeleteRecordController,
    UpdateRecordController,
)

urlpatterns = [
    path('add/', RecordController.as_view(), name='addRecord'),
    path('all/', GetRecordController.as_view(), name='getAllRecords'),
    path('delete/<str:record_code>/', DeleteRecordController.as_view(), name='deleteRecord'),
    path('update/<str:record_code>/', UpdateRecordController.as_view(), name='updateRecord'),
]
