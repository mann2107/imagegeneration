import streamlit as st
import requests
import os
import json
import requests
import json
import time
import io
    
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
import time
from db_helper import *


from model_parameters import modelIds, modelTypes, styleUUID, presetStyle, sdxl_params

# Load environment variables
load_dotenv()

# Leonardo API Key (store this in .env file in production)
LEONARDO_API_KEY = os.getenv("LEONARDO_API_KEY")


def leonardo_text_to_image(prompt, parameters):
    apiCreditCost = "0"
    """Call Leonardo API for text-to-image generation"""
    url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    
    headers = {
        "Authorization": f"Bearer {LEONARDO_API_KEY}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }
    
    # Start with base payload
    payload = {
        "prompt": prompt,
        "num_images": parameters.get("num_images", 1),
        "width": parameters.get("width", 512),
        "height": parameters.get("height", 512),
    }
    
    # Add model ID (required)
    payload["modelId"] = parameters.get("modelId", "b2614463-296c-462a-9586-aafdb8f00e36")
    
           
    # # Add negative prompt if provided
    # if "negative_prompt" in parameters and parameters["negative_prompt"]:
    #     payload["negativePrompt"] = parameters["negative_prompt"]
        
    # Add contrast if provided
    if "contrast" in parameters:
        payload["contrast"] = float(parameters["contrast"])
    
       
    # Add model-specific parameters
    # Phoenix and SDXL models
    if "alchemy" in parameters:
        payload["alchemy"] = parameters["alchemy"]
    
    # Phoenix models
    if "ultra" in parameters:
        payload["ultra"] = parameters["ultra"]


    try:
        if payload["ultra"] == True and payload["alchemy"] == True:
            del payload["alchemy"]
    except:
        pass
    
    # SDXL and SD15 models
    if "photoReal" in parameters:
        payload["photoReal"] = parameters["photoReal"]
        if parameters["photoReal"] and "photoRealVersion" in parameters:
            payload["photoRealVersion"] = parameters["photoRealVersion"]
    
    # Style options
    if "styleUUID" in parameters and parameters["styleUUID"]:
        payload["styleUUID"] = parameters["styleUUID"]
    
    # Preset style for SDXL
    if "presetStyle" in parameters and parameters["presetStyle"]:
        payload["presetStyle"] = parameters["presetStyle"]
    
    # Add prompt enhancement if specified
    if "enhancePrompt" in parameters:
        payload["enhancePrompt"] = parameters["enhancePrompt"]
    
    try:
        st.write("Starting image generation...")
        st.write("Request payload:", json.dumps(payload, indent=2))
        
        # First create the generation
        response = requests.post(url, json=payload, headers=headers)
        
        # Log the response for debugging
        # st.write("Initial API Response:", response.text)
        
        

        if response.status_code != 200:
            st.error(f"API Error: Status code {response.status_code}")
            st.error(f"Response: {response.text}")
            return None, apiCreditCost
            
        generation_data = response.json()
        
        # Get the generation ID from the nested structure
        generation_id = generation_data.get("sdGenerationJob", {}).get("generationId")
        apiCreditCost = generation_data.get("sdGenerationJob", {}).get("apiCreditCost", "0")
        st.write(f"API Credits: {apiCreditCost}")
        if not generation_id:
            st.error("Failed to get generation ID from API")
            st.error(f"Full response: {generation_data}")
            return None, apiCreditCost
            
        # st.write(f"Generation ID received: {generation_id}")
            
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
                return None, apiCreditCost
                
            status_data = status_response.json()
            
            # Update progress
            progress = min(1.0, (attempt + 1) / max_attempts)
            progress_bar.progress(progress)
            status_text.text(f"Checking generation status... ({attempt + 1}/{max_attempts})")
            
            if status_data['generations_by_pk']['status'] == "COMPLETE":
                status_text.text("Generation completed successfully!")
                return status_data, apiCreditCost
            elif status_data['generations_by_pk']['status'] == "FAILED":
                status_text.text("Generation failed!")
                st.error(f"Generation failed: {status_data.get('error')}")
                return None, apiCreditCost
                
            time.sleep(1)  # Wait 1 second before next poll
            attempt += 1
            
        status_text.text("Generation timed out!")
        st.error("Generation timed out")
        return None, apiCreditCost
        
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None, apiCreditCost
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse API response: {str(e)}")
        st.error(f"Raw response: {response.text}")
        return None, apiCreditCost
   
def leonardo_image_to_image(prompt, image_file, parameters):
    """Call Leonardo API for image-to-image generation"""
    
    # Configuration
    # Ensure API key doesn't have any whitespace
    api_key = LEONARDO_API_KEY.strip()
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    
    # Debug info - hide actual key for security
    key_preview = f"{api_key[:5]}...{api_key[-5:]}" if len(api_key) > 10 else "Invalid key format"
    print(f"Using API key: {key_preview}")
    
    try:
        # Step 1: Get a presigned URL for uploading the image
        init_url = "https://cloud.leonardo.ai/api/rest/v1/init-image"
        
        # Determine file extension from uploaded file
        file_name = image_file.name
        extension = file_name.split('.')[-1].lower()
        
        payload = {"extension": extension}
        response = requests.post(init_url, json=payload, headers=headers)
        response.raise_for_status()
        print("Step 1 done")
        # Step 2: Upload the image using the presigned URL
        fields = json.loads(response.json()['uploadInitImage']['fields'])
        upload_url = response.json()['uploadInitImage']['url']
        image_id = response.json()['uploadInitImage']['id']
        print("Step 2 done")
        # Reset file pointer and prepare for upload
        image_file.seek(0)
        print("Step 2.1 done")
        print(image_file)
        print(file_name)
        print(f'image/{extension}')
        files = {'file': (file_name, image_file, f'image/{extension}')}
        print("Step 2.2 done")
        
        # Upload to the presigned URL (no headers needed for this request)
        upload_response = requests.post(upload_url, data=fields, files=files)
        upload_response.raise_for_status()
        print("Step 2.3 done")
        print(upload_response)
        # print(f"Upload response: {upload_response.json()}")
        print("Step 3 done")
        # Step 3: Generate with the uploaded image
        generation_url = "https://cloud.leonardo.ai/api/rest/v1/generations"
        
        # Extract parameters with defaults
        model_id = parameters.get("model_id", "6bef9f1b-29cb-40c7-b9df-32b51c1f67d3")  # Default to Leonardo Creative "1e60896f-3c26-4296-8ecc-53e2afecc132"
        width = parameters.get("width", 512)
        height = parameters.get("height", 512)
        num_images = parameters.get("num_images", 1)
        select_model = parameters.get("select_model", "General")
        select_dimensions = parameters.get("select_dimensions", "Square")
        if select_model == "Raja Ravi Varma":
            model_id = "6bef9f1b-29cb-40c7-b9df-32b51c1f67d3"
            prompt = prompt + " in style of raja ravi varma"
        else:
            model_id = "6bef9f1b-29cb-40c7-b9df-32b51c1f67d3"
            
        
        if select_dimensions == "Portrait":
            height = 1024
            width = 576
        else:
            height = 1024
            width = 576


        generation_payload = {
            "height": height,
            "width": width,
            "modelId": model_id,
            "prompt": prompt,
            "num_images": 1,
            "init_image_id": image_id,  # Array of image IDs as per API docs            
            "init_strength": 0.7,
        }
        print(generation_payload)
        print(headers)
        generation_response = requests.post(generation_url, json=generation_payload, headers=headers)
        generation_response.raise_for_status()
        print("Step 3.1 done")
        
        # Step 4: Get the generated images
        generation_id = generation_response.json()['sdGenerationJob']['generationId']
        results_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}"
        print("Step 4 done")
        # Wait for generation to complete
        max_attempts = 30
        attempts = 0
        while attempts < max_attempts:
            time.sleep(2)  # Wait 2 seconds between checks
            results_response = requests.get(results_url, headers=headers)
            results_response.raise_for_status()
            result_data = results_response.json()
            print(result_data)
            # Check if generation is complete
            status = result_data.get('generations_by_pk', {}).get('status')
            if status == "COMPLETE":
                st.write("Generation completed successfully!")
                return result_data
            elif status == "FAILED":
                st.error("Image generation failed")
                return None
            
            attempts += 1
        
        st.warning("Generation taking longer than expected. Please check your results page later.")
        return None
        
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

def login_page():
    st.title("Kalki Team UI - Login")
    
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
        ["Image to Image", "View History", "Generate Description"]
    )
    # ["Text to Image", "Image to Image", "View History", "Generate Description"]

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
    
    # Import model parameters
    from model_parameters import modelIds, modelTypes, styleUUID, presetStyle, sdxl_params
    
    # Project selection
    projects = get_projects()
    project_names = [p["name"] for p in projects]
    
    if not project_names:
        st.warning("No projects available. Please contact an admin to create a project.")
        return
        
    selected_project = st.selectbox("Select Project", project_names)
    
    # Model selection
    available_models = list(modelIds.keys())
    selected_model_name = st.selectbox("Select Model", available_models)
    
    # Get model ID and type
    selected_model_id = modelIds.get(selected_model_name)
    selected_model_type = modelTypes.get(selected_model_name)
    
    # Prompt input with character counter
    prompt_max_length = 1000  # Set a reasonable max length for prompt
    prompt = st.text_area("Enter your prompt", height=100, max_chars=prompt_max_length)
    st.caption(f"Character count: {len(prompt)}/{prompt_max_length}")
    
        
    # Parameters organized into simple tabs
    tabs = st.tabs(["Dimensions", "Generation", "Style", "Model-Specific"])
        
    with tabs[0]:  # Dimensions tab - Simplified to just 3 options
        # Define the three simple dimension presets as requested
        dimension_presets = {
            "Square": (512, 512),
            "Portrait": (576, 1024),
            "Landscape": (1024, 576)
        }
        
        # Simple radio button selection for the three options
        selected_dimension = st.radio("Select image dimensions", 
                                        list(dimension_presets.keys()), 
                                        horizontal=True,
                                        format_func=lambda x: f"{x} ({dimension_presets[x][0]}×{dimension_presets[x][1]})", index=1)
        
        # Get the dimensions from the selection
        width, height = dimension_presets[selected_dimension]
        
        # Visual display of selected dimensions
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("Width", width)
            st.metric("Height", height)
        
        with col2:
            # Create a simple visual representation with fixed max size
            max_size = 150
            
            # Calculate scaled dimensions for visualization
            if width >= height:
                visual_width = max_size
                visual_height = int(max_size * (height / width))
            else:
                visual_height = max_size
                visual_width = int(max_size * (width / height))
            
            # Display visual representation
            st.markdown(f"""
            <div style="
                width: {visual_width}px; 
                height: {visual_height}px; 
                background-color: #e0f7fa; 
                border: 2px solid #0277bd;
                border-radius: 5px;
                margin: 10px 0;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #0277bd;
                font-weight: bold;
            ">
                {width}×{height}
            </div>
            """, unsafe_allow_html=True)
    
    with tabs[1]:  # Generation tab - Simplified with fewer options
        
        # Set defaults for hidden options
        num_images = 1  # Fixed at 1 image
        enhance_prompt = True  # Always enabled
        contrast = "3.5"  # Default value
        
        # Show contrast options
        contrast = st.radio("Contrast", options=["3", "3.5", "4"], index=1)
    
    with tabs[2]:  # Style tab
        # Show style selection based on model type
        if selected_model_type in ["sdxl", "sd15", "phoenix", "flux"]:
            # Style UUID options
            style_options = list(styleUUID.keys())
            selected_style = st.selectbox("Style", ["None"] + style_options)
            
            if selected_style != "None":
                selected_style_uuid = styleUUID.get(selected_style)
                st.info(f"Selected style: {selected_style}")
            else:
                selected_style_uuid = None
        
    with tabs[3]:  # Model-specific tab - Simplified with defaults
        # Set defaults for hidden options
        alchemy = True  # Always enabled by default
        ultra = True  # Always enabled by default
        photo_real_version = "v2"  # Always v2 when PhotoReal is enabled
        
        # Conditional options based on model type
        if selected_model_type == "flux":
            st.info("Flux model selected - optimized for speed and quality")
        
        elif selected_model_type == "phoenix":
            st.info("Phoenix model selected - advanced capabilities enabled")
            # No options shown - using defaults
        
        elif selected_model_type == "sdxl":
            # Only show PhotoReal option
            photo_real = st.checkbox("Enable PhotoReal", value=False,
                                    help="Enhance photorealism of generated images")
            
            # Show preset style options
            preset_style_options = list(presetStyle.keys())
            preset_style_selection = st.selectbox("Preset Style", ["None"] + preset_style_options)
            
            if preset_style_selection != "None":
                preset_style_value = presetStyle.get(preset_style_selection)
            else:
                preset_style_value = None
        
        elif selected_model_type == "sd15":
            # Only show PhotoReal option
            photo_real = st.checkbox("Enable PhotoReal", value=False,
                                    help="Enhance photorealism of generated images")
    
    # Check quota before generation
    usage = get_user_usage(st.session_state.user['username'])
    if usage and usage["used_today"] >= st.session_state.user["daily_quota"]:
        st.error("You have reached your daily quota. Please try again tomorrow.")
        return
    
    # Display parameter summary
    with st.expander("Summary of Parameters"):
        # Build a parameter dictionary to show the user what settings will be used
        param_summary = {
            "Model": selected_model_name,
            "Width": width,
            "Height": height,
            "Number of Images": num_images,            
            "Contrast": contrast,
            "Enhance Prompt": enhance_prompt
        }
        
        # Add conditional parameters based on model type
        if selected_model_type in ["sdxl", "phoenix", "sd15"]:
            if 'alchemy' in locals():
                param_summary["Alchemy"] = alchemy
        
        if selected_model_type == "phoenix" and 'ultra' in locals():
            param_summary["Ultra Quality"] = ultra
        
        if selected_model_type in ["sdxl", "sd15"] and 'photo_real' in locals():
            param_summary["PhotoReal"] = photo_real
            if photo_real and 'photo_real_version' in locals():
                param_summary["PhotoReal Version"] = photo_real_version
        
        if selected_style_uuid:
            param_summary["Style"] = selected_style
        
        if selected_model_type == "sdxl" and 'preset_style_value' in locals() and preset_style_value:
            param_summary["Preset Style"] = preset_style_selection
            
        
        # Convert all values to strings to avoid PyArrow type errors
        param_summary = {k: str(v) for k, v in param_summary.items()}
            
        # Display the parameter summary as a table
        param_df = pd.DataFrame(list(param_summary.items()), columns=["Parameter", "Value"])
        st.table(param_df)
    
    # Generate button with a more prominent design
    generate_col1, generate_col2, generate_col3 = st.columns([1, 2, 1])
    with generate_col2:
        generate_button = st.button("Generate Images", type="primary", use_container_width=True)
    
    if generate_button:
        if not prompt:
            st.error("Please enter a prompt")
            return
            
        with st.spinner("Generating images..."):
            # Prepare base parameters with defaults
            parameters = {
                "modelId": selected_model_id,
                "width": width,
                "height": height,
                "num_images": 1,  # Fixed at 1 image                
                "contrast": contrast,
                "enhancePrompt": True,  # Always enabled                
            }
            
            # Add conditional parameters based on model type
            if selected_style_uuid:
                parameters["styleUUID"] = selected_style_uuid
                
            # Always add these for supported models
            if selected_model_type in ["sdxl", "phoenix", "sd15"]:
                parameters["alchemy"] = True
            
            if selected_model_type == "phoenix":
                parameters["ultra"] = True
            
            # PhotoReal is the only toggle that remains user-controlled
            if selected_model_type in ["sdxl", "sd15"] and 'photo_real' in locals():
                parameters["photoReal"] = photo_real
                if photo_real:
                    parameters["photoRealVersion"] = "v2"  # Always v2
            
            if selected_model_type == "sdxl" and 'preset_style_value' in locals() and preset_style_value:
                parameters["presetStyle"] = preset_style_value
                
                       
            # Clean up parameters - remove None values
            parameters = {k: v for k, v in parameters.items() if v is not None}
            
            # Call API
            # st.write("Sending request with parameters:", json.dumps(parameters, indent=2))
            result, apiCreditCost = leonardo_text_to_image(prompt, parameters)
            

            if result:
                # Update usage
                update_user_usage(st.session_state.user['username'], int(apiCreditCost))
                
                # Display results
                st.subheader("Generated Images")
                
                # Get the generated images from the nested response structure
                generation_data = result.get("generations_by_pk", {})
                generated_images = generation_data.get("generated_images", [])
                
                if generated_images:
                    # Settings for the gallery display
                    if len(generated_images) <= 2:
                        cols = st.columns(len(generated_images))
                        for i, img_data in enumerate(generated_images):
                            with cols[i]:
                                st.write(img_data)
                                img_url = img_data.get("url")
                                if img_url:
                                    st.image(img_url, use_container_width=True)
                                    st.download_button(
                                        label="Download",
                                        data=requests.get(img_url).content,
                                        file_name=f"generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}.png",
                                        mime="image/png"
                                    )
                    else:
                        # For more than 2 images, use a grid layout with multiple rows
                        rows = (len(generated_images) + 1) // 2  # Calculate needed rows (2 images per row)
                        for row in range(rows):
                            row_cols = st.columns(2)  # Always 2 columns
                            for col in range(2):
                                idx = row * 2 + col
                                if idx < len(generated_images):
                                    img_data = generated_images[idx]
                                    img_url = img_data.get("url")
                                    if img_url:
                                        with row_cols[col]:
                                            st.image(img_url, use_container_width=True)
                                            st.download_button(
                                                label="Download",
                                                data=requests.get(img_url).content,
                                                file_name=f"generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{idx}.png",
                                                mime="image/png"
                                            )
                    
                    # Add option to save generation parameters for reproducibility
                    st.subheader("Generation Details")
                    st.json(parameters)
                    
                    # Option to save these parameters as a preset
                    with st.expander("Save as Preset"):
                        preset_name = st.text_input("Preset Name")
                        if st.button("Save Preset") and preset_name:
                            # Here you would implement the preset saving functionality
                            st.success(f"Preset '{preset_name}' saved!")
                    
                    # Log the generation
                    log_generation(
                        username=st.session_state.user['username'],
                        prompt=prompt,
                        source_image_path=None,
                        generation_type="text_to_image",
                        project=selected_project,
                        parameters=parameters,
                        result_images=generated_images,
                        apiCreditCost=apiCreditCost
                    )
                else:
                    st.error("No images were generated. Please try again.")
            else:
                st.error("Generation failed. Please check the parameters and try again.")

def image_to_image_page():
    st.title("Image to Image Generator (Coming Soon)")
    
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
        st.image(source_image, caption="Source Image", use_container_width=True)
        
        # Prompt input
        prompt = st.text_area("Enter your prompt", height=100)
        
        # Advanced options with expander
        with st.expander("Advanced Options"):
            strength = 0.5
            num_images = 1
            select_dimensions = st.selectbox("Select Dimensions", ["Portrait", "Landscape"])
            select_model = st.selectbox("Select Style", ["Raja Ravi Varma", "Creative"])

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
                    "num_images": num_images,
                    "select_model": select_model
                }
                
                # Reset file pointer
                source_image.seek(0)
                
                # Call API
                result = leonardo_image_to_image(prompt, source_image, parameters)
                
                if result:
                    # Update usage
                    update_user_usage(st.session_state.user['username'], 15)
                    
                    # Display results
                    st.subheader("Generated Images")
                    
                    # The response structure will depend on Leonardo's API
                    # This is an example assuming a list of image URLs
                    image_urls = result.get("generations_by_pk", {}).get("generated_images", [])
                    
                    if image_urls:
                        cols = st.columns(len(image_urls))
                        for i, img_data in enumerate(image_urls):
                            with cols[i]:
                                img_url = img_data.get("url")
                                st.image(img_url, use_container_width=True)
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
                            result_images=image_urls,
                            apiCreditCost=len(image_urls)*15
                        )
                    
                    else:
                        st.error("No images were generated. Please try again.")
    else:
        st.info("Please upload a source image to continue")

def history_page():
    st.title("Generation History")
    conn = sqlite3.connect(DB_PATH)
    # Get all generations (for both admin and regular users)
    query = """
     SELECT g.id, g.username, g.prompt, g.generation_type, g.project, 
            g.parameters, g.result_url, g.timestamp, g.apiCreditCost
     FROM generations g
     ORDER BY g.timestamp DESC
     """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Convert to DataFrame for Streamlit display if needed
    if len(df) > 0:
    
        # Format dates for better readability
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Add filtering options
        st.subheader("Filter History")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Filter by project
            all_projects = df['project'].unique().tolist()
            selected_project = st.selectbox("Filter by Project", ["All Projects"] + all_projects)
        
        with col2:
            # Filter by generation type
            all_types = df['generation_type'].unique().tolist()
            selected_type = st.selectbox("Filter by Type", ["All Types"] + all_types)
            
        with col3:
            # Filter by username
            all_users = df['username'].unique().tolist()
            selected_user = st.selectbox("Filter by User", ["All Users"] + all_users)
        
        # Apply filters
        filtered_df = df.copy()
        if selected_project != "All Projects":
            filtered_df = filtered_df[filtered_df['project'] == selected_project]
        if selected_type != "All Types":
            filtered_df = filtered_df[filtered_df['generation_type'] == selected_type]
        if selected_user != "All Users":
            filtered_df = filtered_df[filtered_df['username'] == selected_user]
        
        st.markdown(f"Showing {len(filtered_df)} of {len(df)} generations")
        st.divider()
        
        # Use an expander for each generation
        for i, row in filtered_df.iterrows():
            

            # Parse parameters to get metadata
            params = json.loads(row['parameters'])
            metadata = params.get("display_metadata", {})
            
            # Create a more descriptive title for the expander
            model_name = metadata.get("model_name", "Unknown Model")
            dimensions = metadata.get("dimensions", "")
            timestamp = row['timestamp']
            username = row['username']
            
            expander_title = f"{username} - {model_name} - {dimensions} - {timestamp}"
            
            with st.expander(expander_title):
                # Display in columns - image(s) on left, details on right
                img_col, details_col = st.columns([2, 3])
                
                with img_col:
                    # Parse and display images
                    try:
                        image_urls = json.loads(row['result_url'])
                        if image_urls and len(image_urls) > 0:
                            # Display the first image
                            st.image(image_urls[0], use_container_width=True)
                            
                            # Add download buttons for all images
                            for idx, img_url in enumerate(image_urls):
                                st.download_button(
                                    f"Download Image",
                                    data=requests.get(img_url).content,
                                    file_name=f"generation_{row['id']}_{idx}.png",
                                    mime="image/png",
                                    key=f"download_{row['id']}_{idx}"
                                )
                    except Exception as e:
                        st.error(f"Error displaying images: {str(e)}")
                
                with details_col:
                    # Display generation details in a clean format
                    st.markdown(f"**Project:** {row['project']}")
                    st.markdown(f"**User:** {row['username']}")
                    st.markdown(f"**Type:** {row['generation_type'].replace('_', ' ').title()}")
                    st.markdown(f"**API Credits:** {row['apiCreditCost']}")
                    st.markdown(f"**Prompt:** {row['prompt']}")
                    
                    # Show key generation parameters
                    st.markdown("### Generation Settings")
                    details_table = []
                    
                    # Add model info
                    details_table.append(["Model", metadata.get("model_name", "Unknown")])
                    
                    # Add style info if present
                    if metadata.get("style_name") and metadata.get("style_name") != "None":
                        details_table.append(["Style", metadata.get("style_name")])
                    
                    # Add preset style if present
                    if metadata.get("preset_style") and metadata.get("preset_style") != "None":
                        details_table.append(["Preset Style", metadata.get("preset_style")])
                    
                    # Add other key parameters
                    details_table.append(["Dimensions", metadata.get("dimensions", "Unknown")])                    
                    
                    if "photoReal" in params:
                        details_table.append(["PhotoReal", metadata.get("photo_real", "Unknown")])
                    
                    # Display as a DataFrame for nice formatting
                    st.table(pd.DataFrame(details_table, columns=["Setting", "Value"]))
                    
                    # Option to reuse these settings for a new generation
                    if st.button("Use These Settings", key=f"reuse_{row['id']}"):
                        # Store settings in session state to be used on the generation page
                        st.session_state.reuse_settings = params
                        st.success("Settings saved! Go to the Text to Image tab to use these settings.")
    else:
        st.info("No generations found in your history.")
        
    # Add option to export history as CSV
    if len(df) > 0:
        st.divider()
        st.subheader("Export History")
        
        # Prepare data for export - simplify complex columns
        export_df = df.copy()
        
        # Clean up complex JSON columns for export
        # export_df['parameters'] = export_df['parameters'].apply(
        #     lambda x: json.dumps(json.loads(x).get("display_metadata", {}))
        # )
        # For MongoDB data
        export_df['parameters'] = export_df['parameters'].apply(
            lambda x: json.dumps(json.loads(x).get("display_metadata", {}))
        )
        
        # Convert to CSV
        csv = export_df.to_csv(index=False)
        
        # Add download button
        st.download_button(
            "Download History as CSV",
            data=csv,
            file_name="generation_history.csv",
            mime="text/csv"
        )

def generate_description_page():
    st.title("Coming Soon")

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
        elif page == "Generate Description":
            generate_description_page()
        
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
    # history_page()
