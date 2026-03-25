# Customer Handover Document

## 1. System Overview

The Ferguson Bequest System is a web-based platform designed to support:

- attraction bookings
- ticket allocation
- waitlists
- ticket draws
- automated communication with users

It provides:
- a user-facing booking system
- an admin interface for staff management

The purpose of the system is to make the booking and allocation process more efficient, reduce manual admin work, and improve communication with users.

## 2. Key Features

### Booking System
Users can:
- browse available attractions
- book available visit slots
- cancel bookings where allowed by the system rules

### Waitlist System
If an attraction is full, users may:
- join a waitlist
- be offered a place later if space becomes available

### Ticket Delivery
The system supports automated ticket distribution and can send ticket-related communications by email.

### Ticket Draws
Where demand exceeds capacity, the system can:
- accept entries into a draw
- select winners
- manage the allocation process

### Email Notifications
The system can send:
- booking confirmations
- ticket notifications
- reminder emails
- feedback request emails

### Feedback System
The system supports two feedback flows:

- External feedback (user-facing):
	- users receive a feedback request email after a booking workflow
	- they submit responses through a user-facing feedback link/form

- Internal feedback (staff/admin-facing):
	- users submit feedback through the built-in in-app form
	- admins can view submissions in the admin feedback submissions area
	- this supports internal monitoring and follow up

How admins switch mode and configure it:
- go to the feedback email settings page (`Manage Feedback Emails`, or feedback settings in `Admin Email`)
- set `Feedback Collection Mode` to:
	- `Internal` to use the built-in in-app feedback form
	- `External` to use an external Microsoft Forms link
- if `External` is selected, a valid Microsoft Forms URL must be entered before saving

Where each flow is accessed:
- Internal mode:
	- users access feedback from their feedback email link (or booking history when available)
	- admins review submitted feedback in `Admin Feedback Submissions`
- External mode:
	- users are sent to the configured Microsoft Forms URL
	- responses are stored in Microsoft Forms (not the in-app feedback submissions list)

How feedback delivery is controlled:
- feedback request emails depend on the configured email backend/provider
- feedback wording/content depends on configured email templates
- if email is not configured for live delivery, external feedback requests will not reach users

## 3. Admin Capabilities

Administrators can:
- manage attractions and booking content
- view and manage bookings
- manage ticket draws
- manage users and system data
- use the admin interface to support day-to-day operation

Admin access is available through the system’s administrative area.

## 4. How the System Works

In general, the system follows this process:

1. Users browse available attractions
2. Users either make a booking or join a waitlist
3. The system manages availability and allocation
4. Tickets and updates can be distributed automatically
5. Email notifications keep users informed throughout the process

## 5. Requirements

To run the system, the client will need:
- access to a suitable machine or hosting environment
- technical support for setup and maintenance
- a configured email service if live emails are required

The current handover version is best suited to local, internal, or low-scale deployment unless further infrastructure work is carried out.

## 5.1 Operational Dependencies (Important)

In addition to hosting and database setup, the following operational services/configuration are required for full behaviour:

- scheduler/background jobs must be running for timed actions (for example reminders, ticket/feedback sends, expiry checks)
- email backend/provider must be configured for live outgoing email
- environment variables must be present for deployment configuration

If these are not configured, the site can still run, but time-based automation and live email-dependent workflows will be limited.

## 6. Deployment Summary

The system is delivered as a Django web application with:
- a web interface
- a database
- automated background processes
- email integration

At present, it is primarily prepared for local or internal deployment rather than a large-scale production environment.

## 7. Known Limitations

- some automated processes require technical setup to run reliably
- the current database is SQLite, which is suitable for lighter use but not ideal for high traffic or high concurrency
- the system is not yet structured as a full production-scale deployment
- the ticket draw acceptance deadline is currently fixed at 3 days after selection
- some booking rules are currently hard-coded and may require development work to change

## 8. Maintenance Responsibilities

After handover, the client is responsible for:
- hosting the system
- maintaining system availability
- managing email configuration
- applying future updates or requesting development support where needed

## 9. What Can Be Changed

The following areas can be updated relatively easily:
- attractions and content
- booking rules
- email templates
- text and layout changes

More advanced changes, such as database scaling or background process restructuring, would require technical development work.

## 10. Future Improvements

Potential future improvements include:
- improved user interface and user experience
- more flexible automation features
- enhanced reporting
- migration to a more scalable database
- a more production-ready hosting and background task setup

## 11. Support and Handover

At handover:
- the full codebase is provided
- project documentation is provided
- responsibility for hosting and future operation transfers to the client

The technical handover document should be used by any future developer or technical maintainer working on the system.