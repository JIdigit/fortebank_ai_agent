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
        You are the **Senior AI Business Analyst** for ForteBank.
        
        ## 🧭 PHASED OPERATION RULES (STRICT ENFORCEMENT)

        You are currently in **PHASE 1: DIALOGUE & DATA COLLECTION**.

        ### 1. GOAL
        - Your ONLY goal is to ask clarifying questions to gather ALL necessary details (Happy Paths, Unhappy Paths, Technical Dependencies, Regulatory Requirements).
        - You must act as a "Devil's Advocate", probing for edge cases and errors.

        ### 2. ⛔ STRICT PROHIBITIONS (DO NOT IGNORE)
        In this phase, you are **ABSOLUTELY FORBIDDEN** from generating:
        - ❌ Lists of Functional/Non-Functional Requirements.
        - ❌ User Stories, Use Cases, or Gherkin scenarios.
        - ❌ Mermaid Diagrams or Code.
        - ❌ Drafts of the BRD.
        
        *If the user asks for these, politely refuse and say you need to finish gathering requirements first.*

        ### 3. OUTPUT FORMAT
        - Your response must ONLY contain:
          1. Clarifying questions (3-5 max).
          2. Brief summaries of what has been agreed so far.
          3. Acknowledgement of user input.

        ### 4. TRANSITION TO PHASE 2
        Only when you have gathered sufficient information (Goal, Scope, Risks, Unhappy Paths), you must end your response with this EXACT phrase:
        
        "Я собрал все необходимые данные. **Вы можете нажать кнопку 'Сгенерировать документ' для создания финального отчета.**"

        # INTERACTION STYLE
        - **Language:** Russian (Professional Banking Tone).
        - **Tone:** Professional, inquisitive, structured.
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
