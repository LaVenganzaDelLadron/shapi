import json
from json import JSONDecodeError
from rest_framework import status
from rest_framework.exceptions import UnsupportedMediaType
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from record.models import Record
from record.serializers import RecordSerializer


class RecordController(APIView):
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
        if 'growth_stage' not in payload and 'growth_stage_id' in payload:
            payload['growth_stage'] = payload.pop('growth_stage_id')

        serializer = RecordSerializer(data=payload)
        if serializer.is_valid():
            record = serializer.save()
            return Response(
                {
                    "message": "Record created",
                    "record": record.record_code,
                },
                status=status.HTTP_201_CREATED,
            )
        if serializer.errors.get('message') == ['A daily snapshot already exists for this batch on this UTC day.']:
            return Response(
                {'message': 'A daily snapshot already exists for this batch on this UTC day.'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetRecordController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_all_records(self):
        records = Record.objects.select_related('batch_code', 'growth_stage').order_by(
            'batch_code__batch_code',
            'date',
            'record_code',
        )
        return RecordSerializer(records, many=True).data

    def get(self, request):
        data = self.get_all_records()
        return Response(
            {
                'message': 'Records fetched successfully',
                'count': len(data),
                'data': data,
            },
            status=status.HTTP_200_OK,
        )


class DeleteRecordController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def delete(self, request, record_code):
        record = Record.objects.filter(record_code=record_code).first()
        if not record:
            return Response(
                {
                    "message": f'Record "{record_code}" not found',
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        record.delete()
        return Response(
            {
                "message": f'Record "{record_code}" deleted',
            },
            status=status.HTTP_200_OK,
        )


class UpdateRecordController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def put(self, request, record_code):
        return Response(
            {
                'message': 'Historical records are immutable. Create a new snapshot instead.',
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def patch(self, request, record_code):
        return Response(
            {
                'message': 'Historical records are immutable. Create a new snapshot instead.',
            },
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
