# Parameters for each model as lists of dictionaries
modelIds = {
    "Leonardo Phoenix 1.0": "de7d3faf-762f-48e0-b3b7-9d0ac3a3fcf3",
    #"Leonardo Phoenix 0.9": "6b645e3a-d64f-4341-a6d8-7a3690fbf042",
    #"Flux Dev": "b2614463-296c-462a-9586-aafdb8f00e36",
    "Flux Schnell": "1dd50843-d653-4516-a8e3-f0238ee453ff",    
    "Leonardo Anime XL": "e71a1c2f-4f80-4800-934f-2c68979d8cc8",
    "Leonardo Lightning XL": "b24e16ff-06e3-43eb-8d33-4416c2d75876",
    "SDXL 1.0": "16e7060a-803e-4df3-97ee-edcfa5dc9cc8",
    "Leonardo Kino XL": "aa77f04e-3eec-4034-9c07-d0f619684628",
    "Leonardo Vision XL": "5c232a9e-9061-4777-980a-ddc8e65647c6",
    "Leonardo Diffusion XL": "1e60896f-3c26-4296-8ecc-53e2afecc132",
    #"AlbedoBase XL": "2067ae52-33fd-4a82-bb92-c2c55e7d2786",
    #"RPG v5": "f1929ea3-b169-4c18-a16c-5d58b4292c69",
    "SDXL 0.9": "b63f7119-31dc-4540-969b-2a9df997e173",
    #"3D Animation Style": "d69c8273-6b17-4a30-a13e-d6637ae1c644",
    #"DreamShaper v7": "ac614f96-1082-45bf-be9d-757f2d31c174"
}

modelTypes = {    
    # Flux Models
    "Flux Dev": "flux",
    "Flux Schnell": "flux",
    
    # Phoenix Models
    "Leonardo Phoenix 1.0": "phoenix",
    "Leonardo Phoenix 0.9": "phoenix",
    
    # SDXL Models
    "SDXL 1.0": "sdxl",
    "SDXL 0.9": "sdxl",
    
    # Fine-tuned SDXL Models
    "Leonardo Anime XL": "sdxl",
    "Leonardo Lightning XL": "sdxl",
    "Leonardo Kino XL": "sdxl",
    "Leonardo Vision XL": "sdxl",
    "Leonardo Diffusion XL": "sdxl",
    "AlbedoBase XL": "sdxl",
    
    # Other Models (based on SD1.5)
    "RPG v5": "sd15",
    "DreamShaper v7": "sd15",
    "3D Animation Style": "sd15"
}


styleUUID = {
    "3D Render": "debdf72a-91a4-467b-bf61-cc02bdeb69c6",
    "Bokeh": "9fdc5e8c-4d13-49b4-9ce6-5a74cbb19177",
    "Cinematic": "a5632c7c-ddbb-4e2f-ba34-8456ab3ac436",
    "Cinematic Concept": "33abbb99-03b9-4dd7-9761-ee98650b2c88",
    "Creative": "6fedbf1f-4a17-45ec-84fb-92fe524a29ef",
    "Dynamic": "111dc692-d470-4eec-b791-3475abac4c46",
    "Fashion": "594c4a08-a522-4e0e-b7ff-e4dac4b6b622",
    "Graphic Design Pop Art": "2e74ec31-f3a4-4825-b08b-2894f6d13941",
    "Graphic Design Vector": "1fbb6a68-9319-44d2-8d56-2957ca0ece6a",
    "HDR": "97c20e5c-1af6-4d42-b227-54d03d8f0727",
    "Illustration": "645e4195-f63d-4715-a3f2-3fb1e6eb8c70",
    "Macro": "30c1d34f-e3a9-479a-b56f-c018bbc9c02a",
    "Minimalist": "cadm8cd6-7838-4c99-b645-df76be8ba8d8",
    "Moody": "621e1c9a-6319-4bee-a12d-ae40659162fa",
    "None": "556c1ee5-ec38-42e8-955a-1e82dad0ffa1",
    "Portrait": "8e2bc543-6ee2-45f9-bcd9-594b6ce84dcd",
    "Pro B&W photography": "22a9a7d2-2166-4d86-80ff-22e2643adbcf",
    "Pro color photography": "7c3f932b-a572-47cb-9b9b-f20211e63b5b",
    "Pro film photography": "581ba6d6-5aac-4492-bebe-54c424a0d46e",
    "Portrait Fashion": "0d34f8e1-46d4-428f-8ddd-4b11811fa7c9",
    "Ray Traced": "b504f83c-3326-4947-82e1-7fe9e839ec0f",
    "Sketch (B&W)": "be8c6b58-739c-4d44-b9c1-b032ed308b61",
    "Sketch (Color)": "093accc3-7633-4ffd-82da-d34000dfc0d6",
    "Stock Photo": "5bdc3f2a-1be6-4d1c-8e77-992a30824a2c",
    "Vibrant": "dee282d3-891f-4f73-ba02-7f8131e5541b",
}

presetStyle = {
    "Bokeh": "BOKEH",
    "Cinematic": "CINEMATIC",
    "Cinematic (Closeup)": "CINEMATIC_CLOSEUP",
    "Creative": "CREATIVE",
    "Fashion": "FASHION",
    "Film": "FILM",
    "Food": "FOOD",
    "HDR": "HDR",
    "Long Exposure": "LONG_EXPOSURE",
    "Macro": "MACRO",
}



common_params = [
    {"contrast": ["3", "3.5", "4"]},
    {"enhancePrompt": ["true", "false"]},
    {"height": "512 - 1536"},
    {"width": "512 - 1536"},
    {"num_images": "1 - 8"},
    {"prompt": "string"},
]


flux_params = [
    # Parameters available for Flux model
    {"styleUUID": "string"},

]

phoenix_params = [
    # Parameters available for Phoenix model
    {"alchemy": ["true", "false"]},
    {"styleUUID": "string"},
    {"ultra": ["true", "false"]},

]

sdxl_params = {
    # Parameters available for SDXL model
    "alchemy": ["true", "false"],
    "photoReal": ["true", "false"], 
    "photoRealVersion": ["v1", "v2"],
    "presetStyle": list(presetStyle.keys()) # Use predefined presetStyle values
}

sd15_params = [
    # Parameters available for SD1.5 model
    {"alchemy": ["true", "false"]},
    {"photoReal": ["true", "false"]},
    {"photoRealVersion": ["v1", "v2"]},
    {"presetStyle": "string"},
]

# Helper function to show available parameters for a selected model
def get_params_for_model(model_name):
    if model_name.lower() == "flux":
        return flux_params
    elif model_name.lower() == "phoenix":
        return phoenix_params
    elif model_name.lower() == "sdxl":
        return sdxl_params
    elif model_name.lower() in ["sd1.5", "sd15"]:
        return sd15_params
    else:
        return "Model not recognized. Choose from: Flux, Phoenix, SDXL, or SD1.5"


def get_model_name_from_id(model_id):
    """Get model name from model ID"""
    from model_parameters import modelIds
    
    for name, id in modelIds.items():
        if id == model_id:
            return name
    return "Unknown Model"

def get_style_name_from_id(style_uuid):
    """Get style name from style UUID"""
    from model_parameters import styleUUID
    
    if not style_uuid:
        return "None"
        
    for name, uuid in styleUUID.items():
        if uuid == style_uuid:
            return name
    return "Custom Style"

