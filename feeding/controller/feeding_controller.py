import json
from json import JSONDecodeError
from rest_framework import status
from rest_framework.exceptions import UnsupportedMediaType
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from feeding.models import Feeding
from feeding.serializers import FeedingSerializer


class FeedingController(APIView):
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
                    status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                )
        payload = dict(payload)
        if 'batch_code' not in payload and 'batch_code_id' in payload:
            payload['batch_code'] = payload.pop('batch_code_id')
        if 'device_code' not in payload and 'device_code_id' in payload:
            payload['device_code'] = payload.pop('device_code_id')
        if 'pen_code' not in payload and 'pen_code_id' in payload:
            payload['pen_code'] = payload.pop('pen_code_id')
        if 'repeat_days' not in payload:
            payload['repeat_days'] = None
        if 'date' not in payload and 'feed_time' in payload:
            payload['date'] = payload['feed_time']

        serializer = FeedingSerializer(data=payload)
        if serializer.is_valid():
            feeding = serializer.save()
            return Response(
                {
                    "message": "Feeding record created",
                    "feeding": feeding.feed_code,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetFeedingController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_all_feedings(self):
        feedings = Feeding.objects.all().order_by('feed_code')
        return FeedingSerializer(feedings, many=True).data

    def get(self, request):
        data = self.get_all_feedings()
        return Response(
            {
                'message': 'Feeding records fetched successfully',
                'count': len(data),
                'data': data,
            },
            status=status.HTTP_200_OK,
        )


class DeleteFeedingController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def delete(self, request, feed_code):
        feeding = Feeding.objects.filter(feed_code=feed_code).first()
        if not feeding:
            return Response(
                {
                    "message": f'Feeding record "{feed_code}" not found',
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        feeding.delete()
        return Response(
            {
                "message": f'Feeding record "{feed_code}" deleted',
            },
            status=status.HTTP_200_OK,
        )


class UpdateFeedingController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def put(self, request, feed_code):
        feeding = Feeding.objects.filter(feed_code=feed_code).first()
        if not feeding:
            return Response(
                {
                    "message": f'Feeding record "{feed_code}" not found',
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        payload = dict(request.data)
        if 'batch_code' not in payload and 'batch_code_id' in payload:
            payload['batch_code'] = payload.pop('batch_code_id')
        if 'device_code' not in payload and 'device_code_id' in payload:
            payload['device_code'] = payload.pop('device_code_id')
        if 'pen_code' not in payload and 'pen_code_id' in payload:
            payload['pen_code'] = payload.pop('pen_code_id')

        serializer = FeedingSerializer(feeding, data=payload)
        if serializer.is_valid():
            updated_feeding = serializer.save()
            return Response(
                {
                    'message': f'Feeding record "{feed_code}" updated successfully',
                    'data': FeedingSerializer(updated_feeding).data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, feed_code):
        feeding = Feeding.objects.filter(feed_code=feed_code).first()
        if not feeding:
            return Response(
                {
                    "message": f'Feeding record "{feed_code}" not found',
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        payload = dict(request.data)
        if 'batch_code' not in payload and 'batch_code_id' in payload:
            payload['batch_code'] = payload.pop('batch_code_id')
        if 'device_code' not in payload and 'device_code_id' in payload:
            payload['device_code'] = payload.pop('device_code_id')
        if 'pen_code' not in payload and 'pen_code_id' in payload:
            payload['pen_code'] = payload.pop('pen_code_id')

        serializer = FeedingSerializer(feeding, data=payload, partial=True)
        if serializer.is_valid():
            updated_feeding = serializer.save()
            return Response(
                {
                    'message': f'Feeding record "{feed_code}" updated successfully',
                    'data': FeedingSerializer(updated_feeding).data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
