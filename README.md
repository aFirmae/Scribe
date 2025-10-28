# 🗨️ Scribe - Real-Time Chat Application

A beautiful, minimalist real-time chat application built with Flask, Socket.IO, and MongoDB. Create temporary chat rooms with unique codes and connect with up to 5 participants instantly.

![Scribe](https://img.shields.io/badge/Status-Ready-brightgreen)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0.0-lightgrey)
![MongoDB](https://img.shields.io/badge/MongoDB-Required-green)

## ✨ Features

- **🚀 Instant Room Creation**: Generate unique 6-character room codes instantly
- **👥 Multi-User Support**: Up to 5 participants per room
- **💬 Real-Time Messaging**: Powered by Socket.IO for instant message delivery
- **🎨 Beautiful UI**: Modern, elegant design with Tailwind CSS
- **📱 Fully Responsive**: Seamless experience on desktop, tablet, and mobile
- **👑 Host Controls**: Room creators can rename rooms, toggle code visibility, and delete rooms
- **🔒 Privacy-First**: Rooms auto-delete after 24 hours of inactivity
- **🌐 Easy Sharing**: Copy room codes with one click

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+** ([Download](https://www.python.org/downloads/))
- **MongoDB** ([Installation Guide](https://docs.mongodb.com/manual/installation/))
- **pip** (Python package installer, usually comes with Python)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Scribe
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
MONGODB_URI=mongodb://localhost:27017/
DATABASE_NAME=scribe_chat
SECRET_KEY=your-secret-key-here-change-this
FLASK_ENV=development
```

### 5. Start MongoDB

Ensure MongoDB is running on your system:

```bash
# macOS (with Homebrew)
brew services start mongodb-community

# Linux
sudo systemctl start mongod

# Or run manually
mongod --dbpath /path/to/your/data/directory
```

## 🚀 Running the Application

### Development Mode

```bash
python app.py
```

The application will be available at `http://localhost:5000`

### Production Mode

For production, use a production-grade WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
```

## 🧹 Setting Up Room Cleanup

To automatically delete inactive rooms after 24 hours, set up a cron job:

### On macOS/Linux

1. Open your crontab:
```bash
crontab -e
```

2. Add the following line to run cleanup every hour:
```bash
0 * * * * cd /path/to/Scribe && /path/to/venv/bin/python cleanup.py >> cleanup.log 2>&1
```

### Manual Cleanup

You can also run the cleanup script manually:

```bash
python cleanup.py
```

## 📁 Project Structure

```
Scribe/
├── app.py                  # Main Flask application with Socket.IO
├── cleanup.py              # Room cleanup script
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .env                   # Your environment variables (not in git)
├── .gitignore             # Git ignore file
├── context.md             # Project context and specifications
├── README.md              # This file
├── templates/             # HTML templates
│   ├── index.html        # Homepage with create/join options
│   ├── chat.html         # Chat room interface
│   └── error.html        # Error page
└── static/               # Static assets
    └── js/
        └── chat.js       # Client-side Socket.IO logic
```

## 🎮 Usage

### Creating a Room

1. Visit the homepage at `http://localhost:5000`
2. Click **"Create Room"**
3. Enter your username
4. Share the generated room code with others

### Joining a Room

1. Visit the homepage
2. Click **"Join Room"**
3. Enter the 6-character room code
4. Enter your username
5. Start chatting!

### Host Controls

As the room host, you can:

- **Rename the room**: Click the edit icon next to the room name
- **Toggle code visibility**: Show/hide the room code from other members
- **Delete the room**: Remove the room and disconnect all participants

## 🔧 Configuration Options

### MongoDB Connection

Update `MONGODB_URI` in `.env`:

```env
# Local MongoDB
MONGODB_URI=mongodb://localhost:27017/

# MongoDB Atlas (Cloud)
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/

# MongoDB with authentication
MONGODB_URI=mongodb://username:password@localhost:27017/
```

### Database Name

Change the database name in `.env`:

```env
DATABASE_NAME=scribe_chat
```

### Secret Key

Generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Update `SECRET_KEY` in `.env` with the generated value.

## 🌐 Deployment

### Deploy to Heroku

1. Install Heroku CLI and login
2. Create a new Heroku app:
```bash
heroku create your-app-name
```

3. Add MongoDB (MongoDB Atlas add-on):
```bash
heroku addons:create mongolab:sandbox
```

4. Set environment variables:
```bash
heroku config:set SECRET_KEY=your-secret-key
```

5. Deploy:
```bash
git push heroku main
```

### Deploy to Railway

1. Create a new project on [Railway](https://railway.app)
2. Connect your GitHub repository
3. Add MongoDB database service
4. Set environment variables in Railway dashboard
5. Deploy automatically from GitHub

## 🐛 Troubleshooting

### MongoDB Connection Issues

```bash
# Check if MongoDB is running
mongosh  # or mongo for older versions

# Start MongoDB service
brew services start mongodb-community  # macOS
sudo systemctl start mongod           # Linux
```

### Port Already in Use

If port 5000 is occupied, change it in `app.py`:

```python
socketio.run(app, host='0.0.0.0', port=8000, debug=True)
```

### Socket.IO Connection Errors

Ensure you're using `eventlet` as the async mode:

```python
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/)
- Real-time communication via [Socket.IO](https://socket.io/)
- Database powered by [MongoDB](https://www.mongodb.com/)
- UI styled with [Tailwind CSS](https://tailwindcss.com/)
- Icons from [FontAwesome](https://fontawesome.com/)

## 📞 Support

If you encounter any issues or have questions, please:

1. Check the [Troubleshooting](#-troubleshooting) section
2. Review existing issues on GitHub
3. Create a new issue with detailed information

---

Made with ❤️ by the Scribe Team
