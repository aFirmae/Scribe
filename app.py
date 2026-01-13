import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
import random
import string
import os
import threading
import time
from dotenv import load_dotenv

load_dotenv()

# Set timezone to Asia/Kolkata
TIMEZONE = pytz.timezone('Asia/Kolkata')
GRACE_PERIOD_SECONDS = 600  # 10 minutes

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Initialize SocketIO with CORS support
socketio = SocketIO(app, cors_allowed_origins="*")

# MongoDB setup
MONGODB_URI = os.getenv('MONGODB_URI')
DATABASE_NAME = 'scribe_chat'

client = MongoClient(MONGODB_URI)
db = client[DATABASE_NAME]
rooms_collection = db['rooms']

# Create unique index on room_code
rooms_collection.create_index('room_code', unique=True)

def generate_room_code():
    """Generate a unique 6-character alphanumeric room code"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not rooms_collection.find_one({'room_code': code}):
            return code

def update_room_activity(room_code):
    """Update the last_active_at timestamp for a room"""
    rooms_collection.update_one(
        {'room_code': room_code},
        {'$set': {'last_active_at': datetime.now(TIMEZONE)}}
    )

# HTTP Routes
@app.route('/')
def index():
    """Serve the homepage"""
    return render_template('index.html')

@app.route('/error')
def error_page():
    """Serve the error page with custom message"""
    message = request.args.get('message', 'An error occurred. The room may have been deleted or you may have been disconnected.')
    return render_template('error.html', message=message)

@app.route('/chat/<room_code>')
def chat_room(room_code):
    """Serve the chat room page"""
    room = rooms_collection.find_one({'room_code': room_code.upper()})
    if not room:
        return render_template('error.html', message='Room not found'), 404
    
    if len(room.get('members', [])) >= 5:
        return render_template('error.html', message='Room is full'), 403
    
    return render_template('chat.html', room_code=room_code.upper())

@app.route('/api/create_room', methods=['POST'])
def create_room():
    """Create a new chat room"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        
        if not username:
            return jsonify({'success': False, 'error': 'Username is required'}), 400
        
        room_code = generate_room_code()
        
        room_doc = {
            'room_code': room_code,
            'room_name': f"{username}'s Room",
            'host_sid': None,  # Will be set when host connects via socket
            'members': [],
            'messages': [],  # Store chat history
            'is_code_visible': False,
            'created_at': datetime.now(TIMEZONE),
            'last_active_at': datetime.now(TIMEZONE)
        }
        
        rooms_collection.insert_one(room_doc)
        
        return jsonify({'success': True, 'room_code': room_code})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/validate_room', methods=['POST'])
def validate_room():
    """Validate if a room code exists, has space, and username is available"""
    try:
        data = request.json
        room_code = data.get('room_code', '').strip().upper()
        username = data.get('username', '').strip()
        
        if not room_code:
            return jsonify({'valid': False, 'reason': 'Room code is required'})
        
        room = rooms_collection.find_one({'room_code': room_code})
        
        if not room:
            return jsonify({'valid': False, 'reason': 'Room not found'})
        
        if len(room.get('members', [])) >= 5:
            return jsonify({'valid': False, 'reason': 'Room is full'})
        
        # Check if username is provided
        # if username:
        #     if any(m['username'] == username for m in room.get('members', [])):
        #         return jsonify({'valid': False, 'reason': 'Username already taken in this room'})
        
        return jsonify({'valid': True})
    
    except Exception as e:
        return jsonify({'valid': False, 'reason': str(e)})

# Socket.IO Event Handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection with grace period"""
    print(f'Client disconnected: {request.sid}')
    
    # Find room where this user is a member
    room = rooms_collection.find_one({'members.sid': request.sid})
    
    if room:
        room_code = room['room_code']
        
        # Update member status to disconnected
        rooms_collection.update_one(
            {'room_code': room_code, 'members.sid': request.sid},
            {'$set': {
                'members.$.status': 'disconnected',
                'members.$.last_seen': datetime.now(TIMEZONE)
            }}
        )
        
        # Get updated room to check host status
        room = rooms_collection.find_one({'room_code': room_code})
        member = next((m for m in room['members'] if m['sid'] == request.sid), None)
        
        if member:
            username = member['username']
            
            # If host disconnected, notify others about potential transfer
            if room['host_sid'] == request.sid:
                emit('system_message', {
                    'text': f'Host {username} has disconnected. Room will close or transfer host in 10 minutes.'
                }, room=room_code)
                
                emit('host_disconnect_grace', {
                    'username': username,
                    'is_host_disconnect': True,
                    'seconds_left': GRACE_PERIOD_SECONDS
                }, room=room_code)

            # Update user list to show disconnected status
            user_list = []
            for m in room['members']:
                is_active = m.get('status', 'active') == 'active'
                user_list.append({
                    'username': m['username'],
                    'is_host': m['sid'] == room['host_sid'],
                    'is_active': is_active
                })
            
            emit('update_user_list', user_list, room=room_code)

@socketio.on('join_room')
def handle_join_room(data):
    """Handle user joining a room"""
    try:
        room_code = data['room_code'].upper()
        username = data['username'].strip()
        
        room = rooms_collection.find_one({'room_code': room_code})
        
        if not room:
            emit('error', {'message': 'Room not found'})
            return
        
        if len(room['members']) >= 5:
            emit('error', {'message': 'Room is full'})
            return
        
        # Check if username already exists in room
        existing_member = next((m for m in room['members'] if m['username'] == username), None)
        
        member_data = {
            'username': username,
            'sid': request.sid,
            'status': 'active',
            'last_seen': datetime.now(TIMEZONE)
        }
        
        is_reconnect = False
        
        if existing_member:
            # User is rejoining
            rooms_collection.update_one(
                {'room_code': room_code, 'members.username': username},
                {'$set': {
                    'members.$.sid': request.sid,
                    'members.$.status': 'active',
                    'members.$.last_seen': datetime.now(TIMEZONE)
                }}
            )
            is_reconnect = True
            
            # If they were host, update host_sid
            if room['host_sid'] == existing_member['sid']: # Check against old SID
                rooms_collection.update_one(
                    {'room_code': room_code},
                    {'$set': {'host_sid': request.sid}}
                )
                emit('host_returned', {}, room=room_code)
        else:
            # New member
            # If this is the first member (or all others are disconnected/gone), make them host
            # actually logic: if no host_sid or host is invalid, or just simple first join
            is_first = not room['members']
            
            if is_first:
                rooms_collection.update_one(
                    {'room_code': room_code},
                    {
                        '$set': {'host_sid': request.sid},
                        '$push': {'members': member_data}
                    }
                )
            else:
                rooms_collection.update_one(
                    {'room_code': room_code},
                    {'$push': {'members': member_data}}
                )
        
        # Join Socket.IO room
        join_room(room_code)
        
        # Update activity
        update_room_activity(room_code)
        
        # Get updated room data
        updated_room = rooms_collection.find_one({'room_code': room_code})
        
        # Send room info to the joining user
        emit('room_info', {
            'room_name': updated_room['room_name'],
            'room_code': room_code,
            'is_code_visible': updated_room['is_code_visible'],
            'is_host': request.sid == updated_room['host_sid'],
            'username': username
        })
        
        # Check if host is currently disconnected
        host_sid = updated_room.get('host_sid')
        host_member = next((m for m in updated_room['members'] if m['sid'] == host_sid), None)
        
        if host_member and host_member.get('status') == 'disconnected':
            last_seen = host_member.get('last_seen', datetime.min.replace(tzinfo=TIMEZONE))
            # Ensure last_seen is timezone aware
            if last_seen.tzinfo is None:
                last_seen = pytz.utc.localize(last_seen).astimezone(TIMEZONE)
                
            elapsed = (datetime.now(TIMEZONE) - last_seen).total_seconds()
            remaining = max(0, GRACE_PERIOD_SECONDS - elapsed)
            
            if remaining > 0:
                emit('host_disconnect_grace', {
                    'username': host_member['username'],
                    'is_host_disconnect': True,
                    'seconds_left': remaining
                }, room=request.sid) # Send only to the joining user
        
        # Send chat history (last 50 messages)
        history = updated_room.get('messages', [])[-50:]
        emit('chat_history', history)

        # Notify others
        if is_reconnect:
             emit('system_message', {
                'text': f'{username} has reconnected.'
            }, room=room_code, skip_sid=request.sid)
        else:
            emit('system_message', {
                'text': f'{username} has joined the chat.'
            }, room=room_code, skip_sid=request.sid)
        
        # Send updated user list to all
        user_list = []
        for m in updated_room['members']:
            is_active = m.get('status', 'active') == 'active'
            user_list.append({
                'username': m['username'],
                'is_host': m['sid'] == updated_room['host_sid'],
                'is_active': is_active
            })
        
        emit('update_user_list', user_list, room=room_code)
        
    except Exception as e:
        print(f'Error in join_room: {e}')
        emit('error', {'message': 'Failed to join room'})

@socketio.on('send_message')
def handle_send_message(data):
    """Handle sending a chat message"""
    try:
        room_code = data['room_code'].upper()
        message = data['message'].strip()
        
        if not message:
            return
        
        room = rooms_collection.find_one({'room_code': room_code})
        
        if not room:
            emit('error', {'message': 'Room not found'})
            return
        
        # Find sender
        sender = next((m for m in room['members'] if m['sid'] == request.sid), None)
        
        if not sender:
            emit('error', {'message': 'You are not in this room'})
            return
        
        # Update activity
        update_room_activity(room_code)
        
        # Broadcast message to room
        message_data = {
            'username': sender['username'],
            'message': message,
            'timestamp': datetime.now(TIMEZONE).isoformat(),
            'is_own': False
        }
        
        # Save to database
        rooms_collection.update_one(
            {'room_code': room_code},
            {'$push': {'messages': {
                'username': sender['username'],
                'message': message,
                'timestamp': message_data['timestamp']
            }}}
        )
        
        emit('receive_message', message_data, room=room_code, skip_sid=request.sid)
        
        # Send back to sender with is_own flag
        message_data['is_own'] = True
        emit('receive_message', message_data)
        
    except Exception as e:
        print(f'Error in send_message: {e}')
        emit('error', {'message': 'Failed to send message'})

@socketio.on('host_action')
def handle_host_action(data):
    """Handle host-specific actions"""
    try:
        room_code = data['room_code'].upper()
        action = data['action']
        
        room = rooms_collection.find_one({'room_code': room_code})
        
        if not room:
            emit('error', {'message': 'Room not found'})
            return
        
        # Verify user is host
        if room['host_sid'] != request.sid:
            emit('error', {'message': 'Only the host can perform this action'})
            return
        
        if action == 'rename_room':
            new_name = data.get('payload', '').strip()
            if new_name:
                rooms_collection.update_one(
                    {'room_code': room_code},
                    {'$set': {'room_name': new_name}}
                )
                
                emit('room_updated', {
                    'key': 'room_name',
                    'value': new_name
                }, room=room_code)
                
                emit('system_message', {
                    'text': f'Host changed the room name to "{new_name}"'
                }, room=room_code)
        
        elif action == 'toggle_code_visibility':
            is_visible = data.get('payload', True)
            rooms_collection.update_one(
                {'room_code': room_code},
                {'$set': {'is_code_visible': is_visible}}
            )
            
            emit('room_updated', {
                'key': 'is_code_visible',
                'value': is_visible
            }, room=room_code)
        
        elif action == 'delete_room':
            # Notify all users
            emit('room_deleted', {
                'message': 'The host has closed this room.'
            }, room=room_code)
            
            # Delete room from database
            rooms_collection.delete_one({'room_code': room_code})
            
    except Exception as e:
        print(f'Error in host_action: {e}')
        emit('error', {'message': 'Failed to perform action'})

def check_grace_periods():
    """Background task to check for expired grace periods"""
    while True:
        try:
            # Check every 30 seconds
            time.sleep(30)
            
            # Find rooms with disconnected members
            rooms = rooms_collection.find({'members.status': 'disconnected'})
            
            for room in rooms:
                room_code = room['room_code']
                updated = False
                host_changed = False
                
                # Check each member
                members_to_remove = []
                for member in room['members']:
                    if member.get('status') == 'disconnected':
                        last_seen = member.get('last_seen', datetime.min.replace(tzinfo=TIMEZONE))
                        # Ensure last_seen is timezone aware
                        if last_seen.tzinfo is None:
                            last_seen = pytz.utc.localize(last_seen).astimezone(TIMEZONE)
                            
                        if (datetime.now(TIMEZONE) - last_seen).total_seconds() > GRACE_PERIOD_SECONDS:
                            members_to_remove.append(member['sid'])
                            
                if members_to_remove:
                    # Remove expired members
                    rooms_collection.update_one(
                        {'room_code': room_code},
                        {'$pull': {'members': {'sid': {'$in': members_to_remove}}}}
                    )
                    updated = True
                    
                    # Log removal
                    expired_usernames = [m['username'] for m in room['members'] if m['sid'] in members_to_remove]
                    print(f"Removed expired members from {room_code}: {expired_usernames}")
                    
                # Re-fetch room to check if empty or needs host update
                if updated:
                    updated_room = rooms_collection.find_one({'room_code': room_code})
                    
                    if not updated_room['members']:
                        rooms_collection.delete_one({'room_code': room_code})
                        print(f"Deleted empty room after grace period: {room_code}")
                        continue
                        
                    # Check if host was removed
                    if room['host_sid'] in members_to_remove:
                        # Assign new host (first active member, or just first member)
                        # Prefer active members
                        new_host = next((m for m in updated_room['members'] if m.get('status') == 'active'), updated_room['members'][0])
                        
                        rooms_collection.update_one(
                            {'room_code': room_code},
                            {'$set': {'host_sid': new_host['sid']}}
                        )
                        
                        emit('new_host', {'sid': new_host['sid']}, room=room_code)
                        emit('system_message', {
                            'text': f'Host rights transferred to {new_host["username"]} due to inactivity.'
                        }, room=room_code)
                        host_changed = True
                        
                    # Notify about removals
                    for username in expired_usernames:
                         emit('system_message', {
                            'text': f'{username} was removed due to inactivity.'
                        }, room=room_code)

                    # Send updated list
                    user_list = []
                    for m in updated_room['members']:
                        is_active = m.get('status', 'active') == 'active'
                        user_list.append({
                            'username': m['username'],
                            'is_host': m['sid'] == updated_room['host_sid'], # Use new host sid if changed
                            'is_active': is_active
                        })
                    emit('update_user_list', user_list, room=room_code)
                    
        except Exception as e:
            print(f"Error in grace period checker: {e}")

# Start background thread
bg_thread = threading.Thread(target=check_grace_periods, daemon=True)
bg_thread.start()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000, debug=True, allow_unsafe_werkzeug=True)
