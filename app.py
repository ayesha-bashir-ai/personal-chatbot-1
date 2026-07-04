from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from modules.modules.assistant_core import PersonalAIAssistant

# Load environment variables from .env (if present) before initializing assistant
load_dotenv()

app = FastAPI()

# create assistant after env is loaded so keys are available
assistant = PersonalAIAssistant()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (images, CSS, JS)
app.mount("/static", StaticFiles(directory="."), name="static")

# Homepage
@app.get("/")
def home():
    return FileResponse("Chat.html")

class ChatRequest(BaseModel):
    message: str
    mode: str = "text"

@app.post("/api/chat")
def chat(req: ChatRequest):
    res = assistant.process_input(req.message, input_type=req.mode)
    return {
        "response": res.get("response", ""),
        "success": res.get("success", False),
        "intent": res.get("intent"),
        "confidence": res.get("confidence"),
    }


@app.get("/_debug")
def debug():
    """Lightweight debug endpoint: returns whether API keys were loaded (no secrets)."""
    return {
        "openrouter_present": bool(assistant.config.get("openrouter_api_key")),
    }