from django.urls import path
from .controllers.auth_controller import LoginController, LogoutController, SignupController


urlpatterns = [
    path('signup/', SignupController.as_view(), name='signup'),
    path('login/', LoginController.as_view(), name='login'),
    path('logout/', LogoutController.as_view(), name='logout'),
]
