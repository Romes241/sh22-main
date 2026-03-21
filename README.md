# 🎟️ Ferguson Bequest – Staff Ticketing System

A Django-based web application providing University of Glasgow staff with exclusive access to attractions, bookings, and ticket draws.

---

## 🌐 Overview

This system allows eligible staff members to:

* Browse attractions and events
* Book visits (max 3 per year)
* Enter ticket draws
* Join waiting lists
* Manage bookings and cancellations
* Access partner discount codes

Administrators can manage the entire system via an admin dashboard.

---

## 🖼️ System Preview

### 🏠 Home Page

![Home](docs/images/home.png)

### 🎡 Attractions

![Attractions](docs/images/attractions.png)

### 👤 User Dashboard

![Dashboard](docs/images/dashboard.png)

### 📜 Booking History

![Booking History](docs/images/booking_history.png)

### ⚙️ Admin Dashboard

![Admin](docs/images/admin_dashboard.png)

### 💸 Discount Codes

![Discounts](docs/images/discounts.png)

---

## ⚙️ Core Features

### 👥 User

* Authentication (login/register)
* Browse and book attractions
* Ticket draw participation
* Waiting list system
* Booking history & cancellation
* Email notifications
* Discount code access

### 🛠️ Admin

* Manage attractions & slots
* Run ticket draws
* Upload tickets
* Manage discount codes
* Handle user suggestions
* Export reports

---

## 📏 Business Rules

* Maximum **3 bookings per year**
* Users can enter multiple draws but **win only once**
* Winners must respond within **72 hours**
* Tickets sent after cancel deadline
* Only eligible staff can participate

---

## 🏗️ System Architecture

```text
User → Django Views → Models → Database
                         ↓
                  Scheduler (APS)
                         ↓
                  Email System
```

---

## 🔄 System Flow

### Booking Flow

1. Select attraction
2. Check eligibility
3. Verify slot
4. Create booking
5. Send confirmation

### Ticket Draw Flow

1. Enter draw
2. Execute draw
3. Select winner
4. Notify user
5. Re-draw if needed

---

## 🧰 Tech Stack

| Layer     | Technology         |
| --------- | ------------------ |
| Backend   | Django 4.2         |
| Language  | Python 3.9         |
| Database  | SQLite             |
| Scheduler | django-apscheduler |
| Email     | Gmail / Amazon SES |
| Export    | openpyxl           |
| Images    | Pillow             |

---

## 📁 Project Structure

```text
sh22-main/
├── config/
├── fergusonbequest/
├── static/
├── media/
├── manage.py
└── requirements.txt
```

---

## 🚀 Quick Start

```bash
git clone https://stgit.dcs.gla.ac.uk/team-project-h/2025/sh22/sh22-main.git
cd sh22-main
pip install -r requirements.txt
pip install python-dotenv
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open:
http://127.0.0.1:8000/

---

## 🧪 Testing

```bash
python manage.py test fergusonbequest
```

---

## 👨‍💻 Team Contributions

This project was developed collaboratively:

* Backend (Django models & logic)
* Frontend (UI & styling)
* Testing & debugging
* Documentation
* Feature development (booking, draws, admin)

---

## ⚠️ Known Limitations

* SQLite is used for development only
* Email requires external configuration
* Some admin workflows need further validation
* Mobile responsiveness can be improved

---

## 🔮 Potential Enhancements

* Improved analytics dashboard
* Better UI consistency
* Docker deployment support
* Enhanced access control

---

## 📬 Contact

[fergusonbequest@glasgow.ac.uk](mailto:fergusonbequest@glasgow.ac.uk)
https://www.gla.ac.uk/myglasgow/humanresources/staffbenefits/fergusonbequest/

---

## 📄 License

Academic coursework project – University of Glasgow
