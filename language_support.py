import os
import json
import streamlit as st
from deep_translator import GoogleTranslator

# Dictionary mapping Indian language codes to their names
LANGUAGES = {
    'en': 'English',
    'hi': 'Hindi',
    'bn': 'Bengali',
    'te': 'Telugu',
    'ta': 'Tamil',
    'mr': 'Marathi',
    'gu': 'Gujarati',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'pa': 'Punjabi',
    'ur': 'Urdu',
    'or': 'Odia',
    'as': 'Assamese',
    'sa': 'Sanskrit'
}

def translate_text(text, target_lang):
    """Translate text to target language"""
    if not text or target_lang == 'en':
        return text
    
    try:
        # Initialize translator with source auto-detection
        translator = GoogleTranslator(source='auto', target=target_lang)
        
        # Split text into chunks if it's too long (Google Translate has a limit)
        max_chunk_size = 5000
        chunks = [text[i:i + max_chunk_size] for i in range(0, len(text), max_chunk_size)]
        
        # Translate each chunk and combine
        translated_chunks = []
        for chunk in chunks:
            translated = translator.translate(chunk)
            translated_chunks.append(translated)
        
        return ' '.join(translated_chunks)
    except Exception as e:
        st.error(f"Translation error: {str(e)}")
        return text

def translate_content(content, target_lang):
    """Translate content while preserving formatting"""
    if not content:
        return content
        
    if isinstance(content, str):
        return translate_text(content, target_lang)
    elif isinstance(content, dict):
        translated_dict = {}
        for key, value in content.items():
            translated_dict[key] = translate_content(value, target_lang)
        return translated_dict
    elif isinstance(content, list):
        return [translate_content(item, target_lang) for item in content]
    return content

def get_language_selector():
    """Get language selector widget"""
    if 'selected_language' not in st.session_state:
        st.session_state.selected_language = 'en'
    
    selected_language = st.selectbox(
        "Select Language",
        options=list(LANGUAGES.keys()),
        format_func=lambda x: LANGUAGES[x],
        key='language_selector'
    )
    
    if selected_language != st.session_state.selected_language:
        st.session_state.selected_language = selected_language
        st.rerun()
    
    return selected_language

def adapt_content_for_culture(content, target_lang):
    """Adapt content for cultural context"""
    if not content:
        return content
        
    cultural_context = get_cultural_context(target_lang)
    return format_content_for_culture(content, cultural_context)

def get_cultural_context(lang):
    """Get cultural context for a language"""
    # Add cultural context mappings for Indian languages
    cultural_contexts = {
        'en': {'formal': True, 'direct': True},
        'hi': {'formal': True, 'direct': False},
        'bn': {'formal': True, 'direct': False},
        'te': {'formal': True, 'direct': False},
        'ta': {'formal': True, 'direct': False},
        'mr': {'formal': True, 'direct': False},
        'gu': {'formal': True, 'direct': False},
        'kn': {'formal': True, 'direct': False},
        'ml': {'formal': True, 'direct': False},
        'pa': {'formal': True, 'direct': False},
        'ur': {'formal': True, 'direct': False},
        'or': {'formal': True, 'direct': False},
        'as': {'formal': True, 'direct': False},
        'sa': {'formal': True, 'direct': False}
    }
    return cultural_contexts.get(lang, {'formal': True, 'direct': True})

def format_content_for_culture(content, cultural_context):
    """Format content according to cultural context"""
    if not content:
        return content
        
    if isinstance(content, str):
        # Add cultural formatting logic here
        return content
    elif isinstance(content, dict):
        return {k: format_content_for_culture(v, cultural_context) for k, v in content.items()}
    elif isinstance(content, list):
        return [format_content_for_culture(item, cultural_context) for item in content]
    return content

st.sidebar.markdown("---")
st.sidebar.header("Help & Support")
st.sidebar.markdown(
    "If you encounter any issues, have questions, or want to report a bug, please contact us:<br>"
    "<ul>"
    "<li><a href='mailto:vtu19466@veltech.edu.in'>vtu19466@veltech.edu.in</a></li>"
    "<li><a href='mailto:vtu20519@veltech.edu.in'>vtu20519@veltech.edu.in</a></li>"
    "<li><a href='mailto:vtu20164@veltech.edu.in'>vtu20164@veltech.edu.in</a></li>"
    "</ul>",
    unsafe_allow_html=True
) 