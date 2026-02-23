from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from auth.serializers import SignupSerializer, LoginSerializer


class SignupView(APIView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "message": "Signup Successfully",
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user_obj = User.objects.filter(Q(email__iexact=email)).first()
        if not user_obj:
            return Response(
                {"message": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = authenticate(request, username=user_obj.username, password=password)
        if not user:
            return Response(
                {"message": "Invalid email or password"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {
                "message": "Login Successfully",
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
            },
            status=status.HTTP_200_OK,
        )
