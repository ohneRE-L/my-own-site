University Management System
A web-based application built with Flask, SQLAlchemy, and Flask-Login to manage university academic processes. Designed for administrators, teachers, and students, it facilitates tracking of faculties, groups, lessons, grades, attendance, and schedules.
Key Features

User Roles: Admin, teacher, and student dashboards with role-based access.
Data Management: Add/edit faculties, groups, students, teachers, and lessons.
Grade & Attendance: Teachers can assign grades and mark attendance.
Schedules: Weekly timetable management by faculty.
Student Insights: View grades, attendance, and schedules.

Technologies

Flask: Web framework.
SQLAlchemy: Database ORM.
Flask-Login: User authentication.
SQLite: Default database (extensible to others).

Getting Started

Clone the repo: git clone https://github.com/ohneRE-L/my-own-site
Install dependencies: pip install -r requirements.txt
Run the app: python app.py
Visit: http://localhost:5000

Project Structure

app.py: Core Flask app.
models.py: Database models.
routes.py: Application routes.
templates/: HTML templates.
static/: CSS and assets.

