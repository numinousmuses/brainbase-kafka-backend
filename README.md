# Kafka Backend

Stack
* FastAPI
* SQLite

Methods
* HTTP Requests
* Websockets

## Endpoint Docs

### /auth/login

1. **Send a POST Request to `/auth`** (assuming you kept `prefix="/auth"` and the route path is `"/"`):

   ```bash
   curl -X POST -H "Content-Type: application/json" \
        -d '{"email":"someone@example.com"}' \
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
         "name": "Default Workspace"
       }
     ]
   }
   ```

If you call the same endpoint again with the same email, you’ll get the same user ID and any previously created workspaces.