import requests
from typing import Dict, Optional, List
import os
from dotenv import load_dotenv
import re

load_dotenv()

class ConfluenceIntegration:
    """
    Интеграция с Confluence для автоматического создания документации.
    """
    
    def __init__(self):
        raw_url = os.getenv('CONFLUENCE_BASE_URL', '').rstrip('/')
        # Очищаем URL от типичных суффиксов, если пользователь скопировал полный путь
        for suffix in ['/home', '/pages', '/overview', '/src']:
            if raw_url.endswith(suffix):
                raw_url = raw_url[:-len(suffix)]
        
        self.original_base_url = raw_url.rstrip('/')
        self.base_url = self.original_base_url
        self.username = os.getenv('CONFLUENCE_USERNAME', '')
        self.api_token = os.getenv('CONFLUENCE_API_TOKEN', '')
        self.space_key = os.getenv('CONFLUENCE_SPACE_KEY', 'BA')
        
        self.enabled = bool(self.base_url and self.username and self.api_token)
        self.api_base = "" # Будет определен при проверке
        
        if self.enabled:
            print(f"✅ Confluence integration enabled. Configured URL: {self.base_url}")
            # Пытаемся определить правильный API путь
            self._detect_api_url()
        else:
            print("⚠️ Confluence integration disabled - missing configuration")
    
    def _detect_api_url(self):
        """
        Пытается определить правильный URL API (с /wiki или без).
        """
        paths_to_try = [
            f"{self.base_url}/rest/api",      # Как настроено
            f"{self.base_url}/wiki/rest/api", # Если забыли /wiki
        ]
        
        # Если в URL уже есть /wiki, попробуем и без него (на случай если это лишнее)
        if "/wiki" in self.base_url:
            base_without_wiki = self.base_url.replace("/wiki", "")
            paths_to_try.append(f"{base_without_wiki}/rest/api")

        print(f"🔍 Detecting Confluence API URL. Testing paths: {paths_to_try}")

        for path in paths_to_try:
            try:
                # Пробуем получить информацию о текущем пользователе (легкий запрос)
                url = f"{path}/user/current"
                response = requests.get(
                    url,
                    auth=(self.username, self.api_token),
                    headers={"Content-Type": "application/json"},
                    timeout=5
                )
                
                if response.status_code == 200:
                    self.api_base = path
                    print(f"✅ Found working API URL: {self.api_base}")
                    return
                elif response.status_code == 401:
                    print(f"❌ Auth failed for {path} (401). Check username/token.")
                    return # Нет смысла перебирать пути, если пароль неверный
            except Exception as e:
                print(f"⚠️ Error checking path {path}: {e}")
        
        # Если ничего не нашли, оставляем дефолтный (скорее всего будет ошибка)
        self.api_base = f"{self.base_url}/rest/api"
        print(f"⚠️ Could not auto-detect API URL. Defaulting to: {self.api_base}")

    def get_spaces(self) -> Dict:
        """
        Получает список доступных Spaces в Confluence.
        """
        if not self.enabled:
            return {"success": False, "error": "Confluence integration not configured"}
        
        url = f"{self.api_base}/space"
        
        try:
            print(f"📤 Fetching spaces from: {url}")
            response = requests.get(
                url,
                auth=(self.username, self.api_token),
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                spaces = []
                for space in data.get('results', []):
                    spaces.append({
                        "key": space.get("key"),
                        "name": space.get("name"),
                        "type": space.get("type"),
                        "url": space.get("_links", {}).get("webui", "")
                    })
                
                print(f"✅ Found {len(spaces)} spaces: {[s['key'] for s in spaces]}")
                return {"success": True, "spaces": spaces}
            else:
                return {"success": False, "error": f"Status {response.status_code}: {response.text[:200]}"}
                
        except Exception as e:
            return {"success": False, "error": f"Exception: {str(e)}"}

    def create_page(self, title: str, content: str, parent_id: Optional[str] = None) -> Dict:
        """
        Создает страницу в Confluence.
        """
        if not self.enabled:
            return {"success": False, "error": "Not configured"}
        
        # Проверяем, существует ли Space
        if not self._check_space_exists(self.space_key):
             return {
                "success": False, 
                "error": f"Space '{self.space_key}' not found. Please create it in Confluence or check permissions."
            }

        url = f"{self.api_base}/content"
        confluence_content = self._markdown_to_confluence(content)
        
        payload = {
            "type": "page",
            "title": title,
            "space": {"key": self.space_key},
            "body": {
                "storage": {
                    "value": confluence_content,
                    "representation": "storage"
                }
            }
        }
        
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]
        
        try:
            print(f"📤 Creating page '{title}' in space '{self.space_key}' via {url}")
            response = requests.post(
                url,
                json=payload,
                auth=(self.username, self.api_token),
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                # Формируем полный URL
                webui = data.get('_links', {}).get('webui', '')
                # Базовый URL для ссылок берем из original_base_url, но нужно быть аккуратным
                # Обычно webui уже содержит /wiki если надо
                full_url = ""
                if webui.startswith("/wiki"):
                     # Если webui начинается с /wiki, а base_url тоже имеет /wiki, не дублируем
                     domain = self.original_base_url.split("/wiki")[0] 
                     full_url = domain + webui
                else:
                     full_url = self.original_base_url + webui

                return {
                    "success": True,
                    "page_id": data.get("id"),
                    "page_url": full_url,
                    "title": data.get("title")
                }
            else:
                error_msg = f"Failed to create page: {response.status_code} - {response.text}"
                print(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            return {"success": False, "error": f"Exception: {str(e)}"}

    def _check_space_exists(self, space_key: str) -> bool:
        """Проверяет существование Space"""
        url = f"{self.api_base}/space/{space_key}"
        try:
            resp = requests.get(url, auth=(self.username, self.api_token))
            return resp.status_code == 200
        except:
            return False

    
    def update_page(self, page_id: str, title: str, content: str, version: int) -> Dict:
        """
        Обновляет существующую страницу в Confluence.
        """
        
        if not self.enabled:
            return {"success": False, "error": "Confluence integration not configured"}
        
        url = f"{self.base_url}/rest/api/content/{page_id}"
        
        confluence_content = self._markdown_to_confluence(content)
        
        payload = {
            "version": {
                "number": version + 1
            },
            "title": title,
            "type": "page",
            "body": {
                "storage": {
                    "value": confluence_content,
                    "representation": "storage"
                }
            }
        }
        
        try:
            response = requests.put(
                url,
                json=payload,
                auth=(self.username, self.api_token),
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "page_id": data.get("id"),
                    "page_url": f"{self.base_url}{data.get('_links', {}).get('webui', '')}",
                    "version": data.get("version", {}).get("number")
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to update page: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception: {str(e)}"
            }
    
    def _markdown_to_confluence(self, markdown: str) -> str:
        """
        Конвертирует Markdown в Confluence Storage Format.
        Улучшенная версия с правильной обработкой всех элементов.
        """
        
        html = markdown
        
        # 1. Обрабатываем жирный текст
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        
        # 2. Обрабатываем заголовки
        lines = html.split('\n')
        processed_lines = []
        
        for line in lines:
            # H1
            if line.startswith('# ') and not line.startswith('## '):
                processed_lines.append(f'<h1>{line[2:]}</h1>')
            # H2
            elif line.startswith('## ') and not line.startswith('### '):
                processed_lines.append(f'<h2>{line[3:]}</h2>')
            # H3
            elif line.startswith('### '):
                processed_lines.append(f'<h3>{line[4:]}</h3>')
            else:
                processed_lines.append(line)
        
        html = '\n'.join(processed_lines)
        
        # 3. Обрабатываем списки
        lines = html.split('\n')
        result = []
        in_list = False
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('- '):
                if not in_list:
                    result.append('<ul>')
                    in_list = True
                # Убираем "- " и обрабатываем содержимое
                list_content = stripped[2:]
                result.append(f'<li>{list_content}</li>')
            else:
                if in_list:
                    result.append('</ul>')
                    in_list = False
                result.append(line)
        
        if in_list:
            result.append('</ul>')
        
        html = '\n'.join(result)
        
        # 4. Обрабатываем горизонтальные линии
        html = re.sub(r'^---+$', '<hr/>', html, flags=re.MULTILINE)
        
        # 5. Обрабатываем параграфы (группируем непустые строки)
        lines = html.split('\n')
        result = []
        paragraph = []
        
        for line in lines:
            # Если это HTML тег, добавляем как есть
            if line.strip().startswith('<') or line.strip() == '':
                if paragraph:
                    result.append(f'<p>{" ".join(paragraph)}</p>')
                    paragraph = []
                if line.strip():
                    result.append(line)
            else:
                paragraph.append(line.strip())
        
        if paragraph:
            result.append(f'<p>{" ".join(paragraph)}</p>')
        
        html = '\n'.join(result)
        
        # 6. Очищаем лишние пустые параграфы
        html = re.sub(r'<p>\s*</p>', '', html)
        html = re.sub(r'\n{3,}', '\n\n', html)
        
        return html
    
    def create_requirements_page(self, requirements_doc: str, project_name: str) -> Dict:
        """
        Создает страницу с бизнес-требованиями в Confluence.
        """
        
        title = f"Бизнес-требования: {project_name}"
        return self.create_page(title, requirements_doc)

confluence_integration = ConfluenceIntegration()
