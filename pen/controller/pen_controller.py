from rest_framework import status
from rest_framework.exceptions import UnsupportedMediaType
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from pen.models import Pen
import json
from json import JSONDecodeError
from pen.serializers import PenSerializer


class PenController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request):
        try:
            payload = request.data
        except UnsupportedMediaType:
            try:
                payload = json.loads(request.body.decode("utf-8"))
            except (UnicodeDecodeError, JSONDecodeError):
                return Response(
                    {
                        "message": "Unsupported media type. Send JSON with Content-Type: application/json."
                    },
                    status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                )

        serializer = PenSerializer(data=payload)
        if serializer.is_valid():
            pen = serializer.save()
            return Response(
                {
                    'message': "Pen Successfully Created",
                    'pen_code': pen.pen_code,
                    'pen_name': pen.pen_name,
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetPenController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_all_pens(self):
        pens = Pen.objects.all().order_by('pen_code')
        return PenSerializer(pens, many=True).data

    def get(self, request):
        data = self.get_all_pens()
        return Response(
            {
                'message': 'Pens fetched successfully',
                'count': len(data),
                'data': data,
            },
            status=status.HTTP_200_OK,
        )

class DeletePenController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def delete(self, request, pen_code):
        pen = Pen.objects.filter(pen_code=pen_code).first()
        if not pen:
            return Response(
                {'message': f'Pen with pen_code "{pen_code}" not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        pen.delete()
        return Response(
            {'message': f'Pen "{pen_code}" deleted successfully'},
            status=status.HTTP_200_OK,
        )

class UpdatePenController(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def put(self, request, pen_code):
        pen = Pen.objects.filter(pen_code=pen_code).first()
        if not pen:
            return Response(
                {'message': f'Pen with pen_code "{pen_code}" not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PenSerializer(pen, data=request.data)
        if serializer.is_valid():
            updated_pen = serializer.save()
            return Response(
                {
                    'message': f'Pen "{pen_code}" updated successfully',
                    'data': PenSerializer(updated_pen).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pen_code):
        pen = Pen.objects.filter(pen_code=pen_code).first()
        if not pen:
            return Response(
                {'message': f'Pen with pen_code "{pen_code}" not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PenSerializer(pen, data=request.data, partial=True)
        if serializer.is_valid():
            updated_pen = serializer.save()
            return Response(
                {
                    'message': f'Pen "{pen_code}" updated successfully',
                    'data': PenSerializer(updated_pen).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
