# Scribe

Scribe is an ephemeral, real-time, lobby-based chat application that lets users create temporary rooms and communicate instantly without sign-ups.

**Live Link:** [scribe.nilashis.in](https://scribe.nilashis.in)

## 1. Functional Requirements

1. Users can open the app in a browser.
2. Users can create a new chat room.
3. Each room gets a unique room code.
4. Users can join a room using the room code.
5. The host can control room settings, code visibility and room name.
6. Users can send and receive messages in real time.
7. The app shows who is currently in the room.
8. Users who disconnect temporarily can rejoin within 30s without losing data.
9. Chat messages are saved so late joiners can see past messages.
10. Empty or inactive rooms are automatically deleted after a fixed time.

## 2. Non-Functional Requirements

1. Messages should appear instantly (low latency).
2. The system should handle multiple users at the same time.
3. Data should not be lost if the server restarts.
4. Temporary network failures should not break the app.
5. The app should clean up unused data automatically.
6. Room lookup should be very fast.
7. The system should be easy to scale later.
8. Background tasks should not block user actions.
9. The backend should stay responsive even during cleanup.
10. The design should be simple and maintainable.

## 3. Database Schema

This is **one document per room**.

```json
{
  "_id": ObjectId("..."),

  "room_code": "X7K9P2",
  "room_name": "Nilashis's Room",

  "host_sid": "session_id_of_host",

  "is_code_visible": false,

  "members": [
    {
      "username": "Nilashis",
      "sid": "socket_io_session_id_1",
      "status": "active",
      "last_seen": ISODate("...")
    }
  ],

  "messages": [
    {
      "username": "Nilashis",
      "message": "Hello",
      "timestamp": "..."
    }
  ],

  "created_at": ISODate("..."),
  "last_active_at": ISODate("...")
}
```
