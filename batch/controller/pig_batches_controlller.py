import json
from json import JSONDecodeError

from rest_framework import status
from rest_framework.exceptions import UnsupportedMediaType
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from batch.models import PigBatches
from batch.serializers import PigBatchesSerializer

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
        serializer = PigBatchesSerializer(data=payload)
        if serializer.is_valid():
            pig_batches = serializer.save()
            return Response(
                {
                    "message": "PigBatches successfully created",
                    "batch": pig_batches.id,
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GetPigBatchesController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_all_pig_batches(self):
        pig_batches = PigBatches.objects.all()
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
            {'message': 'PigBatches deleted successfully'},
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
                    "message": "PigBatches not found for batch code {}".format(batch_code)
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PigBatchesSerializer(pig_batches, data=request.data)
        if serializer.is_valid():
            update_pig_batches = serializer.save()
            return Response(
                {
                    'message': 'PigBatches successfully updated',
                    'data': PigBatchesSerializer(update_pig_batches).data,
                },
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request, batch_code):
        pig_batches = PigBatches.objects.filter(batch_code=batch_code).first()
        if not pig_batches:
            return Response(
                {
                    "message": "PigBatches not found for batch code {}".format(batch_code)
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PigBatchesSerializer(pig_batches, data=request.data, partial=True)
        if serializer.is_valid():
            update_pig_batches = serializer.save()
            return Response(
                {
                    'message': f'PigBatches {batch_code} successfully updated',
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)








