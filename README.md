# Approval Workflow API

A REST API for multi-stage approval workflows (leave, purchase and work-order requests),
built with **FastAPI**, **PostgreSQL**, **JWT authentication** and **role-based access control (RBAC)**.

## Problem it solves
Many organizations still approve requests by email or paper, so nobody knows who approved what or where a
request is stuck. This API digitizes that process: every request moves through fixed approval stages, only the
right role can act at each stage, and every action is recorded in an audit history.

## Workflow

```
Employee creates request
        |
        v
  Stage: MANAGER ---- reject ----> REJECTED
        | approve
        v
  Stage: ADMIN   ---- reject ----> REJECTED
        | approve
        v
     APPROVED
```

## Features
- Register / login with JWT access tokens (bcrypt password hashing)
- Roles: **employee**, **manager**, **admin**
- Multi-stage approval: manager first, then admin (no stage skipping)
- Users cannot approve their own requests
- Employees only see their own requests; managers see requests waiting for them; admins see everything
- Approval history log (who did what, when, with comments)
- Auto-generated Swagger docs at `/docs`
- Automated tests with pytest

## Tech stack
Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL, PyJWT, bcrypt, pytest, Docker

## Run with Docker
```bash
cp .env.example .env        # change SECRET_KEY and ADMIN_PASSWORD
docker compose up --build
```
Open http://localhost:8000/docs

## Run locally (SQLite, no Docker)
```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=Admin@12345 uvicorn app.main:app --reload
```

## Run the tests
```bash
pytest -q
```

## API overview
| Method | Endpoint | Who | Description |
|---|---|---|---|
| POST | `/auth/register` | anyone | Create an employee account |
| POST | `/auth/login` | anyone | Get a JWT (form fields `username` = email, `password`) |
| PUT | `/users/{id}/role` | admin | Promote a user to manager/admin |
| POST | `/requests` | any user | Create a request |
| GET | `/requests` | any user | List requests visible to you |
| GET | `/requests/{id}` | owner / manager / admin | Request details with history |
| POST | `/requests/{id}/approve` | manager, then admin | Approve the current stage |
| POST | `/requests/{id}/reject` | manager, then admin | Reject the request |

## Try it (curl)
```bash
# login as the seeded admin
curl -X POST localhost:8000/auth/login -d "username=admin@example.com&password=Admin@12345"

# create a request as an employee
curl -X POST localhost:8000/requests -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" -d '{"title":"Annual leave","kind":"leave"}'
```

## Project structure
```
app/
  main.py          # app setup, startup, admin seeding
  database.py      # engine and session
  models.py        # User, ApprovalRequest, ApprovalLog
  schemas.py       # request/response models
  security.py      # password hashing and JWT
  deps.py          # current-user and role checks
  routers/         # auth and requests endpoints
tests/             # pytest tests for the full workflow
```

## What I would improve next
- Alembic database migrations instead of `create_all`
- Email or WebSocket notifications when a request needs approval
- Pagination and filters on the request list
- Refresh tokens and rate limiting on login
