import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

class AnalyticsEngine:
    def __init__(self):
        # Initialize the client. It will automatically look for OPENAI_API_KEY in env vars.
        self.client = OpenAI()

    def analyze(self, query: str) -> dict:
        """
        Analyzes the user query using OpenAI's GPT model.
        Returns a dictionary with 'text' and optional 'code'.
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o", 
                messages=[
                    {
                        "role": "system", 
                        "content": """You are an expert business analytics AI agent. Analyze the user's business situation, collect requirements, and support the process of improving business processes. 

If the user asks for a visualization, chart, or graph:
1. Generate Python code using `matplotlib.pyplot` (as `plt`) to create the chart.
2. DO NOT use `plt.show()`.
3. Wrap the code in a markdown code block labeled `python`.
4. Provide a brief textual explanation outside the code block.
5. You have access to `pandas` (as `pd`) and `numpy` (as `np`).
6. Use the 'Forte Bank' color palette: Magenta (#981E5B) and Gold (#EBB700) where appropriate.

Example response for chart:
"Here is the sales data visualization."
```python
import matplotlib.pyplot as plt
data = [10, 20, 15, 25]
plt.bar(['Q1', 'Q2', 'Q3', 'Q4'], data, color='#981E5B')
plt.title('Quarterly Sales')
```"""
                    },
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
            )
            content = response.choices[0].message.content
            
            # Extract code if present
            code = None
            if "```python" in content:
                start = content.find("```python") + 9
                end = content.find("```", start)
                code = content[start:end].strip()
                # Remove the code block from the text to avoid double display (optional, but cleaner)
                # content = content[:start-9] + content[end+3:]
            
            return {"text": content, "code": code}
            
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            return {"text": "I apologize, but I am currently unable to access the advanced analytics engine.", "code": None}

analytics_engine = AnalyticsEngine()
