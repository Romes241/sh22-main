from django.urls import path
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
    path("terms-and-conditions/", views.terms, name="terms_and_conditions"),

    # Ticket draws
    path("ticket-draws/", views.ticket_draws_view, name="ticket_draws"),
    path("ticket-draws/<slug:slug>/", views.ticket_draw_detail, name="ticket_draw_detail"),
    path("ticket-draw-entry/<int:pk>/cancel/", views.cancel_ticket_draw_entry, name="cancel_ticket_draw_entry"),

    # Waiting list (draw)
    path("draw-waiting-list/", views.draw_waiting_list, name="draw_waiting_list"),
    path("draw-waiting-list/cancel/<int:pk>/", views.cancel_ticket_draw_entry, name="cancel_draw_entry"),
    path("draw/accept/<int:pk>/", views.accept_draw_win, name="accept_draw_win"),
    path("draw/decline/<int:pk>/", views.decline_draw_win, name="decline_draw_win"),

    # Attractions + bookings
    path("attraction/<int:pk>/", views.attraction, name="attraction"),
    path("attraction/<int:attraction_pk>/book/", views.booking_view, name="attraction_book"),
    path("attractions/", views.attractions_view, name="attractions"),
    path("booking-history/", views.booking_history, name="booking_history"),
    path("booking/<int:pk>/cancel/", views.cancel_booking, name="cancel_booking"),
    path("booking/<int:booking_id>/feedback/", views.submit_booking_feedback, name="submit_booking_feedback"),

    # Waiting list (attraction-specific)
    path("waiting-list-attraction/", views.waiting_listattraction, name="waiting_listattraction"),
    path("waiting-list-attraction/join/<int:pk>/", views.waiting_listattraction_join, name="waiting_listattraction_join"),
    path("waiting-list-attraction/leave/<int:pk>/", views.waiting_listattraction_leave, name="waiting_listattraction_leave"),

    # Admin dashboard
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-dashboard/<int:year>/<int:month>/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-dashboard/management/", views.admin_management, name="admin_management"),
    path("admin-dashboard/management/draw/<int:draw_id>/run/", views.run_draw, name="run_draw"),
    path("admin-dashboard/management/draws/<int:draw_id>/delete/", views.mng_delete_draw, name="mng_delete_draw"),
    path("admin-dashboard/management/attractions/<int:attraction_id>/delete/", views.mng_delete_attraction, name="mng_delete_attraction"),
    path("admin-reports/", views.admin_reports, name="admin_reports"),
    path("admin-feedback-submissions/", views.admin_feedback_submissions, name="admin_feedback_submissions"),
    path("admin-email/", views.admin_email, name="admin_email"),
    path("admin-terms-and-conditions/", views.manage_terms_and_conditions, name="manage_terms_and_conditions"),
    path("admin-main-page-content/", views.manage_main_page_content, name="manage_main_page_content"),

    # Admin create/edit
    path("manage-feedback-email/", views.manage_feedback_email, name="manage_feedback_email"),
    path("manage-feedback-email/send-now/", views.trigger_feedback_emails, name="trigger_feedback_emails"),
    path("create-attraction/", views.create_attraction, name="create_attraction"),
    path("edit-attraction/<int:pk>/", views.edit_attraction, name="edit_attraction"),

    path("create-ticket-draw/", views.create_ticket_draw, name="create_ticket_draw"),
    path("edit-ticket-draw/<int:pk>/", views.edit_ticket_draw, name="edit_ticket_draw"),

    # Suggestions export
    path("suggestions/", views.create_attraction_suggestion, name="create_attraction_suggestion"),
    path("admin-export/suggestions.xlsx", views.export_suggestions_excel, name="export_suggestions_excel"),
    path("waiting-list-attraction/", views.waiting_listattraction, name="waiting_listattraction"),
    path("waiting-list-attraction/join/<int:pk>/", views.waiting_listattraction_join, name="waiting_listattraction_join"),
    path("waiting-list-attraction/leave/<int:pk>/", views.waiting_listattraction_leave, name="waiting_listattraction_leave"),

    # Discount codes - admin management
    path("staff/discounts/", views.discount_codes_page, name="discount_codes"),
    path("staff/discounts/<int:pk>/edit/", views.discount_code_edit, name="discount_code_edit"),
    path("staff/discounts/<int:pk>/toggle/", views.discount_code_toggle, name="discount_code_toggle"),
    path("staff/discounts/<int:pk>/delete/", views.discount_code_delete, name="discount_code_delete"),

    # Discount codes - user-facing page
    path("discounts/", views.user_discount_codes, name="user_discount_codes"),

    # Ticket upload mechanism
    path("ticket-upload/", views.ticket_upload, name="ticket_upload"),
    path("ticket-upload/view-all/", views.ticket_upload_view_all, name="ticket_upload_view_all"),
    path("ticket-upload/send/", views.ticket_upload_send, name="ticket_upload_send"),
    path('ticket-upload/venue-distribute/', views.venue_distribute_tickets, name='venue_distribute_tickets'),
    path("ticket-upload/individual/", views.individual_booking, name="individual_booking"),
    path("ticket-upload/view/<str:booking_id>/", views.ticket_view, name="ticket_view"),
    path("my-ticket/<str:booking_id>/", views.user_ticket_view, name="user_ticket_view"),
    path("tickets/<str:booking_id>/list/", views.ticket_list, name="ticket_list"),
    path("ticket-upload/delete/", views.ticket_upload_delete, name="ticket_upload_delete"),
    path("ticket-upload/bulk-delete/", views.ticket_upload_bulk_delete, name="ticket_upload_bulk_delete"),
]