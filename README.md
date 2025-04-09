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
   ```
2. Create venv:
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create db:
   ```bash
   flask shell
   db.create_all()
   ```
5. Run the application:
   ```bash
   python app.py
   ```
## Admin Access

Use the admin secret code (set in `app.config['ADMIN_SECRET']`) during registration to create an admin account. Now it is 'myadminsecret'.
If you leave it empty you will be registered as a normal user.

## Possible Improvements

Token based sessions, chatbot powered by chatgpt for enhanced search.