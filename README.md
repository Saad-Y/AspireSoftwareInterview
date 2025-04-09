# Library Management System

A Flask-based library management system with email/password authentication and role-based permissions.

## Features

- **User Roles:**
  - **User:** View, search, check out, and return books.
  - **Admin:** Full control over books and user actions.
- **Book Management:**
  - Add, edit, delete books (admin only).
  - Advanced search with filters and natural language queries.
- **Recommendations:**
  - Suggests books based on borrowing history or latest additions.

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd library_system
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python app.py
   ```

## Admin Access

Use the admin secret code (set in `app.config['ADMIN_SECRET']`) during registration to create an admin account.