// Chat.js - Client-side Socket.IO and UI logic

// Connect to server
socket.on('connect', () => {
    console.log('Connected to server');
    // Join the room
    socket.emit('join_room', {
        room_code: roomCode,
        username: username
    });
});

// Handle room info
socket.on('room_info', (data) => {
    console.log('Room info received:', data);

    // Update room details
    document.getElementById('roomName').textContent = data.room_name;
    document.getElementById('roomNameMobile').textContent = data.room_name;
    document.getElementById('roomCode').textContent = data.room_code;

    isHost = data.is_host;
    isCodeVisible = data.is_code_visible;

    // Show host controls if user is host
    if (isHost) {
        document.getElementById('hostActions').classList.remove('hidden');
        document.getElementById('nonHostLeaveBtn').classList.add('hidden');
        document.getElementById('editRoomNameBtn').classList.remove('hidden');
        document.getElementById('toggleCodeBtn').classList.remove('hidden');
    } else {
        document.getElementById('hostActions').classList.add('hidden');
        document.getElementById('nonHostLeaveBtn').classList.remove('hidden');
    }

    // Update code visibility
    updateCodeVisibility(isCodeVisible);

    // Add welcome message
    addSystemMessage(`Welcome to ${data.room_name}!`);
});

// Handle user list updates
socket.on('update_user_list', (users) => {
    console.log('User list updated:', users);

    const userListDiv = document.getElementById('userList');
    userListDiv.innerHTML = '';

    users.forEach(user => {
        const userDiv = document.createElement('div');
        const opacityClass = user.is_active ? '' : 'opacity-50';
        userDiv.className = `flex items-center space-x-3 p-3 bg-gray-700/30 rounded-lg hover:bg-gray-700/50 transition-colors ${opacityClass}`;

        const statusIndicator = user.is_active 
            ? '<span class="w-2.5 h-2.5 rounded-full bg-emerald-500 border-2 border-gray-800 absolute bottom-0 right-0"></span>'
            : '<span class="w-2.5 h-2.5 rounded-full bg-gray-500 border-2 border-gray-800 absolute bottom-0 right-0"></span>';

        userDiv.innerHTML = `
            <div class="relative">
                <div class="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-emerald-600 to-emerald-500 flex items-center justify-center text-white font-semibold">
                    ${user.username.charAt(0).toUpperCase()}
                </div>
                ${statusIndicator}
            </div>
            <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-300 truncate">
                    ${user.username}
                    ${user.username === username ? ' (You)' : ''}
                    ${!user.is_active ? ' (Away)' : ''}
                </p>
            </div>
            ${user.is_host ? '<i class="fas fa-crown text-yellow-400" title="Host"></i>' : ''}
        `;

        userListDiv.appendChild(userDiv);
    });

    // Update user count
    document.getElementById('userCount').textContent = users.length;
    document.getElementById('userCountMobile').textContent = users.length;
});

// Handle incoming messages
socket.on('receive_message', (data) => {
    console.log('Message received:', data);
    addMessage(data);
});

// Handle system messages
socket.on('system_message', (data) => {
    console.log('System message:', data);
    addSystemMessage(data.text);
});

// Handle room updates
socket.on('room_updated', (data) => {
    console.log('Room updated:', data);

    if (data.key === 'room_name') {
        document.getElementById('roomName').textContent = data.value;
        document.getElementById('roomNameMobile').textContent = data.value;
    } else if (data.key === 'is_code_visible') {
        isCodeVisible = data.value;
        updateCodeVisibility(data.value);
    }
});

// Handle new host assignment
socket.on('new_host', (data) => {
    if (socket.id === data.sid) {
        isHost = true;
        document.getElementById('hostActions').classList.remove('hidden');
        document.getElementById('nonHostLeaveBtn').classList.add('hidden');
        document.getElementById('editRoomNameBtn').classList.remove('hidden');
        document.getElementById('toggleCodeBtn').classList.remove('hidden');
        addSystemMessage('You are now the host of this room.');
    }
    
    // Clear grace period banner if it was active
    clearGracePeriodTimer();
});

// Handle grace period start
socket.on('host_disconnect_grace', (data) => {
    console.log('Host disconnected, grace period started:', data);
    showGracePeriodBanner(data.seconds_left, data.username);
});

// Handle host return
socket.on('host_returned', () => {
    console.log('Host returned');
    clearGracePeriodTimer();
    addSystemMessage('The host has reconnected.');
});

// Handle room deletion
socket.on('room_deleted', (data) => {
    // Redirect to error page showing the room was deleted
    window.location.href = '/error?message=' + encodeURIComponent(data.message || 'This room has been deleted by the host');
});

// Handle errors
socket.on('error', (data) => {
    console.error('Socket error:', data);

    // For critical errors (room not found, room full), redirect to error page
    if (data.message.includes('not found')) {
        window.location.href = '/error?message=' + encodeURIComponent('Room not found');
    } else if (data.message.includes('full')) {
        window.location.href = '/error?message=' + encodeURIComponent('Room is full');
    } else {
        // For other errors, show as system message
        addSystemMessage('Error: ' + data.message);
    }
});

// Message form submission
document.getElementById('messageForm').addEventListener('submit', (e) => {
    e.preventDefault();

    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();

    if (!message) return;

    // Send message to server
    socket.emit('send_message', {
        room_code: roomCode,
        message: message
    });

    // Clear input
    messageInput.value = '';
    messageInput.style.height = 'auto';
    messageInput.focus();
});

// Copy room code
document.getElementById('copyCodeBtn').addEventListener('click', () => {
    const roomCodeText = document.getElementById('roomCode').textContent;
    navigator.clipboard.writeText(roomCodeText).then(() => {
        // Show feedback
        const btn = document.getElementById('copyCodeBtn');
        const icon = btn.querySelector('i');
        icon.classList.remove('fa-copy');
        icon.classList.add('fa-check');

        setTimeout(() => {
            icon.classList.remove('fa-check');
            icon.classList.add('fa-copy');
        }, 2000);
    });
});

// Edit room name
document.getElementById('editRoomNameBtn').addEventListener('click', () => {
    const currentName = document.getElementById('roomName').textContent;
    document.getElementById('newRoomName').value = currentName;
    document.getElementById('editRoomModal').classList.remove('hidden');
    document.getElementById('newRoomName').focus();
});

function closeEditRoomModal() {
    document.getElementById('editRoomModal').classList.add('hidden');
}

document.getElementById('editRoomForm').addEventListener('submit', (e) => {
    e.preventDefault();

    const newName = document.getElementById('newRoomName').value.trim();

    if (!newName) return;

    socket.emit('host_action', {
        room_code: roomCode,
        action: 'rename_room',
        payload: newName
    });

    closeEditRoomModal();
});

// Toggle code visibility
document.getElementById('toggleCodeBtn').addEventListener('click', () => {
    const newVisibility = !isCodeVisible;

    socket.emit('host_action', {
        room_code: roomCode,
        action: 'toggle_code_visibility',
        payload: newVisibility
    });
});

// Delete room
document.getElementById('deleteRoomBtn').addEventListener('click', () => {
    if (confirm('Are you sure you want to delete this room? All participants will be disconnected.')) {
        socket.emit('host_action', {
            room_code: roomCode,
            action: 'delete_room'
        });
    }
});

// UI Helper Functions

function addMessage(data) {
    const messagesContainer = document.getElementById('messagesContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message-enter';

    const isOwn = data.is_own;
    const alignment = isOwn ? 'justify-end' : 'justify-start';

    const timestamp = new Date(data.timestamp).toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });

    messageDiv.innerHTML = `
        <div class="flex ${alignment} mb-2">
            <div class="max-w-[70%] ${isOwn ? 'order-2' : 'order-1'}">
                ${!isOwn ? `<p class="text-xs font-medium text-emerald-500 mb-1 ml-2">${escapeHtml(data.username)}</p>` : ''}
                <div class="${isOwn ? 'bg-emerald-600 text-white shadow-lg' : 'bg-gray-700/50 text-gray-200 border border-gray-600/30'} rounded-2xl px-4 py-2.5 shadow-sm">
                    <p class="text-sm whitespace-pre-wrap break-words leading-relaxed">${escapeHtml(data.message)}</p>
                </div>
                <p class="text-[10px] text-gray-500 mt-1 ${isOwn ? 'text-right' : 'text-left'} ${isOwn ? 'mr-2' : 'ml-2'}">
                    ${timestamp}
                </p>
            </div>
        </div>
    `;

    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

function addSystemMessage(text) {
    const messagesContainer = document.getElementById('messagesContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message-enter flex justify-center my-4';

    messageDiv.innerHTML = `
        <div class="bg-gray-800/50 border border-gray-700/50 text-gray-400 text-xs px-4 py-1.5 rounded-full backdrop-blur-sm">
            <i class="fas fa-info-circle mr-1.5 text-gray-500"></i>${escapeHtml(text)}
        </div>
    `;

    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

function scrollToBottom() {
    const messagesContainer = document.getElementById('messagesContainer');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function updateCodeVisibility(visible) {
    const icon = document.getElementById('codeVisibilityIcon');
    const roomCodeElement = document.getElementById('roomCode');

    if (!visible) {
        roomCodeElement.textContent = '••••••';
        document.getElementById('copyCodeBtn').style.display = 'none';
        
        // Host can still see the toggle button
        if (isHost) {
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        }
    } else {
        roomCodeElement.textContent = roomCode;
        document.getElementById('copyCodeBtn').style.display = 'inline-block';

        if (isHost) {
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
        }
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeEditRoomModal();
    }
});

// Close modal on background click
document.getElementById('editRoomModal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) {
        closeEditRoomModal();
    }
});

// Handle disconnection
socket.on('disconnect', () => {
    console.log('Disconnected from server');
    addSystemMessage('Disconnected from server!');
});

socket.on('reconnect', () => {
    console.log('Reconnected to server');
    addSystemMessage('Reconnected to server!');

    // Rejoin room
    socket.emit('join_room', {
        room_code: roomCode,
        username: username
    });
});

let gracePeriodInterval;

function showGracePeriodBanner(seconds, oldHostName) {
    const banner = document.getElementById('gracePeriodBanner');
    const textElement = document.getElementById('gracePeriodText');
    
    banner.classList.remove('hidden');
    
    let timeLeft = seconds;
    
    // Update immediately
    updateTimerText(timeLeft);
    
    // Clear existing interval
    if (gracePeriodInterval) clearInterval(gracePeriodInterval);
    
    // Start countdown
    gracePeriodInterval = setInterval(() => {
        timeLeft--;
        
        if (timeLeft <= 0) {
            clearInterval(gracePeriodInterval);
            banner.classList.add('hidden');
        } else {
            updateTimerText(timeLeft);
        }
    }, 1000);
    
    function updateTimerText(sec) {
        const minutes = Math.floor(sec / 60);
        const remainingSeconds = Math.floor(sec % 60);
        textElement.textContent = `${oldHostName} disconnected. New host in ${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
}

function clearGracePeriodTimer() {
    const banner = document.getElementById('gracePeriodBanner');
    banner.classList.add('hidden');
    if (gracePeriodInterval) clearInterval(gracePeriodInterval);
}
