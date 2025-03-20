# Kafka Backend

Stack
* FastAPI
* SQLite

Methods
* HTTP Requests
* Websockets

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
    |      ┌────────────────┐        ┌────────────────────┐
    |      │     Chat       │        │       File          │
    |      │----------------│        │----------------------│
    |      │ id (PK)        │        │ id (PK)             │
    |      │ name           │        │ filename            │
    |      │ last_updated   │        │ path                │
    |      │ user_id (FK)   │        │ workspace_id (FK)   │
    |      │ workspace_id(FK│        └─────────────────────┘
    |      └────────────────┘
    |               | 1..M
    |               |  
    |          ┌─────────────────────┐         ┌───────────────────────┐
    |          │   ChatConversation │         │      ChatFile         │
    |          │---------------------│         │------------------------│
    |          │ id (PK)            │         │ id (PK)               │
    |          │ role               │         │ filename               │
    |          │ type               │         │ path                   │
    |          │ content            │         │ chat_id (FK)           │
    |          │ chat_id (FK)       │         └────────────────────────┘
    |          └─────────────────────┘
    |                     |
    |                     | 1..M
    |                     |
    |               ┌─────────────────────────┐
    |               │    ChatFileVersion     │
    |               │-------------------------│
    |               │ id (PK)                │
    |               │ timestamp              │
    |               │ content                │
    |               │ chat_file_id (FK)      │
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



## Endpoint Docs

Below is the updated documentation for the `/auth` endpoint:

---

### `/auth/login`

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