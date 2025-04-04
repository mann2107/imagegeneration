import sqlite3
import hashlib
import json
from datetime import datetime
from model_parameters import get_model_name_from_id, get_style_name_from_id

# Database setup
# Make sure .streamlit directory exists
os.makedirs(".streamlit", exist_ok=True)

DB_PATH = os.path.join(".streamlit", "leonardo_team.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create users table if it doesn't exist
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        daily_quota INTEGER NOT NULL,
        used_today INTEGER DEFAULT 0,
        last_used TEXT
    )
    ''')
    
    # Create generations table if it doesn't exist
    c.execute('''
    CREATE TABLE IF NOT EXISTS generations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        prompt TEXT NOT NULL,
        source_image_path TEXT,
        generation_type TEXT NOT NULL,
        project TEXT NOT NULL,
        parameters TEXT NOT NULL,
        result_url TEXT,
        timestamp TEXT NOT NULL,
        apiCreditCost INTEGER NOT NULL,
        FOREIGN KEY (username) REFERENCES users (username)
    )
    ''')
    
    # Create projects table if it doesn't exist
    c.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        name TEXT PRIMARY KEY,
        description TEXT,
        created_by TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (created_by) REFERENCES users (username)
    )
    ''')
    
    # Insert admin user if it doesn't exist
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        admin_password_hash = hashlib.sha256("admin".encode()).hexdigest()
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", 
                 ("admin", admin_password_hash, "admin", 100, 0, None))
    
    conn.commit()
    conn.close()

def create_user(username, password, role, daily_quota):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", 
                 (username, password_hash, role, daily_quota, 0, None))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    
    conn.close()
    return success

def verify_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    c.execute("SELECT * FROM users WHERE username=? AND password_hash=?", (username, password_hash))
    user = c.fetchone()
    
    conn.close()
    
    if user:
        return {"username": user[0], "role": user[2], "daily_quota": user[3], "used_today": user[4]}
    return None

def get_user_usage(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT used_today, last_used FROM users WHERE username=?", (username,))
    result = c.fetchone()
    
    conn.close()
    
    if result:
        return {"used_today": result[0], "last_used": result[1]}
    return None

def update_user_usage(username, apiCreditCost):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get current usage
    c.execute("SELECT used_today, last_used FROM users WHERE username=?", (username,))
    current = c.fetchone()
    
    today = datetime.now().date().isoformat()
    
    if current[1] and current[1] == today:
        # Same day, increment usage
        new_usage = current[0] + apiCreditCost
    else:
        # New day, reset counter
        new_usage = 0
    
    c.execute("UPDATE users SET used_today=?, last_used=? WHERE username=?", 
             (new_usage, today, username))
    
    conn.commit()
    conn.close()


def log_generation(username, prompt, source_image_path, generation_type, project, parameters, result_images, apiCreditCost):
    """
    Log a generation with enhanced metadata for better history display
    
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
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
    
    # Store the actual image URLs separately for easy access
    image_urls = []
    for img in result_images:
        if isinstance(img, dict) and "url" in img:
            image_urls.append(img["url"])
    
    c.execute('''
    INSERT INTO generations 
    (username, prompt, source_image_path, generation_type, project, parameters, result_url, timestamp, apiCreditCost)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (username, prompt, source_image_path, generation_type, project, 
          json.dumps(enhanced_params), json.dumps(image_urls), timestamp, apiCreditCost))
    
    conn.commit()
    conn.close()


def create_project(name, description, created_by):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    created_at = datetime.now().isoformat()
    
    try:
        c.execute("INSERT INTO projects VALUES (?, ?, ?, ?)", 
                 (name, description, created_by, created_at))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    
    conn.close()
    return success

def get_projects():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT name, description FROM projects")
    projects = c.fetchall()
    
    conn.close()
    
    return [{"name": p[0], "description": p[1]} for p in projects]

def get_user_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
    SELECT username, COUNT(*) as generation_count 
    FROM generations 
    GROUP BY username
    """)
    stats = c.fetchall()
    
    conn.close()
    
    return [{"username": s[0], "generations": s[1]} for s in stats]





