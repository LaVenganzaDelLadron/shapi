from django.urls import path
from .controllers.auth_controller import LoginController, SignupController


urlpatterns = [
    path('signup/', SignupController.as_view(), name='signup'),
    path('login/', LoginController.as_view(), name='login'),
]
