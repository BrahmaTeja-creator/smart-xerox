# smartprint/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views # Needed for LoginView
from . import views # Import your app's views

urlpatterns = [
    # Homepage
    path('', views.home, name='home'),

    # User Panel
    path('user_panel/', views.user_panel, name='user_panel'),

    # Admin Dashboard
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'), # <-- ENSURE THIS LINE IS PRESENT AND CORRECT

    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='smartprint/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    # Admin Actions (Approve/Reject Order)
    path('approve_order/<int:order_id>/', views.approve_order, name='approve_order'),
    path('reject_order/<int:order_id>/', views.reject_order, name='reject_order'),

    # Admin Action (Print Specific Job Item)
    path('print/<int:order_id>/<int:item_id>/', views.print_job_document, name='print_job_document'),

    # AJAX for dynamic cost calculation
    path('calculate_cost_ajax/', views.calculate_cost_ajax, name='calculate_cost_ajax'),
    # smartprint/urls.py
# ... (existing imports and urlpatterns) ...

    path('get_page_count_ajax/', views.get_page_count_ajax, name='get_page_count_ajax'), # Add this line
]