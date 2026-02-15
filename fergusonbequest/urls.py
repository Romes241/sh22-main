from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import EmailAuthenticationForm

urlpatterns = [
    path("", views.home, name="home"),

    # Auth
    path("register/", views.register_view, name="register"),
    path(
        "login/",
        views.CustomLoginView.as_view(
            template_name="fergusonbequest/login.html",
            authentication_form=EmailAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", views.logout_view, name="logout"),

    # User pages
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("dashboard/<int:year>/<int:month>/", views.dashboard_view, name="dashboard"),
    path("how-to-book/", views.terms, name="how_to_book"),

    # Ticket draws
    path("ticket-draws/", views.ticket_draws_view, name="ticket_draws"),
    path("ticket-draws/<slug:slug>/", views.ticket_draw_detail, name="ticket_draw_detail"),
    path("ticket-draw-entry/<int:pk>/cancel/", views.cancel_ticket_draw_entry, name="cancel_ticket_draw_entry"),

    # Attractions + bookings
    path("attraction/<int:pk>/", views.attraction, name="attraction"),
    path("attraction/<int:attraction_pk>/book/", views.booking_view, name="attraction_book"),
    path("attractions/", views.attractions_view, name="attractions"),
    path("booking-history/", views.booking_history, name="booking_history"),
    path("booking/<int:pk>/cancel/", views.cancel_booking, name="cancel_booking"),

    # Waiting list (general draw waiting list)
    path("waiting-list/", views.waiting_list, name="waiting_list"),
    path("waiting-list/cancel/<int:pk>/", views.cancel_ticket_draw_entry, name="cancel_draw_entry"),
    path("waiting-list/accept/<int:pk>/", views.accept_draw_win, name="accept_draw_win"),
    path("waiting-list/decline/<int:pk>/", views.decline_draw_win, name="decline_draw_win"),

    # (If you still use draw-waiting-list URLs elsewhere, keep ONE copy)
    path("draw-waiting-list/", views.draw_waiting_list, name="draw_waiting_list"),
    path("draw-waiting-list/cancel/<int:pk>/", views.cancel_ticket_draw_entry, name="cancel_draw_entry"),

    # Waiting list (attraction-specific)
    path("waiting-list-attraction/", views.waiting_listattraction, name="waiting_listattraction"),
    path("waiting-list-attraction/join/<int:pk>/", views.waiting_listattraction_join, name="waiting_listattraction_join"),
    path("waiting-list-attraction/leave/<int:pk>/", views.waiting_listattraction_leave, name="waiting_listattraction_leave"),

    # Calendar
    path("calendar/", views.calendar_view, name="calendar"),
    path("calendar/<int:year>/<int:month>/", views.calendar_view, name="calendar"),

    # Admin dashboard
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-dashboard/management/", views.admin_management, name="admin_management"),
    path("admin-dashboard/management/draw/<int:draw_id>/run/", views.run_draw, name="run_draw"),
    path("admin-dashboard/management/draws/<int:draw_id>/delete/", views.mng_delete_draw, name="mng_delete_draw"),
    path("admin-dashboard/management/attractions/<int:attraction_id>/delete/", views.mng_delete_attraction, name="mng_delete_attraction"),
    path("admin-reports/", views.admin_reports, name="admin_reports"),

    # Admin create/edit
    path("create-attraction/", views.create_attraction, name="create_attraction"),
    path("edit-attraction/<int:pk>/", views.edit_attraction, name="edit_attraction"),
    path("create-ticket-draw/", views.create_ticket_draw, name="create_ticket_draw"),
    path("edit-ticket-draw/<int:pk>/", views.edit_ticket_draw, name="edit_ticket_draw"),

    # Draw accept/decline routes (if still used)
    path("draw/accept/<int:pk>/", views.accept_draw_win, name="accept_draw_win"),
    path("draw/decline/<int:pk>/", views.decline_draw_win, name="decline_draw_win"),

    # Suggestions export
    path("suggestions/", views.create_attraction_suggestion, name="create_attraction_suggestion"),
    path("admin-export/suggestions.xlsx", views.export_suggestions_excel, name="export_suggestions_excel"),

    # Staff tools
    path("staff/draws/", views.staff_draws_entry, name="staff_draws_entry"),
    path("staff/draws/<int:pk>/json/", views.staff_draw_json, name="staff_draw_json"),

    # ✅ NEW: Discount codes staff page
    path("staff/discounts/", views.discount_codes_page, name="discount_codes"),
]

