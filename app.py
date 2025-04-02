import streamlit as st
import requests
import os
import json
from PIL import Image
import io
import base64
from datetime import datetime
import pandas as pd
import sqlite3
import hashlib
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Leonardo API Key (store this in .env file in production)
LEONARDO_API_KEY = os.getenv("LEONARDO_API_KEY")

# Database setup
DB_PATH = "leonardo_team.db"

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

def update_user_usage(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get current usage
    c.execute("SELECT used_today, last_used FROM users WHERE username=?", (username,))
    current = c.fetchone()
    
    today = datetime.now().date().isoformat()
    
    if current[1] and current[1] == today:
        # Same day, increment usage
        new_usage = current[0] + 1
    else:
        # New day, reset counter
        new_usage = 1
    
    c.execute("UPDATE users SET used_today=?, last_used=? WHERE username=?", 
             (new_usage, today, username))
    
    conn.commit()
    conn.close()

def log_generation(username, prompt, source_image_path, generation_type, project, parameters, result_url):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    
    c.execute('''
    INSERT INTO generations 
    (username, prompt, source_image_path, generation_type, project, parameters, result_url, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (username, prompt, source_image_path, generation_type, project, json.dumps(parameters), result_url, timestamp))
    
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

def leonardo_text_to_image(prompt, parameters):
    """Call Leonardo API for text-to-image generation"""
    url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    
    headers = {
        "Authorization": f"Bearer {LEONARDO_API_KEY}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }
    
    payload = {
        "modelId": "b2614463-296c-462a-9586-aafdb8f00e36",  # Leonardo Creative model
        # "contrast": 3.5,
        "prompt": prompt,
        "num_images": parameters.get("num_images", 1),
        "width": parameters.get("width", 512),
        "height": parameters.get("height", 512),
        # "ultra": True,       
        # "photoRealVersion": "v2",
        # "alchemy": True,
        # "photoReal": True,
        # "photoRealStrength": 0.5,
        "styleUUID": "3cbb655a-7ca4-463f-b697-8a03ad67327c"
        
    }
    
    try:
        st.write("Starting image generation...")
        st.write("Request payload:", json.dumps(payload, indent=2))
        
        # First create the generation
        response = requests.post(url, json=payload, headers=headers)
        
        # Log the response for debugging
        st.write("Initial API Response:", response.text)
        
        if response.status_code != 200:
            st.error(f"API Error: Status code {response.status_code}")
            st.error(f"Response: {response.text}")
            return None
            
        generation_data = response.json()
        
        # Get the generation ID from the nested structure
        generation_id = generation_data.get("sdGenerationJob", {}).get("generationId")
        if not generation_id:
            st.error("Failed to get generation ID from API")
            st.error(f"Full response: {generation_data}")
            return None
            
        st.write(f"Generation ID received: {generation_id}")
            
        # Poll for the generation result
        status_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
        max_attempts = 30  # 30 seconds maximum wait time
        attempt = 0
        
        # Create a progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while attempt < max_attempts:
            status_response = requests.get(status_url, headers=headers)
            
            if status_response.status_code != 200:
                st.error(f"Status check failed: {status_response.status_code}")
                st.error(f"Response: {status_response.text}")
                return None
                
            status_data = status_response.json()
            st.write(f"Status check {attempt + 1}/{max_attempts}")
            
            # Update progress
            progress = min(1.0, (attempt + 1) / max_attempts)
            progress_bar.progress(progress)
            status_text.text(f"Checking generation status... ({attempt + 1}/{max_attempts})")
            
            if status_data['generations_by_pk']['status']== "COMPLETE":
                status_text.text("Generation completed successfully!")
                return status_data
            elif status_data['generations_by_pk']['status'] == "FAILED":
                status_text.text("Generation failed!")
                st.error(f"Generation failed: {status_data.get('error')}")
                return None
                
            time.sleep(1)  # Wait 1 second before next poll
            attempt += 1
            
        status_text.text("Generation timed out!")
        st.error("Generation timed out")
        return None
        
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse API response: {str(e)}")
        st.error(f"Raw response: {response.text}")
        return None

def leonardo_image_to_image(prompt, image_file, parameters):
    """Call Leonardo API for image-to-image generation"""
    # This function would need to be implemented based on Leonardo.ai's API
    # For image-to-image, you typically need to:
    # 1. Upload the source image to their API or a storage service
    # 2. Get the URL of the uploaded image
    # 3. Send a request with the source image URL and other parameters
    
    # This is a placeholder implementation
    url = "https://cloud.leonardo.ai/api/rest/v1/generations/img2img"
    
    headers = {
        "Authorization": f"Bearer {LEONARDO_API_KEY}"
    }
    
    # First upload the image
    files = {"image": image_file}
    
    try:
        # Upload image (this endpoint is hypothetical)
        upload_response = requests.post(
            "https://cloud.leonardo.ai/api/rest/v1/uploads", 
            headers=headers, 
            files=files
        )
        upload_response.raise_for_status()
        
        # Get the image URL from the response
        source_image_url = upload_response.json().get("url")
        
        # Now call the image-to-image endpoint
        payload = {
            "prompt": prompt,
            "sourceImageUrl": source_image_url,
            "modelId": parameters.get("model_id", ""),
            "strength": parameters.get("strength", 0.7),  # How much to transform
            "num_images": parameters.get("num_images", 1)
        }
        
        response = requests.post(
            url, 
            json=payload, 
            headers={"Authorization": f"Bearer {LEONARDO_API_KEY}", "Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        return result
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

def login_page():
    st.title("Leonardo.ai Team UI - Login")
    
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        user = verify_user(username, password)
        if user:
            st.session_state.logged_in = True
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Invalid username or password")
    
    st.divider()
    st.write("Don't have an account? Contact your administrator.")

def main_navigation():
    st.sidebar.title(f"Welcome, {st.session_state.user['username']}")
    
    # Show quota information
    usage = get_user_usage(st.session_state.user['username'])
    if usage:
        quota_used = usage["used_today"] or 0
        quota_total = st.session_state.user["daily_quota"]
        st.sidebar.progress(quota_used / quota_total)
        st.sidebar.text(f"Usage: {quota_used}/{quota_total} generations today")
    
    page = st.sidebar.radio(
        "Navigation",
        ["Text to Image", "Image to Image", "View History"]
    )
    
    # Admin options
    if st.session_state.user["role"] == "admin":
        st.sidebar.divider()
        st.sidebar.subheader("Admin")
        admin_page = st.sidebar.radio(
            "Admin Tools",
            ["User Management", "Project Management", "Usage Statistics"]
        )
    else:
        admin_page = None
    
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()
    
    return page, admin_page

def text_to_image_page():
    st.title("Text to Image Generator")
    
    # Project selection
    projects = get_projects()
    project_names = [p["name"] for p in projects]
    
    if not project_names:
        st.warning("No projects available. Please contact an admin to create a project.")
        return
        
    selected_project = st.selectbox("Select Project", project_names)
    
    # Prompt input
    prompt = st.text_area("Enter your prompt", height=100)
    
    # Advanced options with expander
    with st.expander("Advanced Options"):
        col1, col2 = st.columns(2)
        
        with col1:
            width = st.selectbox("Width", [512, 768, 1024])
            guidance_scale = st.slider("Guidance Scale", 1.0, 20.0, 7.0)
        
        with col2:
            height = st.selectbox("Height", [512, 768, 1024])
            num_images = st.selectbox("Number of Images", [1, 2, 4])
    
    # Check quota before generation
    usage = get_user_usage(st.session_state.user['username'])
    if usage and usage["used_today"] >= st.session_state.user["daily_quota"]:
        st.error("You have reached your daily quota. Please try again tomorrow.")
        return
    
    # Generate button
    if st.button("Generate Images"):
        if not prompt:
            st.error("Please enter a prompt")
            return
            
        with st.spinner("Generating images..."):
            # Prepare parameters
            parameters = {
                "width": width,
                "height": height,
                "num_images": num_images,
                "guidance_scale": guidance_scale
            }
            
            # Call API
            result = leonardo_text_to_image(prompt, parameters)
            
            if result:
                # Update usage
                update_user_usage(st.session_state.user['username'])
                
                # Display results
                st.subheader("Generated Images")
                
                # Get the generated images from the nested response structure
                generation_data = result.get("generations_by_pk", {})
                generated_images = generation_data.get("generated_images", [])
                
                if generated_images:
                    cols = st.columns(len(generated_images))
                    for i, img_data in enumerate(generated_images):
                        with cols[i]:
                            img_url = img_data.get("url")
                            if img_url:
                                st.image(img_url, use_column_width=True)
                                st.markdown(f"[Download]({img_url})")
                    
                    # Log the generation
                    log_generation(
                        username=st.session_state.user['username'],
                        prompt=prompt,
                        source_image_path=None,
                        generation_type="text_to_image",
                        project=selected_project,
                        parameters=parameters,
                        result_url=str(generated_images)
                    )
                else:
                    st.error("No images were generated. Please try again.")

def image_to_image_page():
    st.title("Image to Image Generator")
    
    # Project selection
    projects = get_projects()
    project_names = [p["name"] for p in projects]
    
    if not project_names:
        st.warning("No projects available. Please contact an admin to create a project.")
        return
        
    selected_project = st.selectbox("Select Project", project_names)
    
    # Source image upload
    source_image = st.file_uploader("Upload Source Image", type=["png", "jpg", "jpeg", "webp"])
    
    if source_image:
        st.image(source_image, caption="Source Image", use_column_width=True)
        
        # Prompt input
        prompt = st.text_area("Enter your prompt", height=100)
        
        # Advanced options with expander
        with st.expander("Advanced Options"):
            strength = st.slider("Transformation Strength", 0.1, 1.0, 0.7, 0.1)
            num_images = st.selectbox("Number of Images", [1, 2, 4])
        
        # Check quota before generation
        usage = get_user_usage(st.session_state.user['username'])
        if usage and usage["used_today"] >= st.session_state.user["daily_quota"]:
            st.error("You have reached your daily quota. Please try again tomorrow.")
            return
        
        # Generate button
        if st.button("Transform Image"):
            if not prompt:
                st.error("Please enter a prompt")
                return
                
            with st.spinner("Transforming image..."):
                # Prepare parameters
                parameters = {
                    "strength": strength,
                    "num_images": num_images
                }
                
                # Reset file pointer
                source_image.seek(0)
                
                # Call API
                result = leonardo_image_to_image(prompt, source_image, parameters)
                
                if result:
                    # Update usage
                    update_user_usage(st.session_state.user['username'])
                    
                    # Display results
                    st.subheader("Generated Images")
                    
                    # The response structure will depend on Leonardo's API
                    # This is an example assuming a list of image URLs
                    image_urls = result.get("generationsByPk", {}).get("generated_images", [])
                    
                    if image_urls:
                        cols = st.columns(len(image_urls))
                        for i, img_data in enumerate(image_urls):
                            with cols[i]:
                                img_url = img_data.get("url")
                                st.image(img_url, use_column_width=True)
                                st.markdown(f"[Download]({img_url})")
                        
                        # Save source image to disk and get path
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        source_path = f"uploads/{st.session_state.user['username']}_{timestamp}.png"
                        
                        # Ensure directory exists
                        os.makedirs("uploads", exist_ok=True)
                        
                        # Save the file
                        with open(source_path, "wb") as f:
                            source_image.seek(0)
                            f.write(source_image.read())
                        
                        # Log the generation
                        log_generation(
                            username=st.session_state.user['username'],
                            prompt=prompt,
                            source_image_path=source_path,
                            generation_type="image_to_image",
                            project=selected_project,
                            parameters=parameters,
                            result_url=str(image_urls)
                        )
                    else:
                        st.error("No images were generated. Please try again.")
    else:
        st.info("Please upload a source image to continue")

def history_page():
    st.title("Generation History")
    
    conn = sqlite3.connect(DB_PATH)
    
    # Get user's generations
    if st.session_state.user["role"] == "admin":
        # Admins can see all generations
        query = """
        SELECT g.id, g.username, g.prompt, g.generation_type, g.project, 
               g.parameters, g.result_url, g.timestamp 
        FROM generations g
        ORDER BY g.timestamp DESC
        """
        df = pd.read_sql_query(query, conn)
    else:
        # Users can only see their own generations
        query = """
        SELECT g.id, g.prompt, g.generation_type, g.project, 
               g.parameters, g.result_url, g.timestamp 
        FROM generations g
        WHERE g.username = ?
        ORDER BY g.timestamp DESC
        """
        df = pd.read_sql_query(query, conn, params=(st.session_state.user["username"],))
    
    conn.close()
    
    if len(df) > 0:
        # Format dates for better readability
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Add a column for displaying images
        if "result_url" in df.columns:
            df["result_url"] = df["result_url"].apply(lambda x: json.loads(x.replace("'", '"')) if isinstance(x, str) else [])
        
        # Use an expander for each generation
        for i, row in df.iterrows():
            with st.expander(f"{row['generation_type']} - {row['project']} - {row['timestamp']}"):
                st.write(f"**Prompt:** {row['prompt']}")
                
                # Display parameters
                params = json.loads(row['parameters'])
                st.write("**Parameters:**")
                for key, value in params.items():
                    st.write(f"- {key}: {value}")
                
                # Try to display image URLs
                try:
                    image_urls = row['result_url']
                    if isinstance(image_urls, list) and len(image_urls) > 0:
                        st.write("**Results:**")
                        # For simplicity, just display the first image
                        for img_data in image_urls[:1]:
                            if isinstance(img_data, dict) and 'url' in img_data:
                                st.image(img_data['url'], width=300)
                except Exception as e:
                    st.write("Error displaying images")
    else:
        st.info("No generations found in your history.")

def admin_user_management():
    st.title("User Management")
    
    # Create new user form
    with st.form("new_user_form"):
        st.subheader("Create New User")
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        new_role = st.selectbox("Role", ["user", "admin"])
        new_quota = st.number_input("Daily Quota", min_value=1, value=20)
        
        submit_button = st.form_submit_button("Create User")
        
        if submit_button:
            if new_username and new_password:
                success = create_user(new_username, new_password, new_role, new_quota)
                if success:
                    st.success(f"User {new_username} created successfully")
                else:
                    st.error(f"Username {new_username} already exists")
            else:
                st.error("Username and password are required")
    
    # Display existing users
    st.subheader("Existing Users")
    
    conn = sqlite3.connect(DB_PATH)
    users_df = pd.read_sql_query("SELECT username, role, daily_quota, used_today FROM users", conn)
    conn.close()
    
    st.dataframe(users_df)
    
    # Modify user functionality could be added here

def admin_project_management():
    st.title("Project Management")
    
    # Create new project form
    with st.form("new_project_form"):
        st.subheader("Create New Project")
        new_project_name = st.text_input("Project Name")
        new_project_desc = st.text_area("Description")
        
        submit_button = st.form_submit_button("Create Project")
        
        if submit_button:
            if new_project_name:
                success = create_project(
                    new_project_name, 
                    new_project_desc, 
                    st.session_state.user["username"]
                )
                if success:
                    st.success(f"Project {new_project_name} created successfully")
                else:
                    st.error(f"Project name {new_project_name} already exists")
            else:
                st.error("Project name is required")
    
    # Display existing projects
    st.subheader("Existing Projects")
    
    projects = get_projects()
    if projects:
        projects_df = pd.DataFrame(projects)
        st.dataframe(projects_df)
    else:
        st.info("No projects exist yet")

def admin_usage_statistics():
    st.title("Usage Statistics")
    
    # Get user stats
    user_stats = get_user_stats()
    
    if user_stats:
        st.subheader("Generations by User")
        stats_df = pd.DataFrame(user_stats)
        
        # Create a bar chart
        st.bar_chart(stats_df.set_index('username'))
        
        # Display as table too
        st.dataframe(stats_df)
    else:
        st.info("No usage data available yet")
    
    # Get project stats
    conn = sqlite3.connect(DB_PATH)
    project_stats = pd.read_sql_query("""
    SELECT project, COUNT(*) as generation_count 
    FROM generations 
    GROUP BY project
    """, conn)
    conn.close()
    
    if not project_stats.empty:
        st.subheader("Generations by Project")
        st.bar_chart(project_stats.set_index('project'))
        st.dataframe(project_stats)

def main():
    # Initialize database
    init_db()
    
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    # Main app flow
    if not st.session_state.logged_in:
        login_page()
    else:
        page, admin_page = main_navigation()
        
        if page == "Text to Image":
            text_to_image_page()
        elif page == "Image to Image":
            image_to_image_page()
        elif page == "View History":
            history_page()
        
        # Admin pages
        if admin_page:
            st.divider()
            if admin_page == "User Management":
                admin_user_management()
            elif admin_page == "Project Management":
                admin_project_management()
            elif admin_page == "Usage Statistics":
                admin_usage_statistics()

if __name__ == "__main__":
    main()
