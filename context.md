## **Project Context: "Scribe" - A Real-Time Lobby-Based Chat Application**

This document outlines the scope, design, and technical architecture for **Scribe**, a minimalist, real-time web chat application. The core concept is simplicity and ephemerality, where users can quickly create or join temporary chat rooms using a unique code.

---

### **1. Core Philosophy & User Experience (UI/UX)**

The primary goal is to provide a beautiful, intuitive, and clutter-free user experience. The design will be modern, clean, and fully responsive, ensuring a seamless experience on desktops, tablets, and mobile devices.

- **Minimalism:** The feature set is intentionally limited to the essentials of creating, joining, and participating in a chat.
- **Simplicity:** The user journey from landing on the homepage to chatting in a room should take no more than two clicks and a few keystrokes.
- **Aesthetics:** A visually pleasing interface using Tailwind CSS for a modern utility-first design, complemented by FontAwesome for crisp, recognizable icons. A pleasant color palette and generous spacing will be used to enhance readability and usability.

---

### **2. Feature Breakdown**

#### **2.1. Homepage**

- A centered, full-screen landing page.
- A clear and concise title, e.g., "ChatSphere".
- Two prominent, primary action buttons:
  1. **[`<i class="fa-solid fa-plus"></i>` Create Room]**
  2. **[`<i class="fa-solid fa-users"></i>` Join Room]**

#### **2.2. Room Creation**

1. User clicks "Create Room".
2. A modal or an inline form prompts the user for a **Username**.
3. Upon submitting, the backend:
   - Generates a unique, random 6-character room code (alphanumeric, uppercase: `A-Z`, `0-9`).
   - Creates a new room document in the database.
   - Designates the creator as the **Host**.
   - Redirects the user to the chat room URL (e.g., `/chat/ABC123`).

#### **2.3. Room Joining**

1. User clicks "Join Room".
2. A modal or an inline form prompts for two fields: **Room Code** and **Username**.
3. Input validation will be performed on the frontend and backend.
4. The backend verifies:
   - Does the room code exist?
   - Is the room at its maximum capacity (5 users)?
5. If valid and not full, the user is redirected to the chat room. Otherwise, an error message is displayed (e.g., "Room not found" or "Room is full").

#### **2.4. The Chat Room**

This is the main interface of the application.

- **Responsive Layout:**

  - **Desktop:** A two-column layout.
    - **Left Sidebar:** Room Information, User List, Host Controls.
    - **Right Main Area:** Chat message display and input form.
  - **Mobile:** The left sidebar collapses into an off-canvas menu or a modal, accessible via a "menu" or "users" icon, prioritizing the chat view.
- **Room Information & Controls (Sidebar):**

  - **Room Name:** Displayed at the top. The Host sees an "edit" icon to change it.
  - **Room Code:**
    - Displayed clearly (e.g., `CODE: ABC123`).
    - A **Copy Icon** (`<i class="fa-solid fa-copy"></i>`) next to it copies the code to the clipboard.
    - A **Toggle Switch** or **Icon** (`<i class="fa-solid fa-eye"></i>` / `<i class="fa-solid fa-eye-slash"></i>`) for the Host to show/hide the code for other members.
  - **User List:** A list of participants (max 5). The Host is visually distinguished with a crown icon (`<i class="fa-solid fa-crown"></i>`).
  - **Host Actions:** A "Delete Room" button (with a trash icon) is visible only to the Host. Clicking it will close the room for all participants and delete it from the database.
- **Chat Interface (Main Area):**

  - **Message Display:** A scrollable container that automatically scrolls to the bottom on new messages.
    - **Own Messages:** Aligned to the right, with a distinct background color.
    - **Other's Messages:** Aligned to the left.
    - **Message Structure:** Each message bubble will show the sender's username, the message content, and a timestamp.
    - **System Messages:** Centered and styled differently to announce events like "User [X] has joined," "User [Y] has left," or "Host changed the room name to [New Name]".
  - **Message Input:**
    - A fixed-position form at the bottom of the chat area.
    - A `textarea` that can grow slightly to accommodate multi-line messages.
    - A "Send" button with a paper plane icon (`<i class="fa-solid fa-paper-plane"></i>`). Pressing `Enter` will send the message; `Shift+Enter` will create a new line.

#### **2.5. Room Lifecycle**

- **Capacity:** A hard limit of 5 members per room.
- **Host Deletion:** The host can delete the room at any time.
- **Automatic Expiry:** A room and all its associated chat history will be automatically deleted from the database if it remains inactive for 24 hours. Inactivity is defined as no new user joins or messages sent.

---

### **3. Technology Stack**

- **Frontend:**

  - **HTML5:** For semantic structure.
  - **Tailwind CSS:** For a modern, utility-first, responsive design.
  - **JavaScript (Vanilla):** For DOM manipulation, event handling, and communication with the backend.
  - **FontAwesome:** For all icons used throughout the UI.
  - **Socket.IO Client:** JavaScript library to handle real-time, bidirectional communication.
- **Backend:**

  - **Framework:** **Flask** (Python).
  - **Real-time Engine:** **Flask-SocketIO**, which integrates Socket.IO with Flask.
  - **Database:** **MongoDB**, a NoSQL database perfect for storing flexible, document-based data like chat rooms. `PyMongo` will be the Python driver.
  - **WSGI Server:** Gunicorn or a similar production-grade server.

---

### **4. Data Model (MongoDB Schema)**

A single collection `rooms` will be used.

```json
// Collection: "rooms"
{
  "_id": ObjectId("..."),
  "room_code": "ABC123", // 6-char, indexed, unique
  "room_name": "Team Meeting", // String, can be edited by host
  "host_sid": "socket_io_session_id_of_host", // Used to identify the host
  "members": [
    { "username": "Alice", "sid": "user_socket_id_1" },
    { "username": "Bob", "sid": "user_socket_id_2" }
  ],
  "is_code_visible": true, // Boolean, controlled by host
  "created_at": ISODate("2023-10-27T10:00:00Z"),
  "last_active_at": ISODate("2023-10-27T11:30:00Z") // Updated on join or new message
}
```

- **`room_code`** will have a unique index to ensure fast lookups.
- **`last_active_at`** is the key field for the automatic deletion logic. A background job will periodically query and delete rooms where `last_active_at` is older than 24 hours.

---

### **5. API Endpoints & Socket.IO Events**

#### **Flask HTTP Routes:**

- `GET /`: Serves the homepage (`index.html`).
- `GET /chat/<room_code>`: Serves the chat room page (`chat.html`). The template will be rendered after server-side validation of the room code.
- `POST /api/create_room`:
  - Request Body: `{"username": "John"}`
  - Response: `{"success": true, "room_code": "XYZ789"}`
- `POST /api/validate_room`:
  - Request Body: `{"room_code": "XYZ789"}`
  - Response: `{"valid": true}` or `{"valid": false, "reason": "Room not found / Room is full"}`

#### **Socket.IO Events:**

- **Client to Server:**

  - `connect`: A user connects.
  - `join_room`: Client sends `{ "room_code": "...", "username": "..." }`. Server adds them to the Socket.IO room and updates the DB.
  - `send_message`: Client sends `{ "room_code": "...", "message": "Hello!" }`.
  - `host_action`: Client sends `{ "room_code": "...", "action": "...", "payload": "..." }`, e.g.,
    - `{ "action": "rename_room", "payload": "New Room Name" }`
    - `{ "action": "toggle_code_visibility", "payload": false }`
    - `{ "action": "delete_room" }`
  - `disconnect`: A user disconnects. Server handles their departure.
- **Server to Client(s) (Broadcasted to a specific room):**

  - `update_user_list`: Sent when a user joins or leaves. Payload: `[ { "username": "Alice", "is_host": true }, ... ]`.
  - `receive_message`: Sent to all users in a room. Payload: `{ "username": "Bob", "message": "Hi there!", "timestamp": "..." }`.
  - `room_updated`: Sent when host changes room name or code visibility. Payload: `{ "key": "room_name", "value": "New Name" }`.
  - `system_message`: Sent to announce joins/leaves. Payload: `{ "text": "Bob has joined the chat." }`.
  - `room_deleted`: Sent to all users just before kicking them, prompting the client-side JS to redirect them to the homepage with a message.
