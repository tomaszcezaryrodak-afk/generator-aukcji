"""
Konfiguracja centralna - MODEL i get_secret.
Rozwiązuje circular import dashboard <-> extraction.
"""
import os
from dotenv import load_dotenv
load_dotenv()


def get_secret(key, default=""):
    """Pobiera secret z .env lub Streamlit Secrets."""
    val = os.environ.get(key, "")
    if not val:
        try:
            import streamlit as st
            val = st.secrets.get(key, default)
        except Exception:
            val = default
    return val


MODEL = get_secret("GEMINI_MODEL", "gemini-3-pro-image-preview")
