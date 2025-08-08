from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # We'll create this view
    path('user_panel/', views.user_panel, name='user_panel'),  # Add this line

]

