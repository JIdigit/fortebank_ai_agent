import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

class AnalyticsEngine:
    def __init__(self):
        # Initialize the client. It will automatically look for OPENAI_API_KEY in env vars.
        self.client = OpenAI()

    def analyze(self, query: str, data_context: str = None, conversation_history: list = None) -> dict:
        """
        Analyzes the user query using OpenAI's GPT model.
        Returns a dictionary with 'text' and optional 'code'.
        """
        system_prompt = """
        You are an expert Senior Business Analyst (AI Agent) at ForteBank. 
        Your goal is to help users define business requirements, analyze processes, and create detailed documentation.

        CRITICAL RULES (MUST FOLLOW):
        1. **Proactive Analysis**: Do NOT just answer the user's question. Actively lead the conversation.
           - If the user's request is broad, you MUST ask 3-5 clarifying questions immediately.
           - Focus questions on: KPIs, Target Audience, Project Scope, Risks, Regulatory Constraints, and System Integrations.
           - Example: "To create a detailed requirement, I need to clarify: Who is the target audience? What are the specific risks? Which systems need to be integrated?"

        2. **Context Priority (Absolute Rule)**: 
           - The User's current input is the SOURCE OF TRUTH.
           - If the User's input contradicts your internal knowledge or previous context, **User's input WINS**.
           - If you detect a conflict (e.g., User says "Courier delivery", but standard process is "Pickup"), you MUST explicitly flag it:
             "Note: Standard process implies Pickup, but based on your request, we are documenting Courier Delivery. Please confirm."

        3. **Structured Thinking**:
           - Always structure your responses. Use bullet points, bold text for emphasis.
           - When analyzing data, look for trends, anomalies, and business opportunities.

        4. **Artifact Generation**:
           - Proactively suggest creating artifacts (Use Cases, Diagrams, User Stories) when you have enough information.
           - Do not generate the full document immediately if requirements are vague. Ask questions first.

        Response Language: Russian (Professional, Business Tone).
        """

        messages = [{"role": "system", "content": system_prompt}]
        
        # Добавляем историю диалога, если она есть
        if conversation_history:
            # Конвертируем историю в формат OpenAI messages
            # Ожидаем, что history это список словарей {'role': 'user'/'assistant', 'content': '...'}
            # Берем последние 10 сообщений для сохранения контекста, но не перегрузки
            recent_history = conversation_history[-10:]
            for msg in recent_history:
                # Фильтруем системные сообщения или ошибки, если они попали в историю
                if msg.get('role') in ['user', 'assistant']:
                    messages.append({"role": msg['role'], "content": msg['content']})

        if data_context:
            messages.append({"role": "system", "content": f"Data Context:\n{data_context}"})
            
        messages.append({"role": "user", "content": query})        
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=messages,
                temperature=0.7,
            )
            content = response.choices[0].message.content
            
            # Extract code if present
            code = None
            if "```python" in content:
                start = content.find("```python") + 9
                end = content.find("```", start)
                code = content[start:end].strip()
                # Remove the code block from the text to avoid double display
                content = content[:start-9] + content[end+3:]
            
            return {"text": content.strip(), "code": code}
            
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            return {"text": "I apologize, but I am currently unable to access the advanced analytics engine.", "code": None}

analytics_engine = AnalyticsEngine()
