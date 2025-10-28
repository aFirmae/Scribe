#!/usr/bin/env python3
"""
Cleanup script to delete inactive rooms after 24 hours.
This script should be run periodically (e.g., via cron job or scheduler).
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB setup
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'scribe_chat')

client = MongoClient(MONGODB_URI)
db = client[DATABASE_NAME]
rooms_collection = db['rooms']

def cleanup_inactive_rooms():
    """Delete rooms that have been inactive for more than 24 hours"""
    
    # Calculate the threshold time (24 hours ago)
    threshold = datetime.utcnow() - timedelta(hours=24)
    
    # Find inactive rooms
    inactive_rooms = rooms_collection.find({
        'last_active_at': {'$lt': threshold}
    })
    
    deleted_count = 0
    
    for room in inactive_rooms:
        room_code = room['room_code']
        print(f"Deleting inactive room: {room_code}")
        
        rooms_collection.delete_one({'_id': room['_id']})
        deleted_count += 1
    
    if deleted_count > 0:
        print(f"✓ Deleted {deleted_count} inactive room(s)")
    else:
        print("No inactive rooms to delete")
    
    return deleted_count

if __name__ == '__main__':
    print(f"Running cleanup at {datetime.utcnow().isoformat()}")
    cleanup_inactive_rooms()
    print("Cleanup completed")
