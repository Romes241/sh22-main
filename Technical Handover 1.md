TECHNICAL HANDOVER DOCUMENT

1. ## System Overview

  Project Name: Ferguson Bequest System

  This is a Django-based web application for managing attraction bookings, ticket allocation, waitlists, ticket draws, and automated email communication.

It supports:
- End users (booking system)
- Administrators (via Django admin panel)

` ` `

2. ## Tech Stack

- Backend: Django (Python)
- Database: SQLite (default)
- Frontend: Django Templates (HTML/CSS)
- Email: SMTP
- Background Processing: Internal Python scheduler
- Deployment: Docker / Gunicorn

` ` ` 

3. ## Architecture

- config/ → Django configuration (settings, URLs)
- apps/ → Core logic (bookings, attractions, draws)
- templates/ → Frontend UI
- static/ → Static assets
- scheduler.py → Background jobs

### Core structure:
- Models → Data (bookings, attractions, users)
- Views → Business logic
- Templates → UI rendering
- Scheduler → Automated processes

` ` `

4. ## Core Feature Logic

### Attractions:

  #### Booking System:
  - Users browse attractions
  - Users book time slots
  - Bookings stored in database
  - May include cancellation deadlines
  - Tickets may be released later

  #### Waitlist System:
  - If full, users join waitlist
  - Users may be promoted when space becomes available

  #### Ticket System:
  - Tickets released based on timing logic
  - Controlled by:
    - ticket_visible_at
    - ticket_release_days
  - Scheduler determines when tickets are sent

### Ticket Draw System:

- Users enter draw
- Winner selected automatically
- Users are sent an email notifying them
- Stored as:
  - winner_booking
  - winner_selected_at
- Users can decline the tickets or the system automatically cancels if the user has not accepted after 72 hours

### Email System:
- Booking confirmations
- Tickets
- Reminders
- Feedback emails
- Triggered by user actions and scheduler

### Scheduler (IMPORTANT):
- Handles tickets, draws, reminders, cleanup
- Currently only runs with runserver
- WILL NOT run automatically in production
- Requires cron/systemd or separate service

` ` `

5. ## Local Setup

#### Clone repo:
git clone <repo-url>
cd <repo>

#### Create environment:
python3 -m venv venv
source venv/bin/activate

#### Install dependencies:
pip install -r requirements.txt

#### Create env file:
cp .env.example .env

Edit .env:
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
EMAIL_HOST=...
EMAIL_PORT=...
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...

Run:
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
python manage.py runserver

` ` `

6. ## Environment Variables

#### Required:
- SECRET_KEY
- DEBUG
- ALLOWED_HOSTS
- EMAIL_HOST
- EMAIL_PORT
- EMAIL_HOST_USER
- EMAIL_HOST_PASSWORD

` ` `

7. ## Deployment

The system is deployed as a local Django application to ensure ease of setup and immediate usability.

#### Steps:
- Clone repository
- Set up virtual environment
- Install dependencies
- Configure .env
- Run migrations
- Start server

The application is accessible via:
http://127.0.0.1:8000

This approach was selected as the client did not yet have a defined production hosting environment. It enables the client to run, test, and demonstrate the system independently without requiring additional infrastructure or support.

This also provides a suitable foundation for future integration into existing university systems (e.g. MyGlasgow) once a formal deployment pathway is established.

` ` `

8. ## Background Jobs (Production)

#### Must be run separately:
python manage.py run_scheduler

#### Recommended:
- cron job
- systemd timer

` ` `

9. ## Database

##### Default: SQLite

#### Limitations:
- Not suitable for high concurrency

#### Recommended:
- PostgreSQL for production

` ` `

10. ## Security

#### Before production:
- Set DEBUG=False
- Use environment variables
- Remove .env from repo
- Configure ALLOWED_HOSTS

` ` `

11. ## Known Issues

- Scheduler not production-ready by default
- SQLite limitations
- Email depends on SMTP reliability

` ` `

12. ## What Can Be Changed

#### Easy:
- UI/templates
- Email templates
- Booking rules

#### Moderate:
- Ticket timing logic
- Waitlist behaviour
- Admin workflows

#### Complex:
- Scheduler architecture
- Database migration
- Scaling system

` ` `

13. ## Maintenance

#### Restart:
systemctl restart <service>

#### Migrate:
python manage.py migrate

#### Logs:
journalctl -u <service>

` ` `

14. ## Future Improvements

- PostgreSQL migration
- Proper scheduler service
- Improved CI/CD
- Monitoring/logging
- Increased test coverage