from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import EmailAuthenticationForm

urlpatterns = [
    path('', views.home, name='home'),

    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='fergusonbequest/login.html',authentication_form=EmailAuthenticationForm), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('how-to-book/', views.terms, name='how_to_book'),

]
