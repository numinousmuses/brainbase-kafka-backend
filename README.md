# Kafka Backend

✅ Milestone 1: Agent can write simple Based code and can iterate to fix errors

✅ Milestone 2: Agent can write Based code diffs to modify the existing code and can iterate to fix errors

✅ Milestone 3: Agent can now run on a websocket

✅ Milestone 4: Client that can interact with the agent over websocket

---

# Demo

There is a demo deployed, but it's very slow due to free tier rate limit. For a faster experience you can clone the [frontend](https://github.com/numinousmuses/brainbase-poc) and [backend](https://github.com/numinousmuses/brainbase-kafka-backend) repos then spin up the backend with the steps noted in section 2 of the brief docs below, then spin up the frontend with npm run dev.

Deployed backend: https://brainbase-kafka-backend.onrender.com/

Deployed frontend: https://kafka-brainbase.vercel.app/

---

Stack
* FastAPI
* SQLite

Methods
* HTTP Requests
* Websockets

---

# Brief Docs

- **Project Layout** (file structure and purpose),
- **How to Install & Run**,
- **Available Routers & Endpoints**,
- **Where to Find** key modules (database, WebSocket, etc.).

---

## 1. Project Layout

Project structure:

```
app/
├── core/
│   ├── basedagent/
│   │   ├── __init__.py
│   │   ├── llm.py
│   │   ├── main.py
│   │   ├── triage.py
│   │   └── validation.py
│   ├── ws/
│   │   ├── ws_actions/
│   │   │   ├── __init__.py
│   │   │   ├── delete_file.py
│   │   │   ├── main.py
│   │   │   ├── new_message_action.py
│   │   │   ├── plain_text.py
│   │   │   ├── revert_version.py
│   │   │   └── upload_file.py
│   │   ├── ws_disconnect.py
│   │   └── ws_initpayload.py
│   ├── config.py
│   ├── database.py
│   └── unifieddiff.py
├── models/
│   ├── base.py
│   ├── chat.py
│   ├── chat_conversation.py
│   ├── chat_file.py
│   ├── chat_file_version.py
│   ├── file.py
│   ├── model.py
│   ├── user.py
│   └── workspace.py
├── routers/
│   ├── auth.py
│   ├── chat.py
│   ├── file.py
│   ├── model.py
│   ├── workspace.py
│   └── ws_router.py
├── schemas/
│   ├── auth.py
│   ├── basedagent.py
│   ├── chat.py
│   ├── file.py
│   ├── model.py
│   ├── workspace.py
│   └── ws.py
├── main.py
├── requirements.txt
└── README.md
```

### Key Directories & Files

- **`app/main.py`**  
  Primary FastAPI application entry point. It creates a `FastAPI()` instance, registers routers, sets up CORS, and initializes the database.

- **`app/core/`**  
  General backend “core” modules:
  - `database.py` sets up SQLAlchemy + session management.
  - `config.py` might hold environment configuration or global settings.
  - `unifieddiff.py` and `basedagent/` are specialized logic modules for generating or applying diffs, working with “.based” files, or prompting an LLM.

- **`app/core/ws/`**  
  WebSocket–specific code.  
  - **`ws_actions/`** contains action handlers (`upload_file.py`, `new_message_action.py`, `delete_file.py`, etc.).  
  - `ws_disconnect.py` handles cleanup/persistence on socket disconnect.  
  - `ws_initpayload.py` builds the initial payload for a WebSocket client.

- **`app/models/`**  
  SQLAlchemy ORM models (`Chat`, `ChatFile`, `File`, `User`, etc.).

- **`app/routers/`**  
  FastAPI router modules for REST endpoints (`auth.py`, `workspace.py`, `chat.py`, etc.) plus the `ws_router.py` that configures the WebSocket path.

- **`app/schemas/`**  
  Pydantic models for request/response validation.

- **`requirements.txt`**  
  Lists Python dependencies needed to run the app.

---

## 2. How to Install & Run

1. **Create & activate a virtual environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or venv\Scripts\activate on Windows
   ```

2. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the API** (development):
   ```bash
   uvicorn app.main:app --reload
   ```
   - `app.main:app` references the `app` object created inside `app/main.py`.
   - `--reload` restarts the server whenever you edit files.

4. **Check logs**:  
   You should see something like:
   ```
   INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
   ```

5. **Open** `http://localhost:8000/docs` in your browser to see the **Swagger** UI.  
   You can also check `http://localhost:8000/redoc` for ReDoc-based docs.

---

## 3. Routers & Endpoints

### 3.1. Registered Routers

In **`app/main.py`**:
```python
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(workspace.router, prefix="/workspace", tags=["Workspace"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(file.router, prefix="/file", tags=["File"])
app.include_router(model.router, prefix="/models", tags=["Model"])
app.include_router(ws_router.router, prefix="/ws", tags=["WebSocket"])
```

That means:

- **`/auth/*`** → endpoints for authentication (login, signup, etc.).
- **`/workspace/*`** → endpoints for workspace management.
- **`/chat/*`** → endpoints for chat creation, retrieval, etc.
- **`/file/*`** → endpoints for file upload/download (non-WebSocket).
- **`/models/*`** → endpoints for listing/managing LLM or model configs.
- **`/ws/*`** → **WebSocket** paths for real-time chat sessions (e.g., `ws://.../ws/{chat_id}`).

### 3.2. Automatic OpenAPI Documentation

FastAPI automatically **generates** OpenAPI specs from your router endpoints. You can see them in **Swagger** by browsing to:

```
GET http://localhost:8000/docs
```

(when the server is running).

---

## 4. WebSocket Communication

Your WebSocket routes live in **`ws_router.py`**. A typical client connects to:

```
ws://localhost:8000/ws/{chat_id}
```

- On connect, the server loads the chat’s data (conversation, files) and sends an **initial payload**.
- The client can send JSON messages with an `"action"` key to perform certain tasks (upload files, create new messages, revert versions, delete files, etc.) or send plain text for normal chat.
- On disconnect, the server writes unsaved messages to the database.

*(See the “WebSocket Docs” you have for more detail about the structure of messages and responses.)*

---

## 5. Additional Notes

- **Database Initialization**:  
  `init_db()` is called in `app/main.py`, ensuring your `models/` are set up. If you need migrations, you might integrate **Alembic** or a similar tool.

- **Configurable**:  
  CORS origins, database URLs, or environment variables can typically be set via `app/core/config.py`.

- **Deployment**:  
  For production, you’d run something like:
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```
  or use **gunicorn** with **uvicorn workers**:
  ```bash
  gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
  ```
  Don’t forget to update `allow_origins` in your CORS settings for the domains you use in production.

---

### 6. Organization

Your **FastAPI** backend is organized into modular parts:

- **`main.py`** to create the app and tie together all routers.  
- **`core/`** for database access and any specialized logic (WebSocket helpers, LLM-based code generation, etc.).  
- **`models/`** for SQLAlchemy ORM definitions.  
- **`routers/`** for REST endpoints (plus the WebSocket “router”).  
- **`schemas/`** for pydantic models ensuring typed request/response data.

Starting it is as simple as installing dependencies, running **uvicorn**, and then viewing endpoints or docs in the browser. Use the WebSocket flow for interactive chat or file manipulation; use the standard REST endpoints for authentication, file listing, or retrieving chat data.

---

# Database Schema

Below is a **visual/table-based** overview of the database schema.

---

## 1. Entity-Relationship Overview

```
┌────────────┐           ┌────────────────┐        ┌────────────────┐
│    User    │           │   Workspace    │        │     Model      │
│------------│ 1       M │----------------│        │----------------│
│ id (PK)    │───────────│ id (PK)        │        │ id (PK)        │
│ email      │           │ name           │        │ name           │
│            │           │ owner_id (FK)  │        │ ak             │
│            │           └────────────────┘        │ base_url       │
│            │                                     │ user_id (FK)   │
└────────────┘                                     └────────────────┘
    |   \
    |    \ 1..M
    |     \
    |      ┌────────────────┐        ┌─────────────────────┐
    |      │     Chat       │        │       File          │
    |      │----------------│        │---------------------│
    |      │ id (PK)        │        │ id (PK)             │
    |      │ name           │        │ filename            │
    |      │ last_updated   │        │ path                │
    |      │ user_id (FK)   │        │ workspace_id (FK)   │
    |      │ workspace_id(FK│        └─────────────────────┘
    |      └────────────────┘
    |               | 1..M
    |               |  
    |          ┌─────────────────────┐         ┌────────────────────────┐
    |          │   ChatConversation  │         │      ChatFile          │
    |          │---------------------│         │------------------------│
    |          │ id (PK)             │         │ id (PK)                │
    |          │ role                │         │ filename               │
    |          │ type                │         │ path                   │
    |          │ content             │         │ chat_id (FK)           │
    |          │ chat_id (FK)        │         └────────────────────────┘
    |          └─────────────────────┘
    |                     |
    |                     | 1..M
    |                     |
    |               ┌─────────────────────────┐
    |               │    ChatFileVersion      │
    |               │-------------------------│
    |               │ id (PK)                 │
    |               │ timestamp               │
    |               │ content                 │
    |               │ chat_file_id (FK)       │
    |               └─────────────────────────┘
    |
    └─> (Indicates a one-to-many relationship from User to Chats, Models, Workspaces)
```

### Reading the Diagram

- **Boxes** represent **tables** (e.g., `User`, `Workspace`, `Chat`, etc.).  
- **Lines** show relationships. For instance, a **User** can have **multiple** Workspaces, so there’s a `1..M` relationship from `User` to `Workspace`.  
- **(PK)** stands for **primary key**.  
- **(FK)** stands for **foreign key** (points to a primary key in another table).

---

## 2. Table Summaries & Null Constraints

Below is a concise table listing each model, its columns, and whether they allow `NULL` values (`nullable=False` means “not null” in the database).

### **User**
- **id**: `String`, Primary Key, **not null**  
- **email**: `String`, Unique, **not null**  
- **Relationships**:
  - `workspaces` (User → Workspaces, 1-to-many)
  - `chats` (User → Chats, 1-to-many)
  - `models` (User → Models, 1-to-many)

**Can a user have multiple chats and workspaces?**  
Yes. The relationships in SQLAlchemy specify that a single `User` can be linked to many `Workspace` entries and many `Chat` entries.

### **Workspace**
- **id**: `String`, Primary Key, **not null**  
- **name**: `String`, **not null**  
- **owner_id**: `String`, Foreign Key to `User.id`, **not null**  
- **Relationships**:
  - `owner` (Workspace → User, many-to-1)
  - `files` (Workspace → File, 1-to-many)
  - `chats` (Workspace → Chat, 1-to-many)

### **File**
- **id**: `String`, Primary Key, **not null**  
- **filename**: `String`, **not null**  
- **path**: `String`, **not null**  
- **workspace_id**: `String`, Foreign Key to `Workspace.id`, **not null**
- **Relationship**:
  - `workspace` (File → Workspace, many-to-1)

### **Chat**
- **id**: `String`, Primary Key, **not null**  
- **name**: `String`, **not null**  
- **last_updated**: `String` (can be `NULL` if not specified)  
- **user_id**: `String`, Foreign Key to `User.id`, **not null**  
- **workspace_id**: `String`, Foreign Key to `Workspace.id`, **not null**  
- **Relationships**:
  - `user` (Chat → User, many-to-1)
  - `workspace` (Chat → Workspace, many-to-1)
  - `conversation` (Chat → ChatConversation, 1-to-many)
  - `chat_files` (Chat → ChatFile, 1-to-many)

### **ChatConversation**
- **id**: `String`, Primary Key, **not null**  
- **chat_id**: `String`, Foreign Key to `Chat.id`, **not null**  
- **role**: `String`, **not null** (e.g., "system", "user", "assistant")  
- **type**: `String`, **not null**  
- **content**: `String`, **not null**  
- **Relationship**:
  - `chat` (ChatConversation → Chat, many-to-1)

### **ChatFile**
- **id**: `String`, Primary Key, **not null**  
- **filename**: `String`, **not null**  
- **path**: `String`, **not null**  
- **chat_id**: `String`, Foreign Key to `Chat.id`, **not null**  
- **Relationships**:
  - `chat` (ChatFile → Chat, many-to-1)
  - `versions` (ChatFile → ChatFileVersion, 1-to-many)

### **ChatFileVersion**
- **id**: `String`, Primary Key, **not null**  
- **chat_file_id**: `String`, Foreign Key to `ChatFile.id`, **not null**  
- **timestamp**: `String`, **not null**  
- **content**: `String`, **not null**  
- **Relationship**:
  - `chat_file` (ChatFileVersion → ChatFile, many-to-1)

### **Model**
- **id**: `String`, Primary Key, **not null**  
- **name**: `String`, **not null**  
- **ak**: `String`, **not null** (API key)  
- **base_url**: `String`, **not null**  
- **user_id**: `String`, Foreign Key to `User.id`, **not null**  
- **Relationship**:
  - `user` (Model → User, many-to-1)

---



# Endpoint Docs

Below is the updated documentation for the `/auth` endpoint:

---

## `/auth/login`

1. **Send a POST Request to `/auth`** (assuming you kept `prefix="/auth"` and the route path is `/`):

   ```bash
   curl -X POST -H "Content-Type: application/json" \
        -d '{"email": "someone@example.com"}' \
        http://127.0.0.1:8000/auth/login
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

## `/workspace/new`
---

### Sample Request

Below is an example using `curl` to simulate the file upload from your Next.js app:

```bash
curl -X POST "http://127.0.0.1:8000/workspace/new" \
  -F "owner_id=123e4567-e89b-12d3-a456-426614174000" \
  -F "name=MyNewWorkspace" \
  -F "files=@/path/to/document.pdf" \
  -F "files=@/path/to/image.png"
```

- **owner_id & name:** Sent as form fields.
- **files:** The actual files are attached using the `-F` flag.

### Expected Response

```json
{
  "workspace_id": "workspace-uuid-string",
  "files": [
    {
      "file_id": "file-uuid-string",
      "filename": "document.pdf"
    },
    {
      "file_id": "another-file-uuid",
      "filename": "image.png"
    }
  ]
}
```

## `/file/upload`

---

### Example 1: Uploading Files to a Chat

**Sample Request (using curl):**

```bash
curl -X POST "http://127.0.0.1:8000/file/upload" \
  -F "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -F "target_id=chat-uuid-string" \
  -F "is_chat=true" \
  -F "files=@/path/to/document.pdf" \
  -F "files=@/path/to/image.png"
```

**Explanation:**

- **user_id:** The ID of the user uploading the files.
- **target_id:** The chat ID (from which the parent workspace is inferred).
- **is_chat:** Set to `true` so the files are added both to the chat and to the chat’s workspace.
- **files:** Two actual files are being uploaded.

**Sample Response:**

```json
{
  "files": [
    "file-uuid-string-1",
    "file-uuid-string-2"
  ]
}
```

*The response returns a list of the generated file IDs for the uploaded files.*

---

### Example 2: Uploading Files to a Workspace

**Sample Request (using curl):**

```bash
curl -X POST "http://127.0.0.1:8000/file/upload" \
  -F "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -F "target_id=workspace-uuid-string" \
  -F "is_chat=false" \
  -F "files=@/path/to/document.pdf"
```

**Explanation:**

- **user_id:** The ID of the user uploading the file.
- **target_id:** The workspace ID to which the file should be added.
- **is_chat:** Set to `false` so the file is only added to the workspace.
- **files:** One actual file is being uploaded.

**Sample Response:**

```json
{
  "files": [
    "file-uuid-string-3"
  ]
}
```

*The response returns a list with the generated file ID for the uploaded file.*

---

## `/chat/new`

### Sample Request Using `curl`

Here’s an example request to create a new chat:

```bash
curl -X POST "http://127.0.0.1:8000/chat/new" \
  -F "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -F "workspace_id=workspace-uuid-string" \
  -F "chat_name=General Chat"
```

---

### Expected Response

A successful request might return a response like this:

```json
{
  "chat_id": "generated-chat-uuid-string",
  "name": "General Chat",
  "last_updated": "2025-03-20T11:00:00.123456"
}
```

---

### Explanation

- **Form Fields:**  
  The endpoint expects three form fields:  
  - `user_id`: The UUID of the user creating the chat.
  - `workspace_id`: The UUID of the workspace where the chat will reside.
  - `chat_name`: The name to assign to the new chat.
  
- **Timestamp:**  
  The `last_updated` field is set to the current UTC timestamp (formatted in ISO 8601), ensuring that the chat record is properly initialized with a timestamp.
  
- **Database Interaction:**  
  A new `Chat` record is created and added to the session. After committing and refreshing, the chat details are returned via the `ChatNewResponse` schema.

## DELETE `/chat/{chat_id}`

### Sample Request

Using `curl` to delete a chat by its ID:

```bash
curl -X DELETE "http://127.0.0.1:8000/chat/123e4567-e89b-12d3-a456-426614174000"
```

### Expected Response

If the chat exists and is successfully deleted, you should receive a JSON response like:

```json
{
  "detail": "Chat deleted successfully."
}
```

If the chat does not exist, you'll receive an error:

```json
{
  "detail": "Chat not found."
}
```

---

## PATCH `/chat/rename`

### Sample Request

Using `curl` to rename a chat by providing its ID and a new name (via form fields):

```bash
curl -X PATCH "http://127.0.0.1:8000/chat/rename" \
  -F "chat_id=123e4567-e89b-12d3-a456-426614174000" \
  -F "new_name=New Chat Name"
```

### Expected Response

Upon successful renaming, the response will return the updated chat details, including the updated timestamp:

```json
{
  "chat_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "New Chat Name",
  "last_updated": "2025-03-20T11:00:00.123456"
}
```

If the chat ID is not found, an error message will be returned:

```json
{
  "detail": "Chat not found."
}
```

---

## `/file/{file_id}` and `/file/rename`

### Sample Requests & Responses

#### **Delete File Endpoint**

**Sample Request (using curl):**

```bash
curl -X DELETE "http://127.0.0.1:8000/file/delete/123e4567-e89b-12d3-a456-426614174000"
```

**Expected Response:**

```json
{
  "detail": "File deleted successfully."
}
```

If the file is not found, the response will be:

```json
{
  "detail": "File not found."
}
```

---

#### **Rename File Endpoint**

**Sample Request (using curl):**

```bash
curl -X PATCH "http://127.0.0.1:8000/file/rename" \
  -F "file_id=123e4567-e89b-12d3-a456-426614174000" \
  -F "new_name=new_document.pdf"
```

**Expected Response:**

```json
{
  "file_id": "123e4567-e89b-12d3-a456-426614174000",
  "new_filename": "new_document.pdf",
  "new_path": "uploads/files/123e4567-e89b-12d3-a456-426614174000_new_document.pdf"
}
```

If the file is not found, the endpoint will return:

```json
{
  "detail": "File not found."
}
```

---

### Explanation

- **Delete Endpoint:**  
  Uses a path parameter (`file_id`) to locate and delete the file record(s) from the database and remove the file from disk.

- **Rename Endpoint:**  
  Accepts `file_id` and `new_name` as form fields, renames the physical file on disk (by constructing a new unique filename) and updates the corresponding records in both the File and ChatFile tables, then returns the updated file information.


## `/workspace/rename` and `DELETE /workspace/{workspace_id}`

### Sample Requests & Responses

#### **Rename Workspace**

**Sample Request (using curl):**

```bash
curl -X PATCH "http://127.0.0.1:8000/workspace/rename" \
  -F "workspace_id=workspace-uuid-string" \
  -F "new_name=Renamed Workspace"
```

**Expected Response:**

```json
{
  "workspace_id": "workspace-uuid-string",
  "new_name": "Renamed Workspace"
}
```

If the workspace is not found, the response will be:

```json
{
  "detail": "Workspace not found."
}
```

---

#### **Delete Workspace**

**Sample Request (using curl):**

```bash
curl -X DELETE "http://127.0.0.1:8000/workspace/delete/workspace-uuid-string"
```

**Expected Response:**

```json
{
  "detail": "Workspace and all associated data deleted successfully."
}
```

If the workspace is not found, the response will be:

```json
{
  "detail": "Workspace not found."
}
```

---

### Explanation

- **Rename Workspace (`PATCH /workspace/rename`):**  
  The endpoint accepts `workspace_id` and `new_name` as form fields, updates the workspace's name, commits the change, and returns the updated details.

- **Delete Workspace (`DELETE /workspace/delete/{workspace_id}`):**  
  The endpoint deletes the workspace record from the database. Before deletion, it iterates through all file records associated with the workspace and removes the corresponding physical files from disk. Due to cascade deletion in your model, all related chats and file records are automatically removed.

## `/models/new` and `DELETE /models/{model_id}`

#### **Create New Model**

**Sample Request (using curl):**

```bash
curl -X POST "http://127.0.0.1:8000/models/new" \
  -F "user_id=123e4567-e89b-12d3-a456-426614174000" \
  -F "name=Example Model" \
  -F "ak=your-api-key" \
  -F "base_url=http://api.example.com"
```

**Expected Response:**

```json
{
  "id": "generated-model-uuid-string",
  "name": "Example Model",
  "base_url": "http://api.example.com",
  "user_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

---

#### **Delete a Model**

**Sample Request (using curl):**

```bash
curl -X DELETE "http://127.0.0.1:8000/models/delete/generated-model-uuid-string"
```

**Expected Response:**

```json
{
  "detail": "Model deleted successfully."
}
```

If the model is not found, you’ll receive:

```json
{
  "detail": "Model not found."
}
```

# Websocket Docs

---

## 1. High-Level Flow

When a client connects to:

```
/ws/{chat_id}
```

the following occurs:

1. **`ws_router.py`**:
   - Accepts the WebSocket connection.
   - Calls **`build_initial_payload(...)`** (from `ws_initpayload.py`) to load:
     - The `Chat` record,
     - Its conversation,
     - Any attached files (both text-based and `.based`),
     - Any additional workspace files,
     - A list of model names available to the user.
   - Sends the **initial payload** back to the client as JSON.

2. The server then enters a **loop**:
   - Waits for the client to send a message (plain text or JSON).
   - Hands that message to **`handle_action(...)`** (in `ws_actions.py`), which **dispatches** to the correct handler based on the `"action"` key (e.g., `"upload_file"`, `"new_message"`, `"revert_version"`, or if no `"action"`, treat as **plain text**).

3. On **WebSocketDisconnect**, `ws_disconnect.py`’s **`persist_on_disconnect(...)`** is called:
   - Persists any in-memory conversation messages into the DB.
   - Closes the WebSocket gracefully.

**Important**: Splitting the code into multiple modules **does not** change the **JSON request/response structure**. The front-end can continue to send and receive messages in the same format.

---

## 2. Initial Payload

Upon connecting, the client receives a **JSON** payload shaped like this:

```jsonc
{
  "chat_id": "string",
  "conversation": [
    {
      "role": "user" | "assistant" | "system",
      "type": "text" | "file",
      "content": "string or JSON"
    },
    ...
  ],
  "chat_files_text": [
    {
      "file_id": "string",
      "name": "example.txt",
      "content": "Content extracted from file (text or path for images)",
      "type": "text" | "image"
    },
    ...
  ],
  "chat_files_based": [
    {
      "file_id": "string",
      "name": "some_file.based",
      "latest_content": "Full .based file content",
      "versions": [
        {
          "version_id": "string",
          "timestamp": "ISO-8601 datetime",
          "diff": "unified diff from this version to the newest version"
        },
        ...
      ],
      "type": "based"
    }
    ...
  ],
  "workspace_files": [
    {
      "file_id": "string",
      "name": "some_workspace_file.txt"
    },
    ...
  ],
  "workspace_id": "string",
  "models": [
    "model_a",
    "model_b"
    ...
  ]
}
```

### Where is this built?

- **`ws_initpayload.py`** → `build_initial_payload(...)`:
  - Loads the `Chat` + conversation from the DB.
  - Gathers `.txt`, `.pdf`, `.jpg`, and `.based` files.
  - Constructs `WsInitialPayload` → uses **pydantic** to produce a final JSON to send.

**No changes** to the data structure—only the function location changed.

---

## 3. Message Actions

After sending the initial payload, the server **listens** for client messages in a loop. All messages arrive in `ws_router.py`, are routed through `handle_action(...)` (from `ws_actions.py`), which delegates to **sub-handlers**:

1. **Plain Text** (no `"action"`) → `handle_plain_text(...)`
2. **`"upload_file"`** → `handle_upload_file(...)`
3. **`"new_message"`** → `handle_new_message_action(...)`
4. **`"revert_version"`** → `handle_revert_version(...)`
5. Otherwise → `{"error": "Unknown action: XXX"}`

### 3.1. Plain Text

If the client message has **no** `"action"` field or is **invalid JSON**, it is treated as **plain text** by `handle_plain_text.py`.

- **Example**:

  **Client**:
  ```text
  Hello, are you there?
  ```

  **Server**:
  ```text
  Echo: Hello, are you there?
  ```

The server simply **echoes** the content (for demonstration). The new user message and the echoed assistant message get added to the in-memory conversation list.

---

### 3.2. `"upload_file"`

**Handled by** `upload_file.py` → `handle_upload_file(...)`.

#### Request

```json
{
  "action": "upload_file",
  "filename": "example.pdf",
  "file_data": "<BASE64 ENCODED BYTES>"
}
```

#### Server Steps

1. Decodes `file_data` from base64.
2. Saves file to disk, e.g., `"uploads/files/<UUID>_example.pdf"`.
3. Creates a `ChatFile` DB record (and `File` in the workspace if needed).
4. Appends a **file message** to the conversation.

#### Response

```json
{
  "action": "file_uploaded",
  "message": {
    "role": "user",
    "type": "file",
    "content": {
      "file_id": "<UUID>",
      "filename": "example.pdf",
      "path": "uploads/files/<UUID>_example.pdf"
    }
  }
}
```

---

### 3.3. `"new_message"`

**Handled by** `new_message_action.py` → `handle_new_message_action(...)`.

#### Request

```json
{
  "action": "new_message",
  "model": "gpt-4",
  "prompt": "Explain this PDF's content.",
  "is_first_prompt": false,
  "is_chat_or_composer": false,
  "selected_filename": null  // or "someFile.based"
}
```

#### Server Steps

1. Adds a **user** message (`role="user"`, `type="text"`) to the conversation.
2. Fetches the chosen model from DB.
3. Calls **`handle_new_message(...)`** from `app.core.basedagent` with:
   - The entire conversation,
   - All text-based files,
   - The selected `.based` file (if any),
   - The “other” `.based` files.

4. Based on the agent’s `type`, the server responds:

   - **`"type": "response"`** → Plain text (just send text back).
   - **`"type": "based"`** → Create a brand-new `.based` file in the DB, respond with `{"action": "agent_response", ...}` containing the new file’s content.
   - **`"type": "diff"`** → Apply the diff to the existing `.based` file, add a new version, respond with the updated content.

#### Example **Agent** response (plain text):

```json
// The server just sends text directly:
"Here is a summary of the PDF..."
```

or, wrapped:

```json
{
  "role": "assistant",
  "type": "text",
  "content": "Here is a summary of the PDF..."
}
```

---

### 3.4. `"revert_version"`

**Handled by** `revert_version.py` → `handle_revert_version(...)`.

#### Request

```json
{
  "action": "revert_version",
  "version_id": "abc123-uuid",
  "filename": "myCode.based"
}
```

#### Server Steps

1. Finds the target `ChatFileVersion`.
2. Creates a new version with that old content as the new latest version.
3. Updates conversation or returns a final message indicating the revert result.

#### Response

```json
{
  "action": "revert_complete",
  "message": {
    "role": "assistant",
    "type": "file",
    "content": {
      "based_filename": "myCode.based",
      "based_content": "... the old content ...",
      "message": "Reverted to version abc123-uuid; new version is xyz456-uuid"
    }
  }
}
```

---

### 3.5. `"delete_file"`

**Handled by** a new `delete_file.py` → `handle_delete_file(...)` (or a similar file).  

#### Request

```json
{
  "action": "delete_file",
  "file_id": "some-file-id"
}
```

#### Server Steps

1. Looks up the file referenced by `file_id` in the **`ChatFile`** table for this chat.
2. (Optionally) deletes the actual file from disk (if it exists).
3. Removes the record from **`ChatFile`** (detaching it from the chat).
4. Also removes it from the workspace’s **`File`** table if present.
5. Commits the database changes.
6. Appends a **system** message to the in-memory conversation to record the deletion.
7. Returns a message indicating the file has been removed.

#### Response

```json
{
  "action": "file_deleted",
  "message": {
    "role": "system",
    "type": "file",
    "content": {
      "deleted_file_id": "some-file-id",
      "filename": "the-original-filename.ext"
    }
  }
}
```

The `"role": "system"` message can be used to reflect that the server performed the deletion. The client can listen for `"file_deleted"` to remove the file from its UI.

---

## 4. Unknown Actions

When `"action"` is present but not recognized:

```json
{
  "action": "some_unhandled_action"
}
```

the server sends:

```json
{
  "error": "Unknown action: some_unhandled_action"
}
```

---

## 5. Disconnection & Persistence

When the **WebSocket disconnects**:

- **`ws_disconnect.py`** → `persist_on_disconnect(...)` runs:
  1. Takes the in-memory conversation messages and inserts them into the `ChatConversation` table.
  2. Commits the DB transaction.
  3. Closes the WebSocket.

Thus, any newly added messages not yet in the DB are saved before the connection is fully terminated.

