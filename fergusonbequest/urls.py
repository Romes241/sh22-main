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
    path("ticket-draws/", views.ticket_draws_view, name="ticket_draws"),
    path("ticket-draws/<slug:slug>/", views.ticket_draw_detail, name="ticket_draw_detail"),
    path('attraction/<int:pk>/', views.attraction, name='attraction'),
    path('attraction/<int:attraction_pk>/book/', views.booking_view, name='attraction_book'),
    path('booking-history/', views.booking_history, name='booking_history'),
    path('booking/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('waiting-list/', views.waiting_list, name='waiting_list'),
    path('waiting-list/cancel/<int:pk>/', views.cancel_ticket_draw_entry, name='cancel_draw_entry'),
    path("attractions/", views.attractions_view, name="attractions"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("create-attraction/", views.create_attraction, name="create_attraction"),
    path("edit-attraction/<int:pk>/", views.edit_attraction, name="edit_attraction"),
    path("create-ticket-draw/", views.create_ticket_draw, name="create_ticket_draw"),
    path("edit-ticket-draw/<int:pk>/", views.edit_ticket_draw, name="edit_ticket_draw"),
    path("suggestions/", views.create_attraction_suggestion, name="create_attraction_suggestion"),
    path("admin-export/suggestions.xlsx", views.export_suggestions_excel, name="export_suggestions_excel"),
    path("admin-reports/", views.admin_reports, name = "admin_reports"),
]



