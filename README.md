# Kafka Backend

Stack
* FastAPI
* SQLite

Methods
* HTTP Requests
* Websockets

## Endpoint Docs

Below is the updated documentation for the `/auth` endpoint:

---

### `/auth/login`

1. **Send a POST Request to `/auth`** (assuming you kept `prefix="/auth"` and the route path is `/`):

   ```bash
   curl -X POST -H "Content-Type: application/json" \
        -d '{"email": "someone@example.com"}' \
        http://127.0.0.1:8000/auth
   ```

2. **Receive JSON Response:**

   ```json
   {
     "user_id": "some-uuid-string",
     "email": "someone@example.com",
     "workspaces": [
       {
         "id": "workspace-uuid-string",
         "name": "Default Workspace",
         "chats": [
           {
             "id": "chat-uuid-string",
             "name": "General Chat",
             "last_updated": "2025-03-20T11:00:00",
             "num_versions": 3
           }
         ]
       }
     ]
   }
   ```

**Notes:**

- If you call the endpoint again with the same email, you'll get the same user ID and any previously created workspaces (with their associated chats and chat summaries).
- Each workspace in the response includes its chats. For every chat, the response shows:
  - **Chat ID**  
  - **Chat Name**  
  - **Last Updated Timestamp**  
  - **Number of .based file versions** (calculated as the total count of versions across all files attached to that chat)

This endpoint ensures that a user is created (along with a default workspace) if they do not already exist, and then returns all the relevant data for that user.