import os
import streamlit as st
from config import settings
import sys

print(f"DEBUG: CWD: {os.getcwd()}", file=sys.stderr)
print(f"DEBUG: FAST_TEST_MODE: {settings.FAST_TEST_MODE}", file=sys.stderr)

from config import Settings
config = Settings(INSIGHT_ENGINE_API_KEY="test")
print(f"DEBUG: Instantiated FAST_TEST_MODE: {config.FAST_TEST_MODE}", file=sys.stderr)
