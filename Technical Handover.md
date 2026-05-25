# Technical Handover Document

## 1. System Overview

Project Name: Ferguson Bequest System

The Ferguson Bequest System is a Django-based web application designed to manage attraction bookings, ticket allocation, waitlists, ticket draws, and automated email communication.

The system supports two main types of users:
- End users, who browse attractions, enter draws, and manage bookings
- Administrators, who manage content, bookings, draws, communications, and reporting through the application and Django admin panel

The project was developed as a local Django application so that it can be run, demonstrated, and maintained without requiring a full production hosting platform from the outset.

## 2. Tech Stack

- Backend: Django 5.2.8 (Python)
- Language: Python 3
- Database: SQLite (default)
- Frontend: Django Templates (HTML/CSS)
- Static Assets: Django static files
- Email: Django email backend
  - Console backend for development by default
  - Configurable for Amazon SES in deployment
- Background Processing: APScheduler via django-apscheduler
- Deployment Model: Local Django deployment / development-style deployment
- Testing: Django test framework
- CI: GitLab CI

## 3. Architecture

### Main Structure

- config/ -> Django configuration (settings.py, urls.py, wsgi.py)
- fergusonbequest/ -> Main application logic
- templates/ -> HTML templates
- static/ -> Source static assets
- docs/ -> Project documentation and image assets
- manage.py -> Django entry point

### Core Application Structure

Within fergusonbequest/, the application is organised around standard Django patterns:

- Models -> Define the database structure and core system entities
- Views -> Handle business logic and request/response behaviour
- Forms -> Handle validated user/admin input
- Admin -> Django admin customisation
- Scheduler -> Automated timed/background processes
- Templates -> Frontend presentation

### Main Functional Areas

The system includes logic for:
- Attraction browsing and booking
- Visit slot allocation
- Booking cancellation
- Waitlist promotion
- Ticket draws
- Draw winner selection and reassignment
- Automated email sending
- Reporting and export/admin support

## 4. Core Feature Logic

### 4.1 Attraction Booking System

Users can browse available attractions and book available visit slots.

#### Booking Flow
- Users select an attraction and an available slot
- A booking record is created and linked to the user and slot
- Slot availability is reduced accordingly
- Confirmation and follow-up workflows may be triggered depending on the booking type

#### Booking Rules
Backend validation is used to enforce rules such as:
- Preventing duplicate active bookings where applicable
- Enforcing slot capacity
- Respecting booking limits and eligibility conditions
- Handling cancellation and ticket visibility timing

#### Ticket Visibility / Release
Some attractions use ticket timing logic to control when tickets become visible or distributed. This is handled through model fields and scheduler-based checks.

Relevant concepts include:
- ticket_visible_at
- ticket_release_days
- ticket sent / not sent state

### 4.2 Waitlist System

If an attraction or slot is full, a user may be placed on a waitlist.

#### Waitlist Behaviour
- Users are added to a waitlist when no capacity remains
- If space becomes available through cancellation or admin intervention, the next eligible user can be promoted
- This is intended to make better use of available spaces and reduce manual admin handling

### 4.3 Ticket Draw System

The application supports ticket draws where users enter for a chance to receive tickets.

#### Draw Workflow
- Users submit entries for a draw
- A winner is selected through draw logic
- Winner details are stored in the database
- The selected user is notified by email
- The winner has a limited period to accept the allocation
- If the winner declines or the response deadline expires, reassignment logic can allocate the ticket to another eligible user

Relevant stored concepts include:
- selected winner
- winner selection timestamp
- acceptance/decline state
- reassignment workflow

#### Expiry / Reassignment
The current system supports a response window of 72 hours for draw winners. If the winner does not accept in time, the system can expire that selection and continue the reassignment process.

### 4.4 Email System

The application supports several categories of email communication:

- Booking confirmations
- Reminder emails
- Ticket distribution emails
- Draw winner notifications
- Feedback request emails

Emails can be triggered:
- directly by user/admin actions
- through automated scheduled tasks

By default, the project uses the Django console email backend for development, but it can be configured to use Amazon SES through environment variables.

### 4.5 Reports / Admin Support

The system includes admin-facing functionality to help staff manage operations more efficiently.

This includes:
- viewing and managing attraction/draw data
- monitoring bookings and capacity
- managing waitlists and draws
- centralised reporting support
- export/admin workflows where configured

## 5. Scheduler and Background Jobs

The project uses APScheduler via django-apscheduler for timed background operations.

These jobs support functions such as:
- sending reminders
- distributing tickets
- checking expired draw winners
- sending feedback request emails
- other time-based operational tasks

The scheduler is executed using a dedicated Django management command:

```bash
python manage.py run_scheduler
```

This command is implemented in:

fergusonbequest/management/commands/run_scheduler.py

For hosted deployments the scheduler should be run as a separate managed service (for example using systemd).

### Deployment Validation

The scheduler architecture was validated using:

- Gunicorn
- systemd
- Nginx
- DEBUG=False deployment configuration

The web application and scheduler operate as separate services.

### Database Note

The current database is SQLite.

SQLite is suitable for local operation and lighter internal use, however PostgreSQL is recommended for longer-term production deployments due to concurrency and scheduler workloads.

## 6. Local Setup

### Clone the Repository

git clone https://github.com/Romes241/sh22-main.git
cd sh22-main

### Create and Activate a Virtual Environment

python3 -m venv venv
source venv/bin/activate

### Install Dependencies

pip install -r requirements.txt

### Create an Environment File

Create a .env file based on the example configuration:

cp config/.env.example config/.env

If `.env.example` is not yet present in the repository, create `config/.env` manually using the structure in Section 7 below.

### Run Database Setup

python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
python manage.py runserver

The system will then be available at:

http://127.0.0.1:8000

## 7. Environment Variables

The application expects environment variables for security and deployment flexibility.

### Generating a Django Secret Key

A Django secret key is required in the `.env` file as:

DJANGO_SECRET_KEY=your-generated-key

To generate a secure secret key, run the following command in Python:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output and place it into the `.env` file, for example:

```env
DJANGO_SECRET_KEY=your-generated-key-here
```

Do not commit real secret keys.

### Core Variables

DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1 localhost

### Email Variables

For local development:

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=no-reply@example.com

### Optional Amazon SES Variables

If SES is used:

AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SES_REGION_NAME=
AWS_SES_REGION_ENDPOINT=

### Notes
- For local development, use DJANGO_DEBUG=True
- For deployment/customer use, DJANGO_DEBUG=False should be used
- DJANGO_SECRET_KEY must always be set
- `DJANGO_ALLOWED_HOSTS` can be space-separated (`127.0.0.1 localhost`) or comma-separated (`127.0.0.1,localhost`)

## 8. Deployment Notes

The deployment architecture validated during handover testing is:

Browser
↓
Nginx
↓
Gunicorn
↓
Django Application

Background jobs run separately:

systemd
↓
run_scheduler
↓
APScheduler

### Deployment Steps

#### Clone repository

```bash
git clone https://github.com/Romes241/sh22-main.git
cd sh22-main
```

#### Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Install dependencies

```bash
pip install -r requirements.txt
pip install gunicorn
```

#### Configure environment

```bash
cp config/.env.example config/.env
```

Update:

- DJANGO_SECRET_KEY
- DJANGO_DEBUG=False
- DJANGO_ALLOWED_HOSTS

#### Prepare database

```bash
python manage.py migrate
python manage.py collectstatic
```

#### Configure Nginx

Example configuration files are included in:

deployment/

Update deployment paths as required.

#### Configure services

Example files:

deployment/fergusonbequest.service
deployment/fergusonbequest-scheduler.service

Copy to:

/etc/systemd/system/

Reload:

```bash
sudo systemctl daemon-reload
```

Enable:

```bash
sudo systemctl enable fergusonbequest
sudo systemctl enable fergusonbequest-scheduler
```

Start:

```bash
sudo systemctl start fergusonbequest
sudo systemctl start fergusonbequest-scheduler
```

### Validation Checklist

Deployment testing confirmed:

- Gunicorn service survives reboot
- Scheduler survives reboot
- Nginx serves static files
- DEBUG=False deployment works
- CSS/media load correctly
- collectstatic deployment flow works

## 9. Database

### Current Database
The default database is SQLite.

### Advantages
- Simple local setup
- No external database server required
- Easy to run for demos and small-scale use

### Limitations
- Not ideal for higher concurrency
- More susceptible to locking issues under multiple simultaneous writes
- Less suitable for production-scale scheduling/background job workloads

### Recommendation
For a more production-ready deployment, the system should be migrated to PostgreSQL.

## 10. Security Considerations

Before any production-style deployment, the following should be addressed:

- Set DJANGO_DEBUG=False
- Provide DJANGO_SECRET_KEY via environment variables
- Configure DJANGO_ALLOWED_HOSTS appropriately
- Use a properly configured email backend
- Do not commit real .env files or credentials
- Use a stronger production deployment model than Django’s development server
- Consider HTTPS, reverse proxying, and server hardening if externally hosted

## 11. Known Issues / Limitations

- Scheduler execution requires the dedicated scheduler service in hosted deployments
- SQLite remains a limiting factor for concurrency and scheduled-write workloads
- The SQLite timeout increase is a temporary mitigation, not a long-term concurrency solution
- Email behaviour depends on correct external email backend configuration when not using the console backend
- A future deployment would benefit from clearer separation of web serving, background tasks, and operational services

## 12. What Can Be Changed

### Easier Changes
- UI templates
- Styling and static assets
- Email templates/content
- Basic booking rules
- Text content and admin-facing display behaviour

### Moderate Changes
- Ticket release timing logic
- Waitlist behaviour
- Draw workflow rules
- Reporting/export features
- Admin workflows

### More Complex Changes
- Scheduler architecture
- Database migration from SQLite to PostgreSQL
- Production deployment architecture
- Large-scale performance/scalability improvements
- Integration into wider university systems

## 13. Maintenance

### Common Commands

#### Run Migrations
python manage.py migrate

#### Create an Admin User
python manage.py createsuperuser

#### Collect Static Files
python manage.py collectstatic

#### Run Development Server
python manage.py runserver

#### Run Tests
python manage.py test

### Logs
How logs are accessed depends on the eventual deployment environment.

If deployed under a Linux service manager, logs may be viewed using something like:

journalctl -u <service-name>

### Restarting the Application
The exact restart command depends on how the application is deployed.

Examples:
- rerun python manage.py runserver for local use
- restart the relevant systemd/Gunicorn service if a managed deployment is later introduced

## 14. Recommended Future Improvements

- Migrate from SQLite to PostgreSQL
- Add stronger monitoring and observability
- Introduce backup/recovery procedures
- Consider PostgreSQL migration
- Improve operational logging
- Improve monitoring and operational logging
- Extend and maintain automated test coverage
- Add clearer operational documentation for deployment, backup, and recovery
- Introduce more formal backup/restore procedures if adopted for live operational use

## 15. Handover Summary

The Ferguson Bequest System is currently in a good state for:
- local operation
- demonstration
- further development
- customer familiarisation with the workflow

It is not yet a fully production-ready deployment, primarily due to:
- SQLite limitations
- scheduler architecture limitations
- email backend/provider configuration still depends on final deployment environment
- the absence of a final hosting/deployment environment during development

The recommended next step after handover is for the receiving team to decide whether the system will remain a local/internal tool or be prepared for a more formal hosted deployment.