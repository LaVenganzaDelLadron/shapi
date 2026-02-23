from django.urls import path

from .controller.pig_batches_controlller import (
    PigBatchesController,
    GetPigBatchesController,
    DeletePigBatchesController,
    UpdatePigBatchesController,
)

urlpatterns = [
    path('add/', PigBatchesController.as_view(), name='addBatch'),
    path('all/', GetPigBatchesController.as_view(), name='getAllBatches'),
    path('delete/<str:batch_code>/', DeletePigBatchesController.as_view(), name='deleteBatch'),
    path('update/<str:batch_code>/', UpdatePigBatchesController.as_view(), name='updateBatch'),
]



