# IJFINK Backend

A Flask-based backend for the IJFINK application. It provides authentication, user management, and contact form handling with MySQL persistence.

## Features

- JWT-based authentication and login
- User registration for Authors, Admins, Editors, and Publication Team members
- Admin user management endpoints
- Contact query submission and admin review endpoints
- Health check endpoint
- MySQL database integration

## Repository Structure

- `app.py` - Local development entrypoint (`python app.py`)
- `wsgi.py` - Production WSGI entrypoint used by Gunicorn (`wsgi:app`)
- `config.py` - Flask configuration and environment variable loading
- `database/__init__.py` - MySQL database connection helper
- `app/__init__.py` - Flask application factory and blueprint registration
- `app/controllers/` - Business logic for auth, admin, and contact operations
- `app/views/` - HTTP routes and request/response handling
- `app/models/` - Database model helpers for users and profiles
- `requirements.txt` - Python dependency list
- `SQL_Scripts_&_ERD/journaldb.sql` - Database schema script
- `Test Cases/` - API tests (if present)
- `README_Server.md` - VPS deployment guide (Gunicorn, firewall, Nginx, HTTPS)

## Requirements

- Python 3.11+ recommended
- MySQL server accessible from the application
- `pip` for dependency installation

## Setup (Local Development)

1. Create and activate a virtual environment

   Windows (PowerShell):

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

   macOS / Linux:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root and configure database credentials

   ```env
   SECRET_KEY=your-secret-key
   DEBUG=True
   MYSQL_HOST=localhost
   MYSQL_PORT=16189
   MYSQL_USER=your_mysql_user
   MYSQL_PASSWORD=your_mysql_password
   MYSQL_DATABASE=your_database_name
   ```

4. Create the database schema

   Use the SQL script at `SQL_Scripts_&_ERD/journaldb.sql` to create the required tables.

## Running the App

For local development:

```bash
python app.py
```

The application listens on `http://0.0.0.0:5000` by default.

For production / VPS deployment with Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

See [README_Server.md](README_Server.md) for the full VPS setup (firewall, nohup/systemd, Nginx reverse proxy, HTTPS via Certbot).

## Environment Variables

- `SECRET_KEY` - Flask secret key used for session and JWT operations
- `DEBUG` - Enable debug mode when set to `True`
- `MYSQL_HOST` - MySQL hostname
- `MYSQL_PORT` - MySQL port (default: `16189`)
- `MYSQL_USER` - MySQL username
- `MYSQL_PASSWORD` - MySQL password
- `MYSQL_DATABASE` - MySQL database name
- `REDIS_URI`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` - Redis settings are defined but not required for core endpoints shown here

## API Endpoints

### Health Check

- `GET /health`
- Response: `200`
  ```json
  {
    "success": true,
    "message": "IJFINK backend is running."
  }
  ```

### Authentication

#### Login

- `POST /api/auth/login`
- Request body:
  ```json
  {
    "email": "user@example.com",
    "password": "password123",
    "role": "Author"
  }
  ```
- Response on success returns a JWT Bearer token and user details.

#### Register

- `POST /api/auth/register`
- Public registration supports Author accounts.
- Admin users may create `Admin` or `Editor` accounts when including a valid `Authorization: Bearer <token>` header.
- Request body for Author signup:
  ```json
  {
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane@example.com",
    "password": "password123",
    "confirm_password": "password123",
    "institution": "Example University"
  }
  ```

## Admin Endpoints

> All Admin endpoints require `Authorization: Bearer <token>` header.

#### Get All Users

- `GET /api/admin/users`
- Optional query parameters:
  - `role` (Author, Admin, Editor, Publication Team)
  - `status` (Active, Inactive)

#### Get User Details

- `GET /api/admin/users/<user_id>`

#### Toggle User Status

- `PATCH /api/admin/users/<user_id>/status`
- Request body:
  ```json
  {
    "status": "Active"
  }
  ```

## Contact Endpoints

#### Submit Contact Query

- `POST /api/contact/queries`
- Public endpoint
- Request body:
  ```json
  {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "subject": "Question about submission",
    "message": "Please help with..."
  }
  ```

#### Get All Contact Queries

- `GET /api/contact/queries`
- Admin-only endpoint
- Optional query params:
  - `status` (Pending, Resolved)
  - `assigned_to_me` (true, false)

#### Get Contact Query Details

- `GET /api/contact/queries/<query_id>`

#### Update Contact Query Status

- `PATCH /api/contact/queries/<query_id>/status`
- Request body:
  ```json
  {
    "status": "Resolved"
  }
  ```

## Testing

If tests are present under `Test Cases/`, run them with a test runner such as `pytest` after installing any test dependencies.

```powershell
pytest "Test Cases"
```

## Notes

- The app uses `python-dotenv` to load environment variables from `.env`.
- Database connection details are handled by `database/__init__.py` and the `DevelopmentConfig` fallback when no Flask app context exists.
- JWT token creation and validation are implemented in `app/controllers/auth_controller.py`.
