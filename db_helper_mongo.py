import pymongo
import hashlib
import json
from datetime import datetime
from model_parameters import get_model_name_from_id, get_style_name_from_id
import os
from bson.objectid import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

# MongoDB connection
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client['kalkimedia']

# Collections
users = db['users']
projects = db['projects']
generations = db['generations']


def init_db():
    """Initialize database with required indexes"""
    # Create indexes
    users.create_index("username", unique=True)
    projects.create_index([("user_id", 1), ("name", 1)], unique=True)
    generations.create_index("user_id")
    generations.create_index("created_at")
    

def create_user(username, password, role, daily_quota):
    """
    Create a new user in MongoDB
    
    Args:
        username: Unique identifier for the user
        password: User's password (will be hashed)
        role: User's role (e.g., 'admin', 'user')
        daily_quota: Number of generations allowed per day
    
    Returns:
        Boolean indicating success or failure
    """
    # Hash the password
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # Create user document
    user_doc = {
        "username": username,
        "password_hash": password_hash,
        "role": role,
        "daily_quota": daily_quota,
        "used_quota": 0,
        "last_generation_time": None,
        "created_at": datetime.utcnow()
    }
    
    try:
        # Insert the user document
        result = users.insert_one(user_doc)
        return result.acknowledged
    except pymongo.errors.DuplicateKeyError:
        # Username already exists
        return False
    except Exception as e:
        print(f"Error creating user: {e}")
        return False

def verify_user(username, password):
    """
    Verify a user's credentials in MongoDB
    
    Args:
        username: Username to verify
        password: Password to verify (will be hashed and compared)
    
    Returns:
        User information dictionary if credentials are valid, None otherwise
    """
    # Hash the password for comparison
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # Query for matching user
    user = users.find_one({
        "username": username,
        "password": password_hash
    })
    
    if user:
        # Return relevant user information
        return {
            "username": user["username"],
            "role": user["role"],
            "daily_quota": user["daily_quota"],
            "used_today": user["used_quota"]
        }
    
    return None

def get_user_usage(username):
    """
    Get the usage statistics for a user from MongoDB
    
    Args:
        username: Username to query usage for
    
    Returns:
        Dictionary with usage information if user exists, None otherwise
    """
    # Query for user by username
    user = users.find_one({"username": username}, {
        "used_quota": 1,
        "last_generation_time": 1,
        "_id": 0
    })
    
    if user:
        # Return usage information with consistent field names
        return {
            "used_today": user["used_quota"],
            "last_used": user["last_generation_time"]
        }
    
    return None

def update_user_usage(username, apiCreditCost):
    """
    Update a user's API usage statistics in MongoDB
    
    Args:
        username: Username of the user to update
        apiCreditCost: Cost to add to the user's quota usage
    
    Returns:
        None
    """
    # Get current date in ISO format
    today = datetime.now().date().isoformat()
    
    # Find the user to check their current usage state
    user = users.find_one({"username": username}, {
        "used_quota": 1, 
        "last_generation_time": 1
    })
    
    if user and user.get("last_generation_time") == today:
        # Same day, increment usage
        new_usage = user.get("used_quota", 0) + apiCreditCost
        
        # Update user document
        users.update_one(
            {"username": username},
            {"$set": {"used_quota": new_usage}}
        )
    else:
        # New day or first usage, reset counter and set today's date
        users.update_one(
            {"username": username},
            {
                "$set": {
                    "used_quota": apiCreditCost,
                    "last_generation_time": today
                }
            }
        )

def log_generation(username, prompt, source_image_path, generation_type, project, parameters, result_images, apiCreditCost):
    """
    Log a generation with enhanced metadata for better history display in MongoDB
    
    Parameters:
    - username: The user who performed the generation
    - prompt: The text prompt used
    - source_image_path: Path to source image (for image-to-image)
    - generation_type: Type of generation (text_to_image or image_to_image)
    - project: The project name
    - parameters: Dictionary of parameters used
    - result_images: List of result image data including URLs
    - apiCreditCost: The cost of the generation in API credits
    """
    # Get current timestamp
    timestamp = datetime.now().isoformat()
    
    # Add additional metadata for display in history
    metadata = {
        "model_name": get_model_name_from_id(parameters.get("modelId")),
        "style_name": get_style_name_from_id(parameters.get("styleUUID")),
        "dimensions": f"{parameters.get('width', 'unknown')}×{parameters.get('height', 'unknown')}",
        "guidance_scale": parameters.get("guidance_scale", "unknown"),
        "preset_style": parameters.get("presetStyle", "None"),
        "photo_real": "Enabled" if parameters.get("photoReal") else "Disabled",
        "generation_timestamp": timestamp
    }
    
    # Merge metadata into parameters for storage
    enhanced_params = {**parameters, "display_metadata": metadata}
    
    # Extract image URLs from result_images
    image_urls = []
    for img in result_images:
        if isinstance(img, dict) and "url" in img:
            image_urls.append(img["url"])
    
    # Create generation document
    generation_doc = {
        "username": username,
        "prompt": prompt,
        "source_image_path": source_image_path,
        "generation_type": generation_type,
        "project": project,
        "parameters": enhanced_params,
        "result_urls": image_urls,
        "timestamp": timestamp,
        "apiCreditCost": apiCreditCost,
        "created_at": datetime.utcnow()
    }
    
    # Insert the generation document
    result = generations.insert_one(generation_doc)
    
    return result.inserted_id

def create_project(name, description, created_by):
    """
    Create a new project in MongoDB
    
    Args:
        name: Name of the project (must be unique)
        description: Description of the project
        created_by: Username of the creator
    
    Returns:
        Boolean indicating success or failure
    """
    # Create project document
    project_doc = {
        "name": name,
        "description": description,
        "created_by": created_by,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    try:
        # Insert the project document
        result = projects.insert_one(project_doc)
        return result.acknowledged
    except pymongo.errors.DuplicateKeyError:
        # Project name already exists
        return False
    except Exception as e:
        print(f"Error creating project: {e}")
        return False
    
def get_projects():
    """
    Retrieve all projects from MongoDB
    
    Returns:
        List of project dictionaries with name and description
    """
    # Query all projects and select only name and description fields
    project_list = projects.find({}, {"name": 1, "description": 1, "_id": 0})
    
    # Convert cursor to list
    return list(project_list)

def get_user_stats():
    """
    Retrieve statistics about the number of generations per user from MongoDB
    
    Returns:
        List of dictionaries containing username and generation count
    """
    # Use MongoDB's aggregation framework to group by username and count generations
    pipeline = [
        {"$group": {
            "_id": "$username",
            "generations": {"$sum": 1}
        }},
        {"$project": {
            "_id": 0,
            "username": "$_id",
            "generations": 1
        }}
    ]
    
    # Execute the aggregation pipeline
    stats = generations.aggregate(pipeline)
    
    # Convert cursor to list
    return list(stats)


def get_generation_history():
    """
    Retrieve all generations from MongoDB ordered by timestamp descending
    
    Returns:
        List of all generation documents with complete information
    """
    # Query all generations, sort by timestamp in descending order
    history = generations.find().sort("timestamp", pymongo.DESCENDING)
    
    # Convert cursor to list
    return list(history)


def get_users_dataframe():
    """
    Retrieve all users from MongoDB and return as a pandas DataFrame
    
    Returns:
        DataFrame containing user information
    """
    # Query all users, excluding password hash for security
    user_list = users.find({}, {
        "username": 1, 
        "role": 1, 
        "daily_quota": 1, 
        "used_quota": 1,
        "_id": 0  # Exclude MongoDB's ObjectId
    })
    
    # Convert cursor to list
    user_data = list(user_list)
    
    # Rename 'used_quota' to 'used_today' to match original structure
    for user in user_data:
        if 'used_quota' in user:
            user['used_today'] = user.pop('used_quota')
    
    # Convert to DataFrame
    return pd.DataFrame(user_data)


def get_project_stats():
    """
    Retrieve statistics about the number of generations per project from MongoDB
    
    Returns:
        DataFrame containing project stats
    """
    # Use MongoDB's aggregation framework to count generations by project
    pipeline = [
        {"$group": {
            "_id": "$project",
            "generation_count": {"$sum": 1}
        }},
        {"$project": {
            "_id": 0,
            "project": "$_id",
            "generation_count": 1
        }}
    ]
    
    # Execute the aggregation pipeline
    stats_cursor = generations.aggregate(pipeline)
    
    # Convert cursor to list
    stats_list = list(stats_cursor)
    
    # Convert to DataFrame
    return pd.DataFrame(stats_list)

if __name__ == "__main__":
    verify_user("admin", "omnamahshivaya")
