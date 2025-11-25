import os
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, List, Optional

load_dotenv()

class RequirementsGenerator:
    """
    Генератор бизнес-требований и аналитических артефактов.
    Формирует структурированные документы на основе диалога с пользователем.
    """
    
    def __init__(self):
        self.client = OpenAI()
        
    def generate_business_requirements(self, conversation_history: List[Dict], context: Dict) -> Dict:
        """
        Генерирует полный документ бизнес-требований, включая Use Cases, User Stories и Диаграммы.
        Сначала проводит валидацию на наличие Unhappy Path.
        """
        
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in conversation_history
        ])

        # 0. Валидация (The "Devil's Advocate" Mode)
        print("0️⃣ Validating requirements (Devil's Advocate)...")
        validation_result = self.validate_requirements(conversation_text)
        
        if not validation_result.get('valid', True):
            print("❌ Validation failed. Generating clarification questions.")
            # Возвращаем "документ" с вопросами
            return {
                'version': '0.1 (Draft)',
                'generated_at': datetime.now().isoformat(),
                'goal': 'Требуется уточнение требований',
                'description': 'В ходе анализа выявлены критические пробелы в требованиях, касающиеся обработки ошибок и нестандартных ситуаций (Unhappy Path).',
                'validation_questions': validation_result.get('questions', []),
                'is_draft': True
            }

        # 1. Генерация основных требований
        system_prompt = """Ты - Senior AI Business Analyst ForteBank. Твоя задача - создать полный, профессиональный и детальный документ бизнес-требований (BRD).

Документ должен быть максимально полным и содержать следующие разделы:
1. **Цель проекта** - четкая формулировка бизнес-цели.
2. **Описание** - детальное описание задачи и контекста.
3. **Scope (Границы проекта)** - детально: что входит и что НЕ входит.
4. **Бизнес-правила** - МИНИМУМ 5-7 детальных правил.
5. **KPI** - измеримые метрики успеха.
6. **Заинтересованные стороны** - роли и их интересы.
7. **Функциональные требования** - детальный список функций.
8. **Нефункциональные требования** - производительность, безопасность, доступность (NFR).
9. **Риски и ограничения** - потенциальные риски и регуляторные ограничения.
10. **Интеграции** - список систем (ABS, CRM, Processing), с которыми требуется интеграция.
11. **Обработка ошибок (Error Handling)** - описание поведения системы при сбоях.
12. **Требования безопасности (Security)** - аутентификация, авторизация, шифрование, маскирование данных.

ВАЖНО: Приоритезируй информацию, полученную от пользователя в текущем диалоге.

Формат ответа: JSON с ключами для каждого раздела."""
        
        user_prompt = f"""На основе следующего диалога создай детальный документ бизнес-требований:

{conversation_text}

Дополнительный контекст: {context if context else 'Нет дополнительного контекста'}

Верни результат в формате JSON со следующими ключами:
- goal
- description
- scope_in
- scope_out
- business_rules
- kpi
- stakeholders
- functional_requirements
- non_functional_requirements
- risks
- integrations
- error_handling
- security_requirements
"""

        try:
            # Шаг 1: Базовые требования
            print("1️⃣ Generating Base Requirements...")
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            import json
            requirements = json.loads(response.choices[0].message.content)
            requirements['generated_at'] = datetime.now().isoformat()
            requirements['version'] = '1.0'

            # Шаг 2: Генерация Use Cases (автоматически)
            print("2️⃣ Generating Use Cases...")
            requirements['use_cases'] = self.generate_use_cases(requirements)

            # Шаг 3: Генерация User Stories (автоматически)
            print("3️⃣ Generating User Stories...")
            requirements['user_stories'] = self.generate_user_stories(requirements)

            # Шаг 4: Генерация Диаграммы (автоматически)
            print("4️⃣ Generating Diagram...")
            requirements['diagram_code'] = self.generate_process_diagram_code(requirements)
            
            return requirements
            
        except Exception as e:
            print(f"Error generating requirements: {e}")
            return {"error": str(e)}

    def validate_requirements(self, conversation_text: str) -> Dict:
        """
        Проверяет наличие Unhappy Path сценариев.
        Возвращает dict: {'valid': bool, 'questions': List[str]}
        """
        system_prompt = """You are a rigorous Business Analyst (Devil's Advocate). 
Analyze the conversation and check if the user has defined "Unhappy Path" scenarios (errors, edge cases, failures).
If they are missing, generate 3-5 sharp clarifying questions to expose these gaps.
If the requirements seem robust enough (cover at least some errors/exceptions), return valid=True.

Format: JSON { "valid": boolean, "questions": ["Question 1", "Question 2"] }"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this conversation:\n{conversation_text}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            import json
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Validation error: {e}")
            return {'valid': True} # Fallback to allow generation

    def generate_use_cases(self, requirements: Dict) -> List[Dict]:
        """
        Генерирует Use Cases на основе требований.
        """
        
        system_prompt = """Ты - Креативный Старший Бизнес-аналитик. Твоя задача - создать ПОЛНОСТЬЮ ЗАПОЛНЕННЫЕ Use Cases.

КРИТИЧЕСКИЕ ПРАВИЛА:
1. **ЗАПРЕЩЕНО оставлять поля пустыми**, писать "не указано", "TBD" или "N/A".
2. **ДОДУМЫВАЙ ДЕТАЛИ**: Если в требованиях нет конкретики, ты ОБЯЗАН придумать реалистичный сценарий, основываясь на лучших банковских практиках.
3. **ДЕТАЛИЗАЦИЯ**: Основной сценарий должен содержать минимум 5-7 шагов.
4. **РЕАЛИЗМ**: Используй реальные названия систем (CRM, АБС, Скоринг), ролей и данных.

Каждый Use Case должен содержать:
- title (Название)
- actor (Актор - конкретная роль)
- preconditions (Предусловия - состояние системы до начала)
- main_flow (Основной сценарий - список шагов)
- alternative_flows (Альтернативные сценарии - список)
- postconditions (Постусловия - состояние системы после)
- exceptions (Исключения - ошибки и их обработка)

Формат ответа: JSON массив с Use Cases."""

        user_prompt = f"""Создай минимум 3 подробных Use Cases на основе следующего контекста:

Цель проекта: {requirements.get('goal', 'Автоматизация банковского процесса')}
Описание: {requirements.get('description', '')}
Стейкхолдеры: {requirements.get('stakeholders', [])}
Функциональные требования: {requirements.get('functional_requirements', [])}

Помни: Не оставляй пробелов. Если не знаешь точно - моделируй стандартный банковский процесс."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5, # Немного повышаем температуру для креативности
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result.get('use_cases', [])
            
        except Exception as e:
            print(f"Error generating use cases: {e}")
            return []
    
    def generate_user_stories(self, requirements: Dict) -> List[str]:
        """
        Генерирует User Stories с Gherkin Acceptance Criteria.
        """
        
        system_prompt = """Ты - Agile бизнес-аналитик. Создай детальные User Stories на русском языке.
Формат: "Как <роль>, я хочу <действие>, чтобы <цель>"

CRITICAL: Acceptance Criteria MUST use Gherkin syntax (Given/When/Then).
Example:
- Given: Пользователь авторизован
- When: Нажимает кнопку "Оплатить"
- Then: Система проверяет баланс

Формат ответа: JSON массив с user stories."""

        user_prompt = f"""На основе требований создай минимум 5 User Stories:

Функциональные требования: {requirements.get('functional_requirements', [])}
Заинтересованные стороны: {requirements.get('stakeholders', [])}

Верни массив User Stories в формате JSON с полями: story, acceptance_criteria (список строк)."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result.get('user_stories', [])
            
        except Exception as e:
            print(f"Error generating user stories: {e}")
            return []
    
    def generate_process_diagram_code(self, requirements: Dict) -> str:
        """
        Генерирует код для диаграммы процесса в формате Mermaid.
        Выбирает между Flowchart и Sequence Diagram.
        """
        
        system_prompt = """Ты - системный аналитик. Создай диаграмму для визуализации процесса.
Правила:
1. Если процесс описывает интеграцию систем (Front -> API -> ABS), используй **Sequence Diagram** (sequenceDiagram).
2. Если процесс описывает статусную модель или шаги пользователя, используй **Flowchart** (graph TD).
3. Используй синтаксис Mermaid.
4. Верни ТОЛЬКО код диаграммы.

Пример Sequence:
sequenceDiagram
    Participant User
    Participant App
    User->>App: Login
"""

        user_prompt = f"""Создай диаграмму процесса на основе:

Описание: {requirements.get('description', '')}
Интеграции: {requirements.get('integrations', [])}
Функциональные требования: {requirements.get('functional_requirements', [])}

Верни код Mermaid диаграммы."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip().replace('```mermaid', '').replace('```', '')
            
        except Exception as e:
            print(f"Error generating process diagram: {e}")
            return ""
    
    def format_requirements_document(self, requirements: Dict) -> str:
        """
        Форматирует требования в полный Markdown документ.
        """
        
        # Если это черновик с вопросами
        if requirements.get('is_draft'):
            questions_str = "\n".join([f"- {q}" for q in requirements.get('validation_questions', [])])
            return f"""# ⚠️ ТРЕБУЮТСЯ УТОЧНЕНИЯ

В ходе анализа выявлены критические пробелы в требованиях (Unhappy Path, Edge Cases).
Для создания качественного документа, пожалуйста, ответьте на следующие вопросы:

{questions_str}

---
*Пожалуйста, вернитесь в чат и предоставьте ответы на эти вопросы.*
"""

        # Форматирование Use Cases
        use_cases_str = ""
        if requirements.get('use_cases'):
            for uc in requirements['use_cases']:
                use_cases_str += f"### {uc.get('title', 'Use Case')}\n"
                use_cases_str += f"**Актор:** {uc.get('actor', 'Не указан')}\n\n"
                use_cases_str += f"**Предусловия:** {uc.get('preconditions', 'Нет')}\n\n"
                use_cases_str += "**Основной сценарий:**\n"
                if isinstance(uc.get('main_flow'), list):
                    use_cases_str += "\n".join([f"{i+1}. {step}" for i, step in enumerate(uc['main_flow'])])
                else:
                    use_cases_str += str(uc.get('main_flow', ''))
                use_cases_str += "\n\n"
                if uc.get('alternative_flows'):
                    use_cases_str += "**Альтернативные сценарии:**\n"
                    if isinstance(uc.get('alternative_flows'), list):
                        for flow in uc['alternative_flows']:
                            if isinstance(flow, dict):
                                title = flow.get('title', 'Сценарий')
                                steps = flow.get('steps', [])
                                use_cases_str += f"- **{title}**:\n"
                                if isinstance(steps, list):
                                    for step in steps:
                                        use_cases_str += f"  - {step}\n"
                                else:
                                    use_cases_str += f"  - {steps}\n"
                            else:
                                use_cases_str += f"- {flow}\n"
                    else:
                        use_cases_str += str(uc.get('alternative_flows', ''))
                    use_cases_str += "\n\n"
        else:
            use_cases_str = "_Use Cases не сгенерированы_"

        # Форматирование User Stories
        user_stories_str = ""
        if requirements.get('user_stories'):
            for us in requirements['user_stories']:
                user_stories_str += f"- **Story:** {us.get('story', '')}\n"
                if us.get('acceptance_criteria'):
                    user_stories_str += "  - *Acceptance Criteria (Gherkin):*\n"
                    if isinstance(us['acceptance_criteria'], list):
                        user_stories_str += "\n".join([f"    - {ac}" for ac in us['acceptance_criteria']])
                    else:
                        user_stories_str += f"    - {us['acceptance_criteria']}"
                user_stories_str += "\n"
        else:
            user_stories_str = "_User Stories не сгенерированы_"

        doc = f"""# Документ бизнес-требований (BRD)

**Версия:** {requirements.get('version', '1.0')}  
**Дата создания:** {requirements.get('generated_at', datetime.now().isoformat())}

---

## 1. Цель проекта

{requirements.get('goal', 'Не указана')}

---

## 2. Описание

{requirements.get('description', 'Не указано')}

---

## 3. Границы проекта (Scope)

### ✅ Что входит в проект:
{self._format_list(requirements.get('scope_in', []))}

### ❌ Что НЕ входит в проект:
{self._format_list(requirements.get('scope_out', []))}

---

## 4. Бизнес-правила

{self._format_list(requirements.get('business_rules', []))}

---

## 5. Ключевые показатели эффективности (KPI)

{self._format_list(requirements.get('kpi', []))}

---

## 6. Заинтересованные стороны

{self._format_list(requirements.get('stakeholders', []))}

---

## 7. Функциональные требования

{self._format_list(requirements.get('functional_requirements', []))}

---

## 8. Нефункциональные требования (NFR)

{self._format_list(requirements.get('non_functional_requirements', []))}

---

## 9. Риски и ограничения

{self._format_list(requirements.get('risks', []))}

---

## 10. Интеграции

{self._format_list(requirements.get('integrations', []))}

---

## 11. Обработка ошибок (Error Handling)

{self._format_list(requirements.get('error_handling', []))}

---

## 12. Требования безопасности (Security)

{self._format_list(requirements.get('security_requirements', []))}

---

## 13. Use Cases (Сценарии использования)

{use_cases_str}

---

## 14. User Stories (Пользовательские истории)

{user_stories_str}

---

## 15. Диаграмма процесса

```mermaid
{requirements.get('diagram_code', '')}
```

---

*Документ сгенерирован автоматически AI Business Analyst Agent*
"""
        return doc
    
    def _format_list(self, items) -> str:
        """Форматирует список в Markdown."""
        if isinstance(items, list):
            if not items:
                return "- Не указано"
            return "\n".join([f"- {item}" for item in items])
        elif isinstance(items, str):
            return items
        else:
            return "- Не указано"

requirements_generator = RequirementsGenerator()
