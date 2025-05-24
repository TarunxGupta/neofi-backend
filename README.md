NEOFI BACKEND - COMPLETE USAGE GUIDE
====================================

📦 SETUP
-------

1. Clone the repo and install dependencies:

```
   $ git clone <your-repo-url>
   $ cd <project-folder>
   $ python -m venv venv
   $ source venv/bin/activatevenv
   $ pip install -r requirements.txt
```

2. Create a `.env` file:

```
   DATABASE_URL=(sql):///./neofi.db
   SECRET_KEY=your-secret
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   REFRESH_TOKEN_EXPIRE_DAYS=7
```

3. Run Alembic migrations:

```
   $ alembic revision --autogenerate -m "init"
   $ alembic upgrade head
```

4. Start the server:

```
   $ uvicorn app.main:app --reload
```

   Docs available at: http://localhost:8000/docs

------------------------------------------------

🔐 AUTHENTICATION ROUTES
------------------------

1. Register:
   POST /register
   ```
   {
     "username": "testuser",
     "email": "test@example.com",
     "password": "password123",
     "role": "owner"
   }
   ```

3. Login:
   POST /login (form-data)
   ```
   username = testuser,
   password = password123
   ```

5. Use the returned access_token in headers:
   ```
   Authorization: Bearer <access_token>
   ```
   
7. Refresh:
   POST /refresh
   ```
   Header: Authorization: Bearer <refresh_token>
   ```

9. Logout:
   POST /logout
   ```
   Header: Authorization: Bearer <access_token>
   ```
   
------------------------------------------------

📅 EVENT ROUTES (CRUD + SHARE + VERSIONS)
-----------------------------------------

1. Create Event:
   ```
   POST /events
   {
     "title": "My Event",
     "description": "Kickoff",
     "start_time": "2025-06-10T10:00:00",
     "end_time": "2025-06-10T11:00:00",
     "location": "Room A",
     "is_recurring": false,
     "recurrence_pattern": null
   }
   ```

3. Batch Create Events:
   POST /events/batch
   ```
   [
     { "title": "E1", "start_time": "...", "end_time": "..." },
     { "title": "E2", "start_time": "...", "end_time": "..." }
   ]
   ```

5. Get All Events:
   GET /events

6. Get Event by ID:
   GET /events/{event_id}

7. Update Event:
   PUT /events/{event_id}
   ```
   {
     "title": "Updated",
     "description": "Changed",
     "start_time": "...",
     "end_time": "..."
   }
   ```

9. Delete Event:
   DELETE /events/{event_id}

10. Share Event:
   POST /events/{event_id}/share
   ```
   {
     "users": [{ "user_id": 2, "role": "viewer" }]
   }
   ```

12. Get Permissions:
   GET /events/{event_id}/permissions

13. Update Permission:
   PUT /events/{event_id}/permissions/{user_id}
   ```
   {
     "role": "editor"
   }
   ```

14. Delete Permission:
    DELETE /events/{event_id}/permissions/{user_id}

------------------------------------------------

🕓 VERSIONING / HISTORY / ROLLBACK
----------------------------------

1. View Version History:
   GET /events/{event_id}/changelog

2. View Single Version:
   GET /events/{event_id}/history/{version_id}

3. View Diff Between Versions:
   GET /events/{event_id}/diff/{v1}/{v2}

4. Rollback to Previous Version:
   POST /events/{event_id}/rollback/{version_id}

------------------------------------------------

🔔 NOTIFICATIONS
----------------

- Triggered automatically on:
  - Event update
  - Event delete
  - Event rollback
  - Event share

Stored in: `notifications` table.

------------------------------------------------

⏱ RATE LIMITING
--------------------------

- Applied to login request:
  - Limit: 10 requests per minute 

- (Optional)
  - add rate limiting to each /event.

------------------------------------------------

🧪 RUN TESTS
------------

1. Make a PostgreSQL database.
2. Add database credentials in .env file.
3. Open localhost:8000/docs on your Web Browser or Use Postman.
4. Once you login, use the Auth Token to Authorize using the top right "Authorize" button.
   (In postman, you can set the Collections Authorization Token and then use "Inherit from parent" for each request.
5. Good to go!

------------------------------------------------
