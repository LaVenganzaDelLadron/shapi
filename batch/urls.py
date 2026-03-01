from django.urls import path

from .controller.pig_batches_controlller import (
    PigBatchesController,
    GetPigBatchesController,
    DeletePigBatchesController,
    UpdatePigBatchesController,
    GetTotalPigController,
    GetActiveBatchesController,
)

urlpatterns = [
    path('add/', PigBatchesController.as_view(), name='addBatch'),
    path('all/', GetPigBatchesController.as_view(), name='getAllBatches'),
    path('total-pigs/', GetTotalPigController.as_view(), name='getTotalPigs'),
    path('active/', GetActiveBatchesController.as_view(), name='getActiveBatches'),
    path('delete/<str:batch_code>/', DeletePigBatchesController.as_view(), name='deleteBatch'),
    path('update/<str:batch_code>/', UpdatePigBatchesController.as_view(), name='updateBatch'),
]


