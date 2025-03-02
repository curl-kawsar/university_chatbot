from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
from typing import Dict, Any
from data.config import DATA_FILES
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get environment variables
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")
XAI_API_KEY = os.getenv("XAI_API_KEY")
XAI_BASE_URL = os.getenv("XAI_BASE_URL")
APP_NAME = os.getenv("APP_NAME", "University Assistant API")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "An AI-powered assistant for university information")
ALLOW_ORIGINS = os.getenv("ALLOW_ORIGINS", "*").split(",")
ALLOW_METHODS = os.getenv("ALLOW_METHODS", "*").split(",")
ALLOW_HEADERS = os.getenv("ALLOW_HEADERS", "*").split(",")

app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION
)

# Configure CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=ALLOW_METHODS,
    allow_headers=ALLOW_HEADERS,
    expose_headers=ALLOW_HEADERS
)

def load_data():
    """Load data from JSON files"""
    data = {}
    for key, filepath in DATA_FILES.items():
        try:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Data file not found: {filepath}")
            with open(filepath, 'r') as f:
                data[key] = json.load(f)
        except Exception as e:
            print(f"Error loading {filepath}: {str(e)}")
            data[key] = {}
    return data

# Load data at startup
data = load_data()

class ChatRequest(BaseModel):
    message: str

class UpdateRequest(BaseModel):
    file_name: str
    new_data: dict

def create_context_message():
    """Create a context message from all available data"""
    data_sections = {
        "Academic Deadlines": data["academic_deadlines"],
        "Course Information": data["course_information"],
        "Student Support": data["student_service_support"],
        "Library Books": data["library_books_list"],
        "Transport Services": data["transport_service"],
        "Paper Recheck": data["paper_recheck"]
    }
    
    context_parts = ["You are an AI assistant for our university. Use ONLY the following information to answer queries:"]
    
    for title, content in data_sections.items():
        context_parts.append(f"\n{title}:\n{json.dumps(content, indent=2)}")
    
    context_parts.append("""
Rules:
1. Use ONLY above data
2. If you don't have the information, say 'Please Contact with your Academic Advisor'
3. Quote exact dates/times
4. Be direct and precise""")
    
    return "\n".join(context_parts)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "online",
        "endpoints": {
            "/api/chat": "Chat with the AI assistant",
            "/api/data/{file_name}": "Get specific data",
            "/api/admin/update": "Update data (Admin)",
            "/api/admin/files": "List available files"
        }
    }

@app.get("/api/data/{file_name}")
async def get_data(file_name: str):
    """Get data from a specific file"""
    if file_name not in data:
        raise HTTPException(status_code=404, detail="File not found")
    return {"data": data[file_name]}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint with improved response handling"""
    try:
        from openai import OpenAI
        
        if not XAI_API_KEY:
            raise HTTPException(status_code=500, detail="API key not configured")
            
        client = OpenAI(api_key=XAI_API_KEY, base_url=XAI_BASE_URL)
        
        system_message = create_context_message()
        user_message = f"""Based ONLY on the exact data provided above, answer this question: {request.message}
        You MUST use the exact dates and information from the data. DO NOT provide general advice."""
        
        stream = client.chat.completions.create(
            model="grok-2-latest",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            stream=True 
        )
        
        response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                response += chunk.choices[0].delta.content
        
        # Post-process response for specific queries
        if any(keyword in request.message.lower() for keyword in ["exam", "deadline", "date"]):
            relevant_data = data["academic_deadlines"]
            for key, value in relevant_data.items():
                if key in request.message.lower() and value not in response:
                    response = f"According to our academic calendar, the {key.replace('_', ' ')} is {value}. {response}"
        
        return {
            "response": response,
            "status": "success",
            "source": APP_NAME
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.post("/api/admin/update")
async def update_data(request: UpdateRequest):
    """Update data in a specific file"""
    try:
        file_name = request.file_name
        new_data = request.new_data
        
        if file_name not in data:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Update the data in memory
        if isinstance(data[file_name], dict):
            data[file_name].update(new_data)
        elif isinstance(data[file_name], list):
            if isinstance(new_data, list):
                data[file_name].extend(new_data)
            else:
                data[file_name].append(new_data)
        
        # Save to file
        file_path = DATA_FILES[file_name]
        with open(file_path, 'w') as f:
            json.dump(data[file_name], f, indent=4)
        
        return {
            "status": "success",
            "message": f"Data updated successfully in {file_name}",
            "updated_data": data[file_name]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating data: {str(e)}")

@app.get("/api/admin/files")
async def get_available_files():
    """Get list of available data files"""
    return {"files": list(DATA_FILES.keys())}

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)