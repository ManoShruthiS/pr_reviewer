# ==============================================================================
# FILE: config.py
# PURPOSE: Reads secret keys and configuration settings from the computer's environment.
#
# HOW TO THINK OF THIS FILE (SIMPLE ANALOGY):
# Think of this like a secure vault manager.
# When our project starts, it goes to the secret notes file (the '.env' file)
# and retrieves password keys (like the GitHub Token or OpenAI Key).
# If the keys exist, it shares them with the app; if not, it keeps them empty so
# our program can still run safely in free offline mode!
# ==============================================================================

# 'os' is a standard Python tool that lets our code talk to the computer's operating system (Windows)
import os

# 'load_dotenv' is a helper tool from the 'python-dotenv' library.
# It automatically finds a hidden file named '.env' and loads any secret settings inside it.
from dotenv import load_dotenv

# Look for the '.env' file in our project folder and load any secrets into memory
load_dotenv()

# Read the GITHUB_TOKEN (used to make faster and more frequent requests to GitHub).
# If no token is provided, it safely defaults to an empty text string ("").
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()

# Read the OPENAI_API_KEY (used if you want to connect to OpenAI's GPT for extra explanations).
# If no key is provided, it safely defaults to an empty text string ("") so no money is spent!
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
