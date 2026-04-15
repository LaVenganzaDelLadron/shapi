import json
from json import JSONDecodeError

from rest_framework import status
from rest_framework.exceptions import UnsupportedMediaType
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from batch.models import PigBatches
from batch.serializers import PigBatchesSerializer


def _normalize_payload(payload):
    if hasattr(payload, 'lists'):
        normalized = {}
        for key, values in payload.lists():
            normalized[key] = values[-1] if values else None
        payload = normalized
    else:
        payload = dict(payload)

    if 'pen_code_id' not in payload and 'pen_code' in payload:
        payload['pen_code_id'] = payload.pop('pen_code')
    if 'growth_stage_id' not in payload and 'growth_stage' in payload:
        payload['growth_stage_id'] = payload.pop('growth_stage')
    return payload


class PigBatchesController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request):
        try:
            payload = request.data
        except UnsupportedMediaType:
            try:
                payload = json.loads(request.body.decode('utf-8'))
            except (UnicodeDecodeError, JSONDecodeError):
                return Response(
                    {
                        "message": "Unsupported media type. Send JSON with Content-Type: application/json."
                    },
                    status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
                )
        payload = _normalize_payload(payload)
        serializer = PigBatchesSerializer(data=payload)
        if serializer.is_valid():
            pig_batches = serializer.save()
            return Response(
                {
                    "message": "Batch created successfully",
                    "data": PigBatchesSerializer(pig_batches).data,
                },
                status=status.HTTP_201_CREATED
            )
        return Response(
            {
                "message": "Batch creation failed",
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

class GetPigBatchesController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_all_pig_batches(self):
        pig_batches = PigBatches.objects.select_related('pen_code', 'growth_stage').order_by('batch_code')
        return PigBatchesSerializer(pig_batches, many=True).data

    def get(self, request):
        data = self.get_all_pig_batches()
        return Response({
            'message': 'Pig Batches fetched successfully',
            'count': len(data),
            'data': data,
        },
            status=status.HTTP_200_OK,
        )

class DeletePigBatchesController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def _delete_batch(self, batch_code):
        pig_batches = PigBatches.objects.filter(batch_code=batch_code).first()
        if not pig_batches:
            return Response(
                {
                    "message": "PigBatches not found for batch code {}".format(batch_code)
                },
                status=status.HTTP_404_NOT_FOUND
            )
        pig_batches.delete()
        return Response(
            {
                'message': f'Batch "{batch_code}" deleted successfully',
                'batch_code': batch_code,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, batch_code):
        return self._delete_batch(batch_code)

    # Alias for browser/manual URL testing.
    def get(self, request, batch_code):
        return self._delete_batch(batch_code)

class UpdatePigBatchesController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def put(self, request, batch_code):
        pig_batches = PigBatches.objects.filter(batch_code=batch_code).first()
        if not pig_batches:
            return Response(
                {
                    "message": "Batch not found for batch code {}".format(batch_code)
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PigBatchesSerializer(pig_batches, data=_normalize_payload(request.data))
        if serializer.is_valid():
            update_pig_batches = serializer.save()
            return Response(
                {
                    'message': f'Batch "{batch_code}" updated successfully',
                    'data': PigBatchesSerializer(update_pig_batches).data,
                },
                status=status.HTTP_200_OK
            )
        return Response(
            {
                'message': f'Batch "{batch_code}" update failed',
                'errors': serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    def patch(self, request, batch_code):
        pig_batches = PigBatches.objects.filter(batch_code=batch_code).first()
        if not pig_batches:
            return Response(
                {
                    "message": "Batch not found for batch code {}".format(batch_code)
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PigBatchesSerializer(
            pig_batches,
            data=_normalize_payload(request.data),
            partial=True,
        )
        if serializer.is_valid():
            update_pig_batches = serializer.save()
            return Response(
                {
                    'message': f'Batch "{batch_code}" updated successfully',
                    'data': PigBatchesSerializer(update_pig_batches).data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                'message': f'Batch "{batch_code}" update failed',
                'errors': serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

class GetTotalPigController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get(self, request):
        total_pigs = PigBatches.objects.aggregate(total=Sum('no_of_pigs'))['total'] or 0
        return Response(
            {
                'message': 'Total pigs fetched successfully',
                'total_pigs': total_pigs,
            },
            status=status.HTTP_200_OK,
        )


class GetActiveBatchesController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get(self, request):
        active_batches = PigBatches.objects.filter(no_of_pigs__gt=0)
        data = PigBatchesSerializer(active_batches, many=True).data
        return Response(
            {
                'message': 'Active pig batches fetched successfully',
                'count': len(data),
                'data': data,
            },
            status=status.HTTP_200_OK,
        )

