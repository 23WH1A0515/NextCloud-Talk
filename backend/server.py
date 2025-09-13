from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    avatar_url: Optional[str] = None
    is_online: bool = True

class Room(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    participants: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    unread_count: int = 0

class Reaction(BaseModel):
    emoji: str
    user_id: str
    username: str

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    room_id: str
    sender_id: str
    sender_name: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reactions: List[Reaction] = []
    is_system: bool = False

class MessageCreate(BaseModel):
    room_id: str
    content: str

class ReactionCreate(BaseModel):
    message_id: str
    emoji: str

class SummaryResponse(BaseModel):
    summary_points: List[str]
    message_count: int
    time_range: str

# Mock data initialization
async def init_mock_data():
    # Check if data already exists
    room_count = await db.rooms.count_documents({})
    if room_count > 0:
        return
    
    # Create mock users
    users = [
        {"id": "user1", "username": "Alice Johnson", "avatar_url": None, "is_online": True},
        {"id": "user2", "username": "Bob Smith", "avatar_url": None, "is_online": True},
        {"id": "user3", "username": "Carol Davis", "avatar_url": None, "is_online": False},
        {"id": "current_user", "username": "You", "avatar_url": None, "is_online": True}
    ]
    await db.users.insert_many(users)
    
    # Create mock rooms
    rooms = [
        {
            "id": "room1",
            "name": "General Discussion",
            "description": "Main team chat",
            "participants": ["user1", "user2", "user3", "current_user"],
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "unread_count": 3
        },
        {
            "id": "room2", 
            "name": "Project Alpha",
            "description": "Alpha project coordination",
            "participants": ["user1", "current_user"],
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "unread_count": 1
        },
        {
            "id": "room3",
            "name": "Random",
            "description": "Casual conversations",
            "participants": ["user2", "user3", "current_user"],
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "unread_count": 0
        }
    ]
    await db.rooms.insert_many(rooms)
    
    # Create mock messages
    messages = [
        {
            "id": "msg1",
            "room_id": "room1",
            "sender_id": "user1",
            "sender_name": "Alice Johnson",
            "content": "Hey everyone! How's the project coming along?",
            "timestamp": datetime.now(timezone.utc),
            "reactions": [{"emoji": "👍", "user_id": "user2", "username": "Bob Smith"}],
            "is_system": False
        },
        {
            "id": "msg2",
            "room_id": "room1", 
            "sender_id": "user2",
            "sender_name": "Bob Smith",
            "content": "Making good progress! Just finished the backend API.",
            "timestamp": datetime.now(timezone.utc),
            "reactions": [{"emoji": "🚀", "user_id": "user1", "username": "Alice Johnson"}],
            "is_system": False
        },
        {
            "id": "msg3",
            "room_id": "room1",
            "sender_id": "user3", 
            "sender_name": "Carol Davis",
            "content": "Awesome work team! Frontend is looking great too.",
            "timestamp": datetime.now(timezone.utc),
            "reactions": [],
            "is_system": False
        },
        {
            "id": "msg4",
            "room_id": "room2",
            "sender_id": "user1",
            "sender_name": "Alice Johnson", 
            "content": "Can we schedule a review meeting for tomorrow?",
            "timestamp": datetime.now(timezone.utc),
            "reactions": [],
            "is_system": False
        }
    ]
    await db.messages.insert_many(messages)

# API Routes
@api_router.get("/")
async def root():
    return {"message": "NextTalk Dash API"}

@api_router.get("/rooms", response_model=List[Room])
async def get_rooms():
    rooms = await db.rooms.find().to_list(100)
    return [Room(**room) for room in rooms]

@api_router.get("/rooms/{room_id}/messages", response_model=List[Message])
async def get_messages(room_id: str, limit: int = 50):
    messages = await db.messages.find({"room_id": room_id}).sort("timestamp", -1).limit(limit).to_list(limit)
    messages.reverse()  # Show oldest first
    return [Message(**message) for message in messages]

@api_router.post("/messages", response_model=Message)
async def send_message(message_data: MessageCreate):
    # Create new message
    message_dict = {
        "id": str(uuid.uuid4()),
        "room_id": message_data.room_id,
        "sender_id": "current_user",
        "sender_name": "You",
        "content": message_data.content,
        "timestamp": datetime.now(timezone.utc),
        "reactions": [],
        "is_system": False
    }
    
    message_obj = Message(**message_dict)
    await db.messages.insert_one(message_obj.dict())
    
    # Update room last activity
    await db.rooms.update_one(
        {"id": message_data.room_id},
        {"$set": {"last_activity": datetime.now(timezone.utc)}}
    )
    
    return message_obj

@api_router.post("/reactions")
async def add_reaction(reaction_data: ReactionCreate):
    # Check if reaction already exists
    message = await db.messages.find_one({"id": reaction_data.message_id})
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Remove existing reaction from this user if it exists
    existing_reactions = [r for r in message.get("reactions", []) if r["user_id"] != "current_user"]
    
    # Add new reaction
    new_reaction = {
        "emoji": reaction_data.emoji,
        "user_id": "current_user", 
        "username": "You"
    }
    existing_reactions.append(new_reaction)
    
    # Update message with new reactions
    await db.messages.update_one(
        {"id": reaction_data.message_id},
        {"$set": {"reactions": existing_reactions}}
    )
    
    return {"success": True}

@api_router.get("/summary/{room_id}", response_model=SummaryResponse)
async def get_chat_summary(room_id: str):
    # Mock AI summary - predefined responses based on room
    mock_summaries = {
        "room1": [
            "Team discussed project progress with positive updates",
            "Backend API development completed successfully",
            "Frontend development showing good progress",
            "Overall team morale is high and collaborative",
            "No major blockers or issues identified"
        ],
        "room2": [
            "Project Alpha coordination meeting scheduled",
            "Review meeting requested for tomorrow",
            "Timeline appears to be on track",
            "Team alignment on project deliverables",
            "Next steps clearly defined"
        ],
        "room3": [
            "Casual team conversations",
            "Light-hearted discussions about work-life balance",
            "Team bonding and social interactions",
            "Informal knowledge sharing",
            "Positive team culture evident"
        ]
    }
    
    summary_points = mock_summaries.get(room_id, [
        "Recent conversations in this room",
        "Various topics discussed by team members", 
        "Active participation from multiple users",
        "Collaborative communication observed",
        "Regular team interactions maintained"
    ])
    
    return SummaryResponse(
        summary_points=summary_points,
        message_count=50,
        time_range="Last 24 hours"
    )

@api_router.post("/rooms/{room_id}/mark-read")
async def mark_room_as_read(room_id: str):
    await db.rooms.update_one(
        {"id": room_id},
        {"$set": {"unread_count": 0}}
    )
    return {"success": True}

# Initialize mock data on startup
@app.on_event("startup")
async def startup_event():
    await init_mock_data()

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()