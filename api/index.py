import sys
import os

# Add root directory to sys.path so backend imports resolve seamlessly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
