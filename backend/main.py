from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.analytics_engine import analytics_engine
import pandas as pd
import io

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

class ChatResponse(BaseModel):
    response: str
    image: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "Business Analytics Agent API is running"}

@app.post("/chat", response_model=ChatResponse)
async def chat(
    message: str = Form(...),
    file: Optional[UploadFile] = File(None)
):
    """
    Endpoint to interact with the Business Analytics Agent.
    Accepts a message and an optional file (Excel).
    """
    data_context = None
    if file:
        try:
            contents = await file.read()
            df = pd.read_excel(io.BytesIO(contents))
            # Create a summary of the dataframe
            buffer = io.StringIO()
            df.info(buf=buffer)
            info_str = buffer.getvalue()
            
            data_context = f"File Name: {file.filename}\n"
            data_context += f"Columns: {', '.join(map(str, df.columns))}\n"
            data_context += f"First 5 rows:\n{df.head().to_string()}\n"
            data_context += f"Description:\n{df.describe().to_string()}\n"
            data_context += f"Info:\n{info_str}"
        except Exception as e:
            return ChatResponse(response=f"Error processing file: {str(e)}")

    analysis_result = analytics_engine.analyze(message, data_context)
    text_response = analysis_result["text"]
    code = analysis_result["code"]
    
    image_base64 = None
    if code:
        try:
            image_base64 = code_executor.execute_plot_code(code)
        except Exception as e:
            text_response += f"\n\n[Error generating chart: {str(e)}]"

    return ChatResponse(response=text_response, image=image_base64)
