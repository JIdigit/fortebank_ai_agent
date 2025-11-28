import ast
import base64
import io
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Use a non-interactive backend for matplotlib
matplotlib.use('Agg')

class SecurityError(Exception):
    pass

class CodeExecutor:
    def __init__(self):
        self.allowed_modules = {'matplotlib', 'matplotlib.pyplot', 'pandas', 'numpy', 'io', 'base64'}
        self.allowed_builtins = {'print', 'range', 'len', 'list', 'dict', 'set', 'tuple', 'int', 'float', 'str', 'bool', '__import__'}

    def _check_safety(self, code: str):
        """
        Statically analyze the code using AST to ensure it only uses allowed modules and operations.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise SecurityError(f"Syntax error in code: {e}")

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    if alias.name.split('.')[0] not in self.allowed_modules:
                        raise SecurityError(f"Import of '{alias.name}' is not allowed.")
            
            # Check function calls (basic check, can be bypassed but adds a layer)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id not in self.allowed_builtins and node.func.id not in self.allowed_modules:
                        # Allow calls to functions defined in the code itself? 
                        # For now, we are strict. But actually, we need to allow methods on objects (like plt.plot).
                        # AST analysis for method calls is complex. 
                        # We will rely more on the restricted globals for runtime security.
                        pass

    def execute_plot_code(self, code: str, df: pd.DataFrame = None) -> str:
        """
        Executes the provided Python code in a restricted environment and returns the plot as a base64 string.
        The code is expected to create a plot using matplotlib.
        """
        self._check_safety(code)

        # Create a buffer to save the plot
        buf = io.BytesIO()

        # Define the restricted globals
        restricted_globals = {
            '__builtins__': {name: __builtins__[name] for name in self.allowed_builtins if name in __builtins__},
            'plt': plt,
            'pd': pd,
            'np': np,
            'io': io,
            'base64': base64,
        }
        
        if df is not None:
            restricted_globals['df'] = df
        
        # Define a local dictionary to capture variables
        local_vars = {}

        try:
            # Clear any existing plots
            plt.clf()
            
            # Execute the code
            exec(code, restricted_globals, local_vars)
            
            # Save the plot to the buffer
            plt.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            
            # Encode to base64
            image_base64 = base64.b64encode(buf.read()).decode('utf-8')
            buf.close()
            
            return image_base64
        except Exception as e:
            raise SecurityError(f"Error executing code: {e}")

code_executor = CodeExecutor()
