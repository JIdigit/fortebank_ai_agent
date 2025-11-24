from fastapi import FastAPI, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.analytics_engine import analytics_engine
from services.requirements_generator import requirements_generator
from services.confluence_integration import confluence_integration
import pandas as pd
import io
from typing import Optional, List, Dict
from datetime import datetime
import uuid

app = FastAPI(title="Business Analytics Agent API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from services.code_executor import code_executor

# In-memory session storage (в продакшене использовать Redis или БД)
sessions = {}

class ChatResponse(BaseModel):
    response: str
    image: Optional[str] = None
    session_id: Optional[str] = None

class RequirementsRequest(BaseModel):
    session_id: str
    project_name: str
    additional_context: Optional[Dict] = None

class RequirementsResponse(BaseModel):
    success: bool
    requirements: Optional[Dict] = None
    document: Optional[str] = None
    error: Optional[str] = None

class ArtifactsRequest(BaseModel):
    requirements: Dict
    artifact_type: str  # "use_cases", "user_stories", "process_diagram"

class ArtifactsResponse(BaseModel):
    success: bool
    artifacts: Optional[List] = None
    diagram: Optional[str] = None
    error: Optional[str] = None

class ConfluencePublishRequest(BaseModel):
    project_name: str
    document: str
    
class ConfluencePublishResponse(BaseModel):
    success: bool
    page_url: Optional[str] = None
    error: Optional[str] = None

@app.get("/")
async def root():
    return {
        "message": "Business Analytics Agent API is running",
        "version": "2.0",
        "features": [
            "Chat with AI analyst",
            "Generate business requirements",
            "Create use cases and user stories",
            "Generate process diagrams",
            "Confluence integration"
        ]
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(
    message: str = Form(...),
    file: Optional[UploadFile] = File(None),
    session_id: Optional[str] = Form(None)
):
    """
    Endpoint to interact with the Business Analytics Agent.
    Accepts a message and an optional file (Excel).
    Maintains conversation history via session_id.
    """
    
    # Создаем или получаем сессию
    if not session_id:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "context": {}
        }
    
    session = sessions.get(session_id, {
        "created_at": datetime.now().isoformat(),
        "messages": [],
        "context": {}
    })
    
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
            
            session["context"]["last_file"] = file.filename
            session["context"]["file_data"] = data_context
        except Exception as e:
            return ChatResponse(
                response=f"Ошибка обработки файла: {str(e)}",
                session_id=session_id
            )

    # Сохраняем сообщение пользователя
    session["messages"].append({
        "role": "user",
        "content": message,
        "timestamp": datetime.now().isoformat()
    })

    analysis_result = analytics_engine.analyze(
        query=message, 
        data_context=data_context,
        conversation_history=session["messages"]
    )
    text_response = analysis_result["text"]
    code = analysis_result["code"]
    
    # Сохраняем ответ ассистента
    session["messages"].append({
        "role": "assistant",
        "content": text_response,
        "timestamp": datetime.now().isoformat()
    })
    
    sessions[session_id] = session
    
    image_base64 = None
    if code:
        try:
            image_base64 = code_executor.execute_plot_code(code)
        except Exception as e:
            text_response += f"\n\n[Ошибка генерации графика: {str(e)}]"

    return ChatResponse(
        response=text_response,
        image=image_base64,
        session_id=session_id
    )

@app.post("/generate-requirements", response_model=RequirementsResponse)
async def generate_requirements(request: RequirementsRequest):
    """
    Генерирует документ бизнес-требований на основе диалога.
    """
    
    session = sessions.get(request.session_id)
    if not session:
        return RequirementsResponse(
            success=False,
            error="Сессия не найдена. Пожалуйста, начните диалог сначала."
        )
    
    try:
        start_time = datetime.now()
        
        # Генерируем требования
        requirements = requirements_generator.generate_business_requirements(
            conversation_history=session["messages"],
            context=request.additional_context or session.get("context", {})
        )
        
        if "error" in requirements:
            return RequirementsResponse(
                success=False,
                error=requirements["error"]
            )
        
        # Форматируем документ
        document = requirements_generator.format_requirements_document(requirements)
        
        # Сохраняем в сессию
        session["requirements"] = requirements
        session["requirements_document"] = document
        sessions[request.session_id] = session
        
        end_time = datetime.now()
        generation_time = (end_time - start_time).total_seconds()
        
        return RequirementsResponse(
            success=True,
            requirements=requirements,
            document=document
        )
        
    except Exception as e:
        return RequirementsResponse(
            success=False,
            error=f"Ошибка генерации требований: {str(e)}"
        )

@app.post("/generate-artifacts", response_model=ArtifactsResponse)
async def generate_artifacts(request: ArtifactsRequest):
    """
    Генерирует аналитические артефакты (Use Cases, User Stories, диаграммы).
    """
    
    try:
        if request.artifact_type == "use_cases":
            artifacts = requirements_generator.generate_use_cases(request.requirements)
            return ArtifactsResponse(success=True, artifacts=artifacts)
            
        elif request.artifact_type == "user_stories":
            artifacts = requirements_generator.generate_user_stories(request.requirements)
            return ArtifactsResponse(success=True, artifacts=artifacts)
            
        elif request.artifact_type == "process_diagram":
            diagram = requirements_generator.generate_process_diagram_code(request.requirements)
            return ArtifactsResponse(success=True, diagram=diagram)
            
        else:
            return ArtifactsResponse(
                success=False,
                error=f"Неизвестный тип артефакта: {request.artifact_type}"
            )
            
    except Exception as e:
        return ArtifactsResponse(
            success=False,
            error=f"Ошибка генерации артефактов: {str(e)}"
        )

@app.post("/publish-to-confluence", response_model=ConfluencePublishResponse)
async def publish_to_confluence(request: ConfluencePublishRequest):
    """
    Публикует документ бизнес-требований в Confluence.
    """
    
    try:
        result = confluence_integration.create_requirements_page(
            requirements_doc=request.document,
            project_name=request.project_name
        )
        
        if result.get("success"):
            return ConfluencePublishResponse(
                success=True,
                page_url=result.get("page_url")
            )
        else:
            return ConfluencePublishResponse(
                success=False,
                error=result.get("error", "Неизвестная ошибка")
            )
            
    except Exception as e:
        return ConfluencePublishResponse(
            success=False,
            error=f"Ошибка публикации в Confluence: {str(e)}"
        )

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """
    Получает информацию о сессии.
    """
    session = sessions.get(session_id)
    if not session:
        return {"error": "Сессия не найдена"}
    
    return {
        "session_id": session_id,
        "created_at": session.get("created_at"),
        "message_count": len(session.get("messages", [])),
        "has_requirements": "requirements" in session
    }

@app.get("/health")
async def health_check():
    """
    Проверка состояния сервиса и его компонентов.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(sessions),
        "confluence_enabled": confluence_integration.enabled
    }

@app.get("/test-confluence")
async def test_confluence():
    """
    Тестовый endpoint для проверки подключения к Confluence.
    """
    if not confluence_integration.enabled:
        return {
            "success": False,
            "error": "Confluence integration is not configured",
            "config": {
                "base_url": bool(confluence_integration.base_url),
                "username": bool(confluence_integration.username),
                "api_token": bool(confluence_integration.api_token),
                "space_key": confluence_integration.space_key
            }
        }
    
    return {
        "success": True,
        "message": "Confluence integration is configured",
        "config": {
            "base_url": confluence_integration.base_url,
            "username": confluence_integration.username,
            "space_key": confluence_integration.space_key,
            "api_token_set": bool(confluence_integration.api_token)
        }
    }

@app.get("/confluence-spaces")
async def get_confluence_spaces():
    """
    Получает список доступных Confluence Spaces.
    """
    result = confluence_integration.get_spaces()
    return result
