# Task Management System

## Project Overview

A web-based task management system for internal enterprise use. It allows administrators to assign tasks and developers to view and update their own task status. The system supports full CRUD operations for both users and tasks.

## Tech Stack

- **Backend:** Python Flask
- **Database:** SQLite
- **Frontend:** HTML + Vue3 + Element Plus (via CDN)
- **HTTP Client:** Axios
- **Version Control:** Git + GitHub

## Features

### User Management
- User login with role-based permissions (admin / developer)
- Full CRUD operations for users (Create, Read, Update, Delete)
- Role assignment (admin / developer)
- Admin account protection

### Task Management
- Full CRUD operations for tasks (Create, Read, Update, Delete)
- Task assignment to developers
- Task status update (Pending / In Progress / Finished)
- Real-time statistics dashboard with clickable filter cards
- Advanced filtering: assignee, status, start date, deadline, keyword
- Pagination support (5 / 10 / 20 / 50 per page)

### Developer View
- Personal task list with filtering and pagination
- Personal statistics dashboard (only current user's tasks)
- Task status update

### Security & Data
- Data isolation (developers only see their own tasks)
- Protected admin account

## How to Run

1. Install dependencies:
   ```bash
   pip install flask flask-cors