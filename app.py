from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from pymongo import MongoClient
from datetime import datetime, timedelta
import pytz
import random
import string
import os
from dotenv import load_dotenv

load_dotenv()

# Set timezone to Asia/Kolkata
TIMEZONE = pytz.timezone('Asia/Kolkata')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Initialize SocketIO with CORS support
socketio = SocketIO(app, cors_allowed_origins="*")

# MongoDB setup
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'scribe_chat')

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
    message = request.args.get('message', 'An error occurred')
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
            'is_code_visible': True,
            'created_at': datetime.now(TIMEZONE),
            'last_active_at': datetime.now(TIMEZONE)
        }
        
        rooms_collection.insert_one(room_doc)
        
        return jsonify({'success': True, 'room_code': room_code})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/validate_room', methods=['POST'])
def validate_room():
    """Validate if a room code exists and has space"""
    try:
        data = request.json
        room_code = data.get('room_code', '').strip().upper()
        
        if not room_code:
            return jsonify({'valid': False, 'reason': 'Room code is required'})
        
        room = rooms_collection.find_one({'room_code': room_code})
        
        if not room:
            return jsonify({'valid': False, 'reason': 'Room not found'})
        
        if len(room.get('members', [])) >= 5:
            return jsonify({'valid': False, 'reason': 'Room is full'})
        
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
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')
    
    # Find and update room where this user was a member
    room = rooms_collection.find_one({'members.sid': request.sid})
    
    if room:
        room_code = room['room_code']
        
        # Find the member who disconnected
        member = next((m for m in room['members'] if m['sid'] == request.sid), None)
        
        if member:
            username = member['username']
            
            # Remove member from room
            rooms_collection.update_one(
                {'room_code': room_code},
                {'$pull': {'members': {'sid': request.sid}}}
            )
            
            # Check if room is now empty
            updated_room = rooms_collection.find_one({'room_code': room_code})
            
            if not updated_room['members']:
                # Delete empty room
                rooms_collection.delete_one({'room_code': room_code})
                print(f'Deleted empty room: {room_code}')
            else:
                # If disconnected user was host, assign new host
                if room['host_sid'] == request.sid:
                    new_host_sid = updated_room['members'][0]['sid']
                    rooms_collection.update_one(
                        {'room_code': room_code},
                        {'$set': {'host_sid': new_host_sid}}
                    )
                    emit('new_host', {'sid': new_host_sid}, room=room_code)
                
                # Notify others
                emit('system_message', {
                    'text': f'{username} has left the chat.'
                }, room=room_code)
                
                # Send updated user list
                updated_room = rooms_collection.find_one({'room_code': room_code})
                user_list = [{
                    'username': m['username'],
                    'is_host': m['sid'] == updated_room['host_sid']
                } for m in updated_room['members']]
                
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
        if any(m['username'] == username for m in room['members']):
            emit('error', {'message': 'Username already taken in this room'})
            return
        
        # Add member to room
        member = {'username': username, 'sid': request.sid}
        
        # If this is the first member, make them host
        if not room['members']:
            rooms_collection.update_one(
                {'room_code': room_code},
                {
                    '$set': {'host_sid': request.sid},
                    '$push': {'members': member}
                }
            )
        else:
            rooms_collection.update_one(
                {'room_code': room_code},
                {'$push': {'members': member}}
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
        
        # Notify others about new user
        emit('system_message', {
            'text': f'{username} has joined the chat.'
        }, room=room_code, skip_sid=request.sid)
        
        # Send updated user list to all
        user_list = [{
            'username': m['username'],
            'is_host': m['sid'] == updated_room['host_sid']
        } for m in updated_room['members']]
        
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

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
