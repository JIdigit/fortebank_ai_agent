from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.analytics_engine import analytics_engine

app = FastAPI(title="Business Analytics Agent API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from typing import Optional
from services.code_executor import code_executor

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    image: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "Business Analytics Agent API is running"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint to interact with the Business Analytics Agent.
    """
    analysis_result = analytics_engine.analyze(request.message)
    text_response = analysis_result["text"]
    code = analysis_result["code"]
    
    image_base64 = None
    if code:
        try:
            image_base64 = code_executor.execute_plot_code(code)
        except Exception as e:
            text_response += f"\n\n[Error generating chart: {str(e)}]"

    return ChatResponse(response=text_response, image=image_base64)
