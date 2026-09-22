# VoltShare – Smart EV Charging & Grid Management Platform

An academic Full Stack Development project built with Django. VoltShare allows private EV charger owners to share their chargers with EV drivers.

## Project Overview

*   **Host:** Owns an EV charger, adds listings, sets availability, and tracks revenue.
*   **Driver:** Searches for chargers, views available slots, and books sessions.
*   **Architecture:** Django Model-View-Template (MVT) pattern.
*   **Database:** Built-in SQLite database.
*   **Frontend:** HTML, CSS, and Bootstrap 5.

---

## 1. Complete Project Structure

```text
VoltShare_project/
│
├── .venv/                      # Python virtual environment (dependencies)
├── db.sqlite3                  # SQLite database file
├── manage.py                   # Django management script
├── README.md                   # This documentation file
│
├── voltshare/                  # Main project configuration folder
│   ├── settings.py             # Global settings (DB, templates, apps)
│   ├── urls.py                 # Root URL routing
│   └── wsgi.py / asgi.py       # Web server gateways
│
├── charging/                   # Main application folder
│   ├── admin.py                # Admin panel configuration
│   ├── forms.py                # Django forms (Registration, Booking)
│   ├── models.py               # Database tables (UserProfile, ChargingStation, etc.)
│   ├── urls.py                 # App-specific URL routing
│   ├── views.py                # Core logic handling requests/responses
│   └── migrations/             # Database migration history
│
├── templates/                  # HTML Templates
│   ├── base.html               # Master layout with navbar
│   ├── home.html               # Homepage with metrics
│   ├── register.html / login.html # Authentication pages
│   ├── host_dashboard.html     # Host metrics and stations
│   ├── add_station.html        # Form to add a charger
│   ├── manage_availability.html# Form to generate 1-hour slots
│   ├── search_chargers.html    # Driver search directory
│   ├── charger_details.html    # Station details and booking buttons
│   └── driver_dashboard.html   # Driver history and cancellations
│
└── static/                     
    └── css/
        └── style.css           # Custom CSS styling
```

---

## 2. Setup & Execution Instructions

### Prerequisites
- Python 3.x installed.

### Setup Instructions
1. **Open a terminal** and navigate to the project directory:
   ```bash
   cd VoltShare_project
   ```
2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .\.venv\Scripts\activate
   # Mac/Linux:
   source .venv/bin/activate
   ```
3. **Install Django**:
   ```bash
   pip install django
   ```

### Database Setup
To initialize the database tables using the models we defined:
```bash
python manage.py makemigrations
python manage.py migrate
```

### Creating the Default Admin (Superuser)
To access the Django Admin panel:
```bash
python manage.py createsuperuser
```
*(Enter a username, email, and password when prompted).*

### How to Run the Project
Start the development server:
```bash
python manage.py runserver
```
Then, open a web browser and go to `http://127.0.0.1:8000/`. To access the admin panel, go to `http://127.0.0.1:8000/admin/`.

---

## 3. Module Explanation (For Viva/Review)

1.  **`models.py` (Database Layer):** 
    Defines the shape of our data. We used `UserProfile` to extend the default user with Roles (Host/Driver). `ChargingStation` stores hardware details. `AvailabilitySlot` breaks time into 1-hour bookable chunks. `Booking` tracks reservations and costs.
2.  **`views.py` (Logic Layer):** 
    Acts as the middleman. It intercepts HTTP requests, queries the database, applies logic (like checking for double-bookings or generating 1-hour time blocks), and passes data to the HTML templates. We used `@login_required` to protect sensitive views.
3.  **`forms.py` (Input Layer):** 
    Automatically generates secure HTML forms based on our models. It handles validation, like making sure passwords match during registration.
4.  **`urls.py` (Routing Layer):** 
    Maps browser URLs (like `/search/`) to specific Python functions inside `views.py`.

---

## 4. SRS Requirements Mapping

| SRS Requirement | How it was Implemented |
| :--- | :--- |
| **R1:** Roles (Host/Driver) | Created `UserProfile` model linked to Django's built-in `User` via `OneToOneField`. |
| **R2:** Authentication | Used Django's built-in secure `login()`, `logout()`, and password hashing. |
| **R3:** Dashboard Restrictions | Used `request.user.userprofile.role` checks inside views to restrict access. |
| **R4:** Create Charger Listings | Built `ChargingStation` model and `add_station` view/form. |
| **R5 & R6:** Public Directory & Search | Built `search_chargers` view filtering by Location and Plug Type via Django ORM. |
| **R7:** Generate Availability Slots | `manage_availability` view breaks Host-selected time ranges into **1-hour blocks**. |
| **R8 & R9:** Driver Booking | `book_slot` view handles requests and transitions slot status from Available to Booked. |
| **R10:** Prevent Double Booking | `book_slot` checks `if slot.status == 'Booked'` and rejects the request if true. |
| **R11:** Cancel Booking | `cancel_booking` updates Booking status to 'Cancelled' and frees up the time slot. |
| **R12:** Delete Unbooked Slots | `delete_slot` checks `if slot.status == 'Booked'` to prevent Hosts from deleting reservations. |
| **R13 & R14:** Dashboards | Created tailored dashboards showing upcoming bookings, revenue (for Hosts), and past history (for Drivers). |
| **R15:** Cost Calculation | Done dynamically in `book_slot` based on hours duration and Host's hourly rate. |
| **R16:** Admin Panel | Registered all models in `admin.py` utilizing Django's default secure panel. |
| **R17:** Platform Metrics | Homepage dynamically queries `.count()` for Chargers and Bookings. |

---

## 5. Manual Test Cases

| Test Case | Input / Action | Expected Result | Actual Result |
| :--- | :--- | :--- | :--- |
| **1. Registration** | `/register/`, enter details, select "Driver" | Redirect to login with success message. | Pass |
| **2. Login** | `/login/`, enter valid credentials | Redirect to home with welcome message & Navbar updates. | Pass |
| **3. Host Charger Creation** | Logged as Host, go to Dashboard -> Add Station | Station appears in Dashboard grid. | Pass |
| **4. Availability Creation** | Dashboard -> Manage Availability -> Add Slot (2 hours) | System splits range into two 1-hour `Available` slots. | Pass |
| **5. Driver Search** | Navbar -> Find Chargers -> Search "Chennai" | Grid filters to show Chennai stations. | Pass |
| **6. Successful Booking** | Driver views station details -> Clicks "Book Now" | Cost calculated, Booking created, slot disappears from 'Available' list. | Pass |
| **7. Double Booking Attempt** | Host checks Availability table for booked slot | Slot shows "Booked" badge; "Delete" button is disabled. | Pass |
| **8. Booking Cancellation** | Driver Dashboard -> Click "Cancel" on a booking | Booking moves to "Past" section, Slot becomes 'Available' again. | Pass |
| **9. Unauthorized Access** | Driver attempts to navigate to `/host/dashboard/` | Redirected to home with "Unauthorized access" red alert. | Pass |
