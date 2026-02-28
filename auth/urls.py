from django.urls import path
from .controllers.auth_controller import LoginController, LogoutController, SignupController, CSRFTokenView

urlpatterns = [
    path('signup/', SignupController.as_view(), name='signup'),
    path('login/', LoginController.as_view(), name='login'),
    path('csrf/',CSRFTokenView.as_view(), name='csrf'),
    path('logout/', LogoutController.as_view(), name='logout'),
]
