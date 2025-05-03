import os
import streamlit as st
import json
import google.generativeai as genai
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import pytesseract
import random
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pathlib
import sys
from io import StringIO
import hashlib
import database
from language_support import get_language_selector, translate_text, translate_content

# Load environment variables
load_dotenv()

# Configure your Gemini API key here
GENIE_API_KEY = os.getenv("GENIE_API_KEY")

if not GENIE_API_KEY:
    st.error("Google Gemini API Key not found! Please check your .env file.")
    st.stop()

genai.configure(api_key=GENIE_API_KEY)

# Configure Tesseract
pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

# Initialize database
database.init_db()

# Add settings button in the sidebar
with st.sidebar:
    st.title("⚙️ Settings")
    selected_language = get_language_selector()

def extract_text_from_file(uploaded_file):
    """Extract text content from uploaded file."""
    file_type = uploaded_file.name.split(".")[-1].lower()
    try:
        if file_type == "txt":
            return uploaded_file.read().decode("utf-8")
        elif file_type == "pdf":
            pdf_reader = PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        elif file_type == "docx":
            doc = Document(uploaded_file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        elif file_type in ["png", "jpeg", "jpg"]:
            image = Image.open(uploaded_file)
            return pytesseract.image_to_string(image)
        else:
            st.error("Unsupported file type! Please upload .txt, .pdf, .docx, or image files (.png, .jpeg, .jpg).")
            return None
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

def generate_summary(text_content):
    """Generate a summary of the text content using Google Gemini API"""
    prompt = f"""
    Please provide a comprehensive summary of the following text. 
    Include the main points and key takeaways in a clear, concise format.
    
    Text: {text_content}
    """

    try:
        model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp")
        response = model.generate_content(prompt)
        summary = response.text
        
        # Translate summary to selected language if not English
        if 'selected_language' in st.session_state and st.session_state.selected_language != 'en':
            summary = translate_text(summary, st.session_state.selected_language)
            
        return summary
    except Exception as e:
        st.error(f"Error generating summary: {e}")
        return None

def generate_flashcards(text_content):
    """Generate flashcards using Google Gemini API"""
    prompt = f"""
    Create 9 study flashcards from the following text.
    Your response must be in valid JSON format.
    Each flashcard should have a clear question/concept on the front and a concise answer/explanation on the back.
    
    Text: {text_content}
    
    Response must be in this exact JSON format:
    {{
        "flashcards": [
            {{
                "front": "Question or concept here",
                "back": "Answer or explanation here"
            }},
            ... more cards ...
        ]
    }}
    
    Ensure you create exactly 9 flashcards and the response is strictly in this JSON format.
    """

    try:
        model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp")
        response = model.generate_content(prompt)
        
        # Clean and validate the response text
        response_text = response.text.strip()
        
        # Remove any markdown code block indicators if present
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "", 1)
        if response_text.startswith("```"):
            response_text = response_text.replace("```", "", 1)
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        # Parse the JSON
        flashcards_data = json.loads(response_text)
        
        # Validate the structure
        if not isinstance(flashcards_data, dict) or "flashcards" not in flashcards_data:
            raise ValueError("Invalid response format")
        
        return flashcards_data["flashcards"]
    except json.JSONDecodeError as e:
        st.error(f"Error parsing flashcards response: {str(e)}")
        return []
    except Exception as e:
        st.error(f"Error generating flashcards: {str(e)}")
        return []

def fetch_questions(text_content, quiz_level):
    """Fetch MCQ questions using Google Gemini API"""
    prompt = f"""
    Text: {text_content}
    You are an AI that generates multiple-choice quiz questions.
    Based on the given text, create 10 MCQs at a {quiz_level} level.
    Format the output as JSON with keys: mcq, options (a, b, c, d), and correct.
    Example:
    {{
        "mcqs": [
            {{
                "mcq": "What is Python?",
                "options": {{
                    "a": "A snake",
                    "b": "A programming language",
                    "c": "A car",
                    "d": "A fruit"
                }},
                "correct": "b"
            }}
        ]
    }}
    """

    try:
        model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp")
        response = model.generate_content(prompt)
        
        # Clean and validate the response text
        response_text = response.text.strip()
        
        # Remove any markdown code block indicators if present
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "", 1)
        if response_text.startswith("```"):
            response_text = response_text.replace("```", "", 1)
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        # Parse the JSON
        questions_data = json.loads(response_text)
        questions = questions_data.get("mcqs", [])
        
        # Translate questions if language is not English
        if 'selected_language' in st.session_state and st.session_state.selected_language != 'en':
            for question in questions:
                question['mcq'] = translate_text(question['mcq'], st.session_state.selected_language)
                for option_key, option_text in question['options'].items():
                    question['options'][option_key] = translate_text(option_text, st.session_state.selected_language)
        
        return questions
    except Exception as e:
        st.error(f"Error parsing response: {e}")
        return []

def fetch_true_false_questions(text_content, quiz_level):
    """Fetch True/False questions using Google Gemini API"""
    prompt = f"""
    Text: {text_content}
    You are an AI that generates True/False quiz questions.
    Based on the given text, create 10 True/False questions at a {quiz_level} level.
    Format the output as JSON with keys: question, correct_answer (true/false).
    Example:
    {{
        "true_false": [
            {{
                "question": "Python is a programming language.",
                "correct_answer": true
            }}
        ]
    }}
    """

    try:
        model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp")
        response = model.generate_content(prompt)
        
        # Clean and validate the response text
        response_text = response.text.strip()
        
        # Remove any markdown code block indicators if present
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "", 1)
        if response_text.startswith("```"):
            response_text = response_text.replace("```", "", 1)
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        # Parse the JSON
        questions_data = json.loads(response_text)
        questions = questions_data.get("true_false", [])
        
        # Translate questions if language is not English
        if 'selected_language' in st.session_state and st.session_state.selected_language != 'en':
            for question in questions:
                question['question'] = translate_text(question['question'], st.session_state.selected_language)
        
        return questions
    except Exception as e:
        st.error(f"Error parsing response: {e}")
        return []

def save_quiz_results():
    """Save quiz results to session state history and update gamification elements"""
    if "quiz_history" not in st.session_state:
        st.session_state.quiz_history = []
    
    result = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "quiz_type": quiz_type,
        "level": quiz_level,
        "score": st.session_state.marks,
        "total": len(st.session_state.questions)
    }
    st.session_state.quiz_history.append(result)
    
    # Update gamification elements
    if st.session_state.authenticated:
        # Update streak
        database.update_streak(st.session_state.current_user)
        
        # Award achievements based on quiz performance
        if result["score"] == result["total"]:
            # Perfect score achievement
            achievement = database.create_achievement(
                "Perfect Score",
                "Completed a quiz with 100% accuracy",
                100,
                "🏆"
            )
            if achievement:
                database.award_achievement(st.session_state.current_user, achievement["id"])
        
        if result["level"] == "hard" and result["score"] >= result["total"] * 0.8:
            # Hard mode master achievement
            achievement = database.create_achievement(
                "Hard Mode Master",
                "Scored 80% or higher on a hard difficulty quiz",
                200,
                "🎯"
            )
            if achievement:
                database.award_achievement(st.session_state.current_user, achievement["id"])
        
        # Award badges for consistency
        if len(st.session_state.quiz_history) >= 10:
            badge = database.create_badge(
                "Quiz Master",
                "Completed 10 quizzes",
                "📚"
            )
            if badge:
                database.award_badge(st.session_state.current_user, badge["id"])
        
        # Update leaderboard scores
        leaderboard = database.create_leaderboard(
            "Quiz Performance",
            "Overall quiz performance leaderboard",
            "quiz"
        )
        if leaderboard:
            total_score = sum(q["score"] for q in st.session_state.quiz_history)
            database.update_leaderboard_score(
                leaderboard["id"],
                st.session_state.current_user,
                total_score
            )

def show_analytics():
    """Display analytics dashboard"""
    if "quiz_history" in st.session_state and st.session_state.quiz_history:
        st.subheader("Your Learning Progress")
        df = pd.DataFrame(st.session_state.quiz_history)
        
        # Show performance trend
        fig = px.line(df, x="date", y="score", title="Score History")
        st.plotly_chart(fig)
        
        # Show statistics by difficulty level
        st.write("Performance by Difficulty Level")
        level_stats = df.groupby("level")["score"].mean().round(2)
        st.bar_chart(level_stats)

def create_study_timer():
    """Create a Pomodoro study timer"""
    if "timer_running" not in st.session_state:
        st.session_state.timer_running = False
        st.session_state.timer_duration = 25  # minutes
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.timer_duration = st.number_input(
            "Study Duration (minutes)", 
            min_value=1, 
            max_value=60, 
            value=25
        )
    
    with col2:
        if st.button("Start Timer" if not st.session_state.timer_running else "Stop Timer"):
            st.session_state.timer_running = not st.session_state.timer_running
            
    if st.session_state.timer_running:
        placeholder = st.empty()
        for mins in range(st.session_state.timer_duration * 60, -1, -1):
            mm, ss = divmod(mins, 60)
            placeholder.metric("Time Remaining", f"{mm:02d}:{ss:02d}")
            time.sleep(1)

def get_youtube_recommendations(text_content):
    """Get relevant YouTube video recommendations based on the content"""
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
    
    if not YOUTUBE_API_KEY:
        st.error("YouTube API Key not found! Please check your .env file.")
        st.info("Make sure your .env file exists and contains YOUTUBE_API_KEY=your_key")
        return []
    
    try:
        # Get better search keywords using Gemini
        prompt = f"""
        Analyze this text and generate 2-3 specific search phrases for educational videos.
        Make the phrases very specific to the main topics in the text.
        Format: Return only the search phrases, one per line, no numbering or bullets.
        
        Text: {text_content[:1000]}  # Using first 1000 chars to stay within limits
        """
        
        model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp")
        response = model.generate_content(prompt)
        search_phrases = response.text.strip().split('\n')
        
        # Initialize YouTube API client
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        videos = []
        for phrase in search_phrases:
            # Enhance search query with educational terms
            search_query = f"{phrase.strip()} tutorial explanation"
            st.write(f"Searching for: {search_query}")  # Debug info
            
            request = youtube.search().list(
                part="snippet",
                q=search_query,
                type="video",
                videoDefinition="high",
                relevanceLanguage="en",
                maxResults=2,
                videoDuration="medium",
                order="relevance",
                safeSearch="strict",
                # Add education-focused filters
                topicId="/m/01k8wb",  # Knowledge/Education topic
            )
            
            response = request.execute()
            
            if 'items' in response:
                for item in response['items']:
                    # Check if video is not already in the list
                    video_id = item['id']['videoId']
                    if not any(v['video_id'] == video_id for v in videos):
                        video = {
                            'title': item['snippet']['title'],
                            'description': item['snippet']['description'],
                            'thumbnail': item['snippet']['thumbnails']['medium']['url'],
                            'video_id': video_id,
                            'url': f"https://www.youtube.com/watch?v={video_id}",
                            'search_phrase': phrase.strip()  # Store the search phrase that found this video
                        }
                        videos.append(video)
        
        # If we found videos, show them grouped by search phrase
        if videos:
            st.subheader("Found Educational Videos")
            for phrase in search_phrases:
                phrase_videos = [v for v in videos if v['search_phrase'] == phrase.strip()]
                if phrase_videos:
                    st.write(f"**Videos related to: {phrase}**")
                    cols = st.columns(len(phrase_videos))
                    for idx, video in enumerate(phrase_videos):
                        with cols[idx]:
                            st.markdown(f"""
                            <div style="border:1px solid #ddd; padding:10px; border-radius:5px; margin:5px;">
                                <img src="{video['thumbnail']}" style="width:100%;">
                                <h4>{video['title']}</h4>
                                <p>{video['description'][:100]}...</p>
                                <a href="{video['url']}" target="_blank">Watch Video</a>
                            </div>
                            """, unsafe_allow_html=True)
        
        return videos
            
    except HttpError as e:
        st.error(f"YouTube API Error: {str(e)}")
        return []
    except Exception as e:
        st.error(f"Unexpected Error: {str(e)}")
        st.write("Error type:", type(e).__name__)
        return []

def get_book_suggestions(text_content):
    """Generate book suggestions based on the content"""
    try:
        # Analyze content for targeted recommendations
        analysis_prompt = f"""
        Analyze this educational content and provide:
        1. The MAIN TOPIC being discussed
        2. THREE SPECIFIC CONCEPTS covered
        3. The technical LEVEL (beginner/intermediate/advanced)

        Format your response exactly like this:
        MAIN: (specific topic or technology)
        CONCEPTS: (list the 3 main concepts)
        LEVEL: (level)

        Text: {text_content[:1500]}
        """
        
        model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp",
                                    generation_config={
                                        'temperature': 0.1
                                    })
        analysis = model.generate_content(analysis_prompt)
        
        # Get relevant book recommendations
        recommendation_prompt = f"""
        Based on this analysis: {analysis.text}

        Suggest 5 SPECIFIC books that directly cover these concepts.
        For each book provide:
        1. Title (must be a real, published book)
        2. Author name(s)
        3. Publisher
        4. Publication year
        5. ISBN-13 number
        6. Brief description explaining how it relates to these specific concepts
        7. Technical level
        8. Key topics covered (comma separated)

        Format as JSON:
        {{
            "books": [
                {{
                    "title": "exact book title",
                    "author": "author name(s)",
                    "publisher": "publisher name",
                    "year": "publication year",
                    "isbn": "ISBN-13 number",
                    "description": "how this book relates to the concepts",
                    "level": "technical level",
                    "topics": "key topics covered"
                }}
            ]
        }}

        IMPORTANT:
        - Only suggest real, published books with valid ISBNs
        - Focus on books most relevant to the specific concepts
        - Include only recent editions (last 5 years when possible)
        - Ensure books are widely available
        - Explain relevance to the concepts in description
        """

        recommendations = model.generate_content(recommendation_prompt)
        
        # Parse recommendations
        rec_text = recommendations.text.strip()
        if rec_text.startswith("```json"):
            rec_text = rec_text.replace("```json", "", 1)
        if rec_text.startswith("```"):
            rec_text = rec_text.replace("```", "", 1)
        if rec_text.endswith("```"):
            rec_text = rec_text[:-3]
        
        # Validate and return books
        books = json.loads(rec_text.strip())["books"]
        
        # Filter books with valid ISBNs (basic validation)
        valid_books = []
        for book in books:
            isbn = book.get("isbn", "").replace("-", "").replace(" ", "")
            if len(isbn) == 13 and isbn.isdigit():
                valid_books.append(book)
        
        return valid_books

    except Exception as e:
        st.error(f"Error generating book suggestions: {e}")
        return []

def get_tech_news(text_content):
    """Get recent news related to the topic"""
    try:
        # First analyze the content to identify key topics
        topic_prompt = f"""
        Analyze this content and identify:
        1. The main technology/topic
        2. 2-3 key technical terms/concepts

        Format your response exactly like this:
        MAIN: (main topic)
        TERMS: (key terms, comma separated)

        Text: {text_content[:1000]}
        """
        
        model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp",
                                    generation_config={
                                        'temperature': 0.1
                                    })
        topic_analysis = model.generate_content(topic_prompt)
        
        # Get recent news based on the analysis
        news_prompt = f"""
        Based on this analysis: {topic_analysis.text}

        Generate 3 recent news items about these topics from these sources ONLY:
        - TechCrunch (techcrunch.com)
        - The Verge (theverge.com)
        - VentureBeat (venturebeat.com)
        - TechRadar (techradar.com)
        - ZDNet (zdnet.com)

        Each news item must be:
        1. From the last 3 months
        2. Real and verifiable
        3. Related to the main topic or terms
        4. Include ONLY working URLs from the above domains

        Format EXACTLY as this JSON (no extra text):
        {{
            "news": [
                {{
                    "title": "Actual news headline",
                    "source": "Source name (e.g. TechCrunch)",
                    "date": "MM/YYYY",
                    "summary": "Brief news summary",
                    "category": "Update/Release/Research",
                    "url": "https://www.[sourcedomain].com/actual-article-path"
                }}
            ]
        }}

        IMPORTANT: Only include URLs that match the exact domain patterns of the sources listed above.
        """

        news_response = model.generate_content(news_prompt)
        
        # Clean and parse the response
        response_text = news_response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "", 1)
        if response_text.startswith("```"):
            response_text = response_text.replace("```", "", 1)
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        response_text = response_text.strip()
        
        # Parse and validate news items
        news_data = json.loads(response_text)
        valid_domains = [
            "techcrunch.com",
            "theverge.com", 
            "venturebeat.com",
            "techradar.com",
            "zdnet.com"
        ]
        
        # Filter only news items with valid URLs
        valid_news = []
        for news in news_data.get("news", []):
            url = news.get("url", "").lower()
            if any(domain in url for domain in valid_domains):
                valid_news.append(news)
        
        return valid_news

    except Exception as e:
        st.error(f"Error fetching news: {str(e)}")
        return []

def generate_roadmap(text_content):
    """Generate a learning roadmap based on the content"""
    try:
        # Analyze content to determine topic and scope
        analysis_prompt = f"""
        Analyze this educational content and identify:
        1. Main topic/technology
        2. Current level (beginner/intermediate/advanced)
        3. Key concepts covered
        4. Prerequisites needed

        Format your response exactly like this:
        TOPIC: (main topic)
        LEVEL: (current level)
        CONCEPTS: (key concepts)
        PREREQS: (prerequisites)

        Text: {text_content[:1500]}
        """
        
        model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp",
                                    generation_config={
                                        'temperature': 0.1
                                    })
        analysis = model.generate_content(analysis_prompt)
        
        # Generate detailed roadmap
        roadmap_prompt = f"""
        Based on this analysis: {analysis.text}

        Create a detailed learning roadmap with these components:
        1. Prerequisites (what to learn first)
        2. Core Concepts (main topics to master)
        3. Advanced Topics (next steps)
        4. Projects (hands-on practice)
        5. Resources (tools/platforms to use)
        6. Estimated Timeline

        Format as JSON:
        {{
            "roadmap": {{
                "prerequisites": [
                    {{
                        "topic": "topic name",
                        "description": "what to learn",
                        "estimated_time": "time needed",
                        "resources": "suggested learning resources"
                    }}
                ],
                "core_concepts": [
                    {{
                        "topic": "concept name",
                        "description": "what to learn",
                        "estimated_time": "time needed",
                        "importance": "why this matters"
                    }}
                ],
                "advanced_topics": [
                    {{
                        "topic": "advanced topic",
                        "description": "what to learn",
                        "prerequisites": "required core concepts"
                    }}
                ],
                "projects": [
                    {{
                        "name": "project name",
                        "description": "project details",
                        "skills_practiced": "what you'll learn",
                        "difficulty": "beginner/intermediate/advanced"
                    }}
                ],
                "resources": [
                    {{
                        "type": "tool/platform type",
                        "suggestions": "specific resources",
                        "purpose": "how to use it"
                    }}
                ],
                "timeline": {{
                    "total_duration": "estimated total time",
                    "milestones": [
                        {{
                            "phase": "phase name",
                            "duration": "time needed",
                            "goals": "what to achieve"
                        }}
                    ]
                }}
            }}
        }}
        """

        roadmap_response = model.generate_content(roadmap_prompt)
        
        # Parse response
        response_text = roadmap_response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "", 1)
        if response_text.startswith("```"):
            response_text = response_text.replace("```", "", 1)
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        return json.loads(response_text.strip())["roadmap"]

    except Exception as e:
        st.error(f"Error generating roadmap: {e}")
        return None

def get_learning_resources(text_content):
    """Generate relevant learning resources with direct links"""
    try:
        # First determine the main topic category
        topic_prompt = f"""
        Analyze this content and identify the MAIN topic category.
        Choose ONLY from: 
        - Programming (Python, Java, JavaScript, HTML, CSS)
        - Networks (Computer Networks, Cybersecurity, Network Security)
        - Data Science (Machine Learning, Statistics, Data Analysis)
        - IT Infrastructure (Cloud Computing, DevOps, System Administration)
        - Business (Management, Marketing, Finance)
        - Science (Physics, Chemistry, Biology)
        - Mathematics (Algebra, Calculus, Statistics)
        - Language (English, Spanish, French)
        
        Respond with ONLY the category and specific topic, like: "Networks: Computer Networks" or "Programming: Python"
        
        Text: {text_content[:1000]}
        """
        
        model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp",
                                    generation_config={
                                        'temperature': 0.1
                                    })
        
        topic_response = model.generate_content(topic_prompt)
        category, topic = topic_response.text.strip().lower().split(": ")
        
        # Define resource templates based on category and topic
        resource_templates = {
            "programming": {
                "python": [
                    {
                        "platform": "W3Schools",
                        "url": "https://www.w3schools.com/python/",
                        "title": "Python Tutorial",
                        "description": "Learn Python with hands-on examples and exercises",
                        "difficulty": "beginner",
                        "format": "Interactive"
                    },
                    {
                        "platform": "GeeksforGeeks",
                        "url": "https://www.geeksforgeeks.org/python-programming-language/",
                        "title": "Python Programming Language",
                        "description": "Comprehensive Python programming tutorials and examples",
                        "difficulty": "intermediate",
                        "format": "Text"
                    },
                    {
                        "platform": "JavaTpoint",
                        "url": "https://www.javatpoint.com/python-tutorial",
                        "title": "Python Tutorial",
                        "description": "Complete Python tutorial for beginners and professionals",
                        "difficulty": "beginner",
                        "format": "Text"
                    }
                ],
                "java": [
                    {
                        "platform": "W3Schools",
                        "url": "https://www.w3schools.com/java/",
                        "title": "Java Tutorial",
                        "description": "Learn Java programming with examples",
                        "difficulty": "beginner",
                        "format": "Interactive"
                    },
                    {
                        "platform": "GeeksforGeeks",
                        "url": "https://www.geeksforgeeks.org/java/",
                        "title": "Java Programming",
                        "description": "Java tutorials and programming examples",
                        "difficulty": "intermediate",
                        "format": "Text"
                    },
                    {
                        "platform": "JavaTpoint",
                        "url": "https://www.javatpoint.com/java-tutorial",
                        "title": "Java Tutorial",
                        "description": "Learn Java programming step by step",
                        "difficulty": "beginner",
                        "format": "Text"
                    }
                ],
                "javascript": [
                    {
                        "platform": "W3Schools",
                        "url": "https://www.w3schools.com/js/",
                        "title": "JavaScript Tutorial",
                        "description": "Learn JavaScript with interactive examples",
                        "difficulty": "beginner",
                        "format": "Interactive"
                    },
                    {
                        "platform": "GeeksforGeeks",
                        "url": "https://www.geeksforgeeks.org/javascript/",
                        "title": "JavaScript Programming",
                        "description": "JavaScript tutorials and coding examples",
                        "difficulty": "intermediate",
                        "format": "Text"
                    },
                    {
                        "platform": "JavaTpoint",
                        "url": "https://www.javatpoint.com/javascript-tutorial",
                        "title": "JavaScript Tutorial",
                        "description": "Complete JavaScript learning guide",
                        "difficulty": "beginner",
                        "format": "Text"
                    }
                ],
                "html": [
                    {
                        "platform": "W3Schools",
                        "url": "https://www.w3schools.com/html/",
                        "title": "HTML Tutorial",
                        "description": "Learn HTML with interactive examples",
                        "difficulty": "beginner",
                        "format": "Interactive"
                    }
                ],
                "css": [
                    {
                        "platform": "W3Schools",
                        "url": "https://www.w3schools.com/css/",
                        "title": "CSS Tutorial",
                        "description": "Learn CSS with interactive examples",
                        "difficulty": "beginner",
                        "format": "Interactive"
                    }
                ]
            },
            "data science": {
                "machine learning": [
                    {
                        "platform": "Coursera",
                        "url": "https://www.coursera.org/learn/machine-learning",
                        "title": "Machine Learning Specialization",
                        "description": "Learn fundamental AI concepts and develop practical machine learning skills",
                        "difficulty": "intermediate",
                        "format": "Course"
                    },
                    {
                        "platform": "Khan Academy",
                        "url": "https://www.khanacademy.org/math/statistics-probability",
                        "title": "Statistics and Probability",
                        "description": "Essential statistics for machine learning",
                        "difficulty": "beginner",
                        "format": "Interactive"
                    }
                ]
            },
            "business": {
                "management": [
                    {
                        "platform": "Harvard Business School Online",
                        "url": "https://online.hbs.edu/courses/",
                        "title": "Business Management Courses",
                        "description": "Learn management principles from world-class faculty",
                        "difficulty": "intermediate",
                        "format": "Course"
                    },
                    {
                        "platform": "MIT OpenCourseWare",
                        "url": "https://ocw.mit.edu/courses/sloan-school-of-management/",
                        "title": "Management Courses",
                        "description": "Free management courses from MIT",
                        "difficulty": "advanced",
                        "format": "Course"
                    }
                ],
                "marketing": [
                    {
                        "platform": "Google Digital Garage",
                        "url": "https://learndigital.withgoogle.com/digitalgarage/course/digital-marketing",
                        "title": "Fundamentals of Digital Marketing",
                        "description": "Free digital marketing certification course",
                        "difficulty": "beginner",
                        "format": "Interactive"
                    }
                ]
            },
            "science": {
                "physics": [
                    {
                        "platform": "Khan Academy",
                        "url": "https://www.khanacademy.org/science/physics",
                        "title": "Physics",
                        "description": "Comprehensive physics courses from mechanics to quantum",
                        "difficulty": "beginner",
                        "format": "Interactive"
                    },
                    {
                        "platform": "MIT OpenCourseWare",
                        "url": "https://ocw.mit.edu/courses/physics/",
                        "title": "MIT Physics Courses",
                        "description": "University-level physics courses",
                        "difficulty": "advanced",
                        "format": "Course"
                    }
                ],
                "chemistry": [
                    {
                        "platform": "Khan Academy",
                        "url": "https://www.khanacademy.org/science/chemistry",
                        "title": "Chemistry",
                        "description": "From atoms to chemical reactions",
                        "difficulty": "beginner",
                        "format": "Interactive"
                    }
                ]
            },
            "mathematics": {
                "calculus": [
                    {
                        "platform": "Khan Academy",
                        "url": "https://www.khanacademy.org/math/calculus-1",
                        "title": "Calculus",
                        "description": "Comprehensive calculus courses",
                        "difficulty": "intermediate",
                        "format": "Interactive"
                    },
                    {
                        "platform": "MIT OpenCourseWare",
                        "url": "https://ocw.mit.edu/courses/mathematics/",
                        "title": "MIT Mathematics",
                        "description": "Advanced mathematics courses",
                        "difficulty": "advanced",
                        "format": "Course"
                    }
                ]
            },
            "language": {
                "english": [
                    {
                        "platform": "Duolingo",
                        "url": "https://www.duolingo.com/course/en/",
                        "title": "English Course",
                        "description": "Learn English through interactive lessons",
                        "difficulty": "beginner",
                        "format": "Interactive"
                    },
                    {
                        "platform": "BBC Learning English",
                        "url": "https://www.bbc.co.uk/learningenglish/",
                        "title": "BBC English Courses",
                        "description": "Free English learning resources",
                        "difficulty": "intermediate",
                        "format": "Mixed"
                    }
                ],
                "spanish": [
                    {
                        "platform": "SpanishDict",
                        "url": "https://www.spanishdict.com/learn",
                        "title": "Spanish Courses",
                        "description": "Learn Spanish from basics to advanced",
                        "difficulty": "beginner",
                        "format": "Interactive"
                    }
                ]
            },
            "networks": {
                "computer networks": [
                    {
                        "platform": "GeeksforGeeks",
                        "url": "https://www.geeksforgeeks.org/computer-network-tutorials/",
                        "title": "Computer Networks Tutorial",
                        "description": "Complete guide to computer networking concepts",
                        "difficulty": "intermediate",
                        "format": "Text"
                    },
                    {
                        "platform": "JavaTpoint",
                        "url": "https://www.javatpoint.com/computer-network-tutorial",
                        "title": "Computer Network Tutorial",
                        "description": "Learn computer networks from basics to advanced",
                        "difficulty": "beginner",
                        "format": "Text"
                    },
                    {
                        "platform": "TutorialsPoint",
                        "url": "https://www.tutorialspoint.com/data_communication_computer_network/",
                        "title": "Data Communication & Computer Network",
                        "description": "Comprehensive networking concepts and protocols",
                        "difficulty": "intermediate",
                        "format": "Text"
                    },
                    {
                        "platform": "Coursera",
                        "url": "https://www.coursera.org/specializations/computer-communications",
                        "title": "Computer Communications Specialization",
                        "description": "Learn about network protocols, architecture, and applications",
                        "difficulty": "intermediate",
                        "format": "Course"
                    }
                ],
                "cybersecurity": [
                    {
                        "platform": "Coursera",
                        "url": "https://www.coursera.org/specializations/cyber-security",
                        "title": "Cybersecurity Specialization",
                        "description": "Learn fundamental cybersecurity concepts",
                        "difficulty": "intermediate",
                        "format": "Course"
                    },
                    {
                        "platform": "TryHackMe",
                        "url": "https://tryhackme.com/paths",
                        "title": "Cybersecurity Learning Paths",
                        "description": "Hands-on cybersecurity training",
                        "difficulty": "beginner",
                        "format": "Interactive"
                    }
                ],
                "network security": [
                    {
                        "platform": "Coursera",
                        "url": "https://www.coursera.org/learn/network-security",
                        "title": "Network Security & Database Vulnerabilities",
                        "description": "Learn about network security fundamentals",
                        "difficulty": "intermediate",
                        "format": "Course"
                    },
                    {
                        "platform": "TutorialsPoint",
                        "url": "https://www.tutorialspoint.com/network_security/",
                        "title": "Network Security Tutorial",
                        "description": "Comprehensive guide to network security",
                        "difficulty": "intermediate",
                        "format": "Text"
                    }
                ]
            },
            "it infrastructure": {
                "cloud computing": [
                    {
                        "platform": "AWS Training",
                        "url": "https://aws.amazon.com/training/",
                        "title": "AWS Training and Certification",
                        "description": "Official Amazon Web Services training",
                        "difficulty": "beginner",
                        "format": "Mixed"
                    },
                    {
                        "platform": "Microsoft Learn",
                        "url": "https://learn.microsoft.com/en-us/training/azure/",
                        "title": "Microsoft Azure Training",
                        "description": "Official Azure cloud training",
                        "difficulty": "beginner",
                        "format": "Mixed"
                    }
                ],
                "devops": [
                    {
                        "platform": "Linux Foundation",
                        "url": "https://training.linuxfoundation.org/training/devops-and-sre-fundamentals/",
                        "title": "DevOps Fundamentals",
                        "description": "Learn DevOps principles and practices",
                        "difficulty": "intermediate",
                        "format": "Course"
                    }
                ]
            }
        }
        
        # Get resources for the identified category and topic
        if category in resource_templates and topic in resource_templates[category]:
            return resource_templates[category][topic]
        else:
            st.warning(f"Category: {category}, Topic: {topic}")  # Debug info
            return []

    except Exception as e:
        st.error(f"Error finding resources: {str(e)}")
        return []

def get_available_certificates(text_content):
    """Get relevant certifications with guaranteed working URLs"""
    try:
        # First determine the main topic
        topic_prompt = f"""
        Analyze this content and identify the MAIN technical topic.
        Keep it simple and specific (e.g., Python, Java, Network Security, Cloud Computing, etc.)
        
        Content: {text_content[:1500]}
        
        Respond with ONLY the topic name, nothing else.
        """
        
        model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp",
                                    generation_config={
                                        'temperature': 0.1
                                    })
        
        topic = model.generate_content(topic_prompt).text.strip().lower()
        
        # Define reliable certification recommendations
        cert_prompt = f"""
        Recommend 3 professional certifications for learning {topic}.
        
        Use ONLY these platforms and their exact URLs:
        1. Coursera: https://www.coursera.org
        2. edX: https://www.edx.org
        3. Udemy: https://www.udemy.com
        4. Microsoft Learn: https://learn.microsoft.com
        5. AWS Training: https://aws.amazon.com/training
        6. Google: https://grow.google/certificates
        7. CompTIA: https://www.comptia.org
        8. Cisco: https://www.cisco.com/c/en/us/training-events/training.html

        For each certification provide:
        NAME: (name of certification)
        PLATFORM: (platform from the list above)
        LEVEL: (beginner/intermediate/advanced)
        COST: (approximate cost)
        DURATION: (estimated time)
        URL: (exact URL from the list above)
        DESCRIPTION: (1-2 sentences about what you'll learn)

        Format as a simple list with --- between each certification.
        """
        
        response = model.generate_content(cert_prompt)
        cert_list = []
        
        # Parse the recommendations
        for cert_block in response.text.split('---'):
            if not cert_block.strip():
                continue
                
            cert_data = {}
            for line in cert_block.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    cert_data[key.strip().upper()] = value.strip()
            
            if cert_data:
                cert_list.append({
                    "name": cert_data.get('NAME', 'N/A'),
                    "platform": cert_data.get('PLATFORM', 'N/A'),
                    "level": cert_data.get('LEVEL', 'N/A'),
                    "cost": cert_data.get('COST', 'N/A'),
                    "duration": cert_data.get('DURATION', 'N/A'),
                    "url": cert_data.get('URL', 'https://www.coursera.org'),  # Default to Coursera if URL missing
                    "description": cert_data.get('DESCRIPTION', 'N/A')
                })
        
        return cert_list

    except Exception as e:
        st.error(f"Error finding certifications: {str(e)}")
        return []

def generate_coding_exercises(text_content):
    """Generate interactive coding exercises with real-time feedback"""
    try:
        prompt = f"""
        Create 3 practical coding exercises based on this content.
        Format your response as valid JSON with this exact structure:
        {{
            "exercises": [
                {{
                    "title": "Exercise title",
                    "description": "Detailed problem description",
                    "difficulty": "beginner/intermediate/advanced",
                    "input_output": {{
                        "sample_input": "Example input",
                        "sample_output": "Expected output"
                    }},
                    "starter_code": "Python code template to start with",
                    "test_cases": [
                        {{
                            "input": "test input",
                            "expected_output": "expected output"
                        }}
                    ],
                    "hints": [
                        "Hint 1",
                        "Hint 2"
                    ]
                }}
            ]
        }}
        
        Text content: {text_content}
        """
        
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config={
                'temperature': 0.7
            }
        )
        
        response = model.generate_content(prompt)
        
        # Clean and parse the response
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "", 1)
        if response_text.startswith("```"):
            response_text = response_text.replace("```", "", 1)
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        exercises_data = json.loads(response_text.strip())
        return exercises_data.get("exercises", [])
        
    except Exception as e:
        st.error(f"Error generating exercises: {str(e)}")
        return []

def execute_code(code, test_input):
    """Execute user code safely and return output"""
    try:
        # Create a string IO object to capture stdout
        output_buffer = StringIO()
        sys.stdout = output_buffer
        
        # Execute the code with test input
        exec(code)
        
        # Restore stdout
        sys.stdout = sys.__stdout__
        
        # Get the captured output
        output = output_buffer.getvalue().strip()
        return output
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        sys.stdout = sys.__stdout__

def track_progress():
    """Enhanced analytics with learning metrics"""
    try:
        if "study_metrics" not in st.session_state:
            st.session_state.study_metrics = {
                "time_spent": 0,  # in minutes
                "topics_studied": set(),
                "quiz_scores": [],
                "flashcards_reviewed": 0,
                "exercises_completed": 0,
                "concept_mastery": {},
                "last_session": None,
                "study_sessions": []
            }
        
        # Update study time
        if "session_start" not in st.session_state:
            st.session_state.session_start = datetime.now()
        
        # Calculate time spent
        current_session_time = (datetime.now() - st.session_state.session_start).total_seconds() / 60
        total_time = st.session_state.study_metrics["time_spent"] + current_session_time
        
        return {
            "total_time": round(total_time, 2),
            "topics": list(st.session_state.study_metrics["topics_studied"]),
            "quiz_performance": {
                "average": sum(st.session_state.study_metrics["quiz_scores"]) / len(st.session_state.study_metrics["quiz_scores"]) if st.session_state.study_metrics["quiz_scores"] else 0,
                "total_quizzes": len(st.session_state.study_metrics["quiz_scores"])
            },
            "flashcards": st.session_state.study_metrics["flashcards_reviewed"],
            "exercises": st.session_state.study_metrics["exercises_completed"],
            "mastery": st.session_state.study_metrics["concept_mastery"]
        }
    except Exception as e:
        st.error(f"Error tracking progress: {str(e)}")
        return None

def update_study_metrics(metric_type, value):
    """Update various study metrics"""
    try:
        if metric_type == "quiz_score":
            st.session_state.study_metrics["quiz_scores"].append(value)
        elif metric_type == "topic":
            st.session_state.study_metrics["topics_studied"].add(value)
        elif metric_type == "flashcard":
            st.session_state.study_metrics["flashcards_reviewed"] += value
        elif metric_type == "exercise":
            st.session_state.study_metrics["exercises_completed"] += value
        elif metric_type == "mastery":
            topic, level = value
            st.session_state.study_metrics["concept_mastery"][topic] = level
    except Exception as e:
        st.error(f"Error updating metrics: {str(e)}")

def extract_main_topic(text_content):
    """Extract the main topic from the content"""
    try:
        prompt = f"""
        Analyze this content and identify the MAIN topic category.
        Choose ONLY from: 
        - Programming
        - Networks
        - Data Science
        - IT Infrastructure
        - Business
        - Science
        - Mathematics
        - Language
        
        Respond with ONLY the category name, nothing else.
        
        Content: {text_content[:1500]}
        """
        
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config={
                'temperature': 0.1
            }
        )
        
        topic = model.generate_content(prompt).text.strip()
        return topic
    except Exception as e:
        st.error(f"Error extracting topic: {str(e)}")
        return "General"

def create_study_group(group_name, description, topic, max_members=10):
    """Create a new study group"""
    if "study_groups" not in st.session_state:
        st.session_state.study_groups = []
    
    new_group = {
        "id": len(st.session_state.study_groups),
        "name": group_name,
        "description": description,
        "topic": topic,
        "max_members": max_members,
        "members": [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "posts": []
    }
    
    st.session_state.study_groups.append(new_group)
    return new_group

def join_study_group(group_id):
    """Join an existing study group"""
    if "study_groups" not in st.session_state:
        st.session_state.study_groups = []
    
    for group in st.session_state.study_groups:
        if group["id"] == group_id:
            if len(group["members"]) < group["max_members"]:
                group["members"].append({
                    "username": st.session_state.get("username", "Anonymous"),
                    "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                return True
    return False

def create_forum_post(group_id, title, content):
    """Create a new forum post in a study group"""
    if "study_groups" not in st.session_state:
        st.session_state.study_groups = []
    
    for group in st.session_state.study_groups:
        if group["id"] == group_id:
            new_post = {
                "id": len(group["posts"]),
                "title": title,
                "content": content,
                "author": st.session_state.get("username", "Anonymous"),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "comments": []
            }
            group["posts"].append(new_post)
            return new_post
    return None

def add_comment(group_id, post_id, content):
    """Add a comment to a forum post"""
    if "study_groups" not in st.session_state:
        st.session_state.study_groups = []
    
    for group in st.session_state.study_groups:
        if group["id"] == group_id:
            for post in group["posts"]:
                if post["id"] == post_id:
                    new_comment = {
                        "id": len(post["comments"]),
                        "content": content,
                        "author": st.session_state.get("username", "Anonymous"),
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    post["comments"].append(new_comment)
                    return new_comment
    return None

def share_resource(group_id, title, description, url, resource_type):
    """Share a learning resource in a study group"""
    if "study_groups" not in st.session_state:
        st.session_state.study_groups = []
    
    for group in st.session_state.study_groups:
        if group["id"] == group_id:
            new_resource = {
                "id": len(group.get("resources", [])),
                "title": title,
                "description": description,
                "url": url,
                "type": resource_type,
                "shared_by": st.session_state.get("username", "Anonymous"),
                "shared_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            if "resources" not in group:
                group["resources"] = []
            group["resources"].append(new_resource)
            return new_resource
    return None

def share_progress(group_id, topic, progress_data):
    """Share learning progress in a study group"""
    if "study_groups" not in st.session_state:
        st.session_state.study_groups = []
    
    for group in st.session_state.study_groups:
        if group["id"] == group_id:
            new_progress = {
                "id": len(group.get("progress_shares", [])),
                "topic": topic,
                "data": progress_data,
                "shared_by": st.session_state.get("username", "Anonymous"),
                "shared_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            if "progress_shares" not in group:
                group["progress_shares"] = []
            group["progress_shares"].append(new_progress)
            return new_progress
    return None

def hash_password(password):
    """Hash a password using SHA-256"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, email):
    """Create a new user account"""
    if "users" not in st.session_state:
        st.session_state.users = {}
    
    if username in st.session_state.users:
        return False, "Username already exists"
    
    st.session_state.users[username] = {
        "password": hash_password(password),
        "email": email,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "profile": {
            "bio": "",
            "interests": [],
            "learning_goals": [],
            "achievements": []
        }
    }
    return True, "Account created successfully"

def verify_user(username, password):
    """Verify user credentials"""
    if "users" not in st.session_state:
        st.session_state.users = {}
    
    if username not in st.session_state.users:
        return False, "Username not found"
    
    if st.session_state.users[username]["password"] != hash_password(password):
        return False, "Incorrect password"
    
    return True, "Login successful"

def update_user_profile(username, bio=None, interests=None, learning_goals=None):
    """Update user profile information"""
    if "users" not in st.session_state or username not in st.session_state.users:
        return False, "User not found"
    
    user = st.session_state.users[username]
    if bio:
        user["profile"]["bio"] = bio
    if interests:
        user["profile"]["interests"] = interests
    if learning_goals:
        user["profile"]["learning_goals"] = learning_goals
    
    return True, "Profile updated successfully"

def main():
    """Main function to run the Streamlit app"""
    
    # Initialize session state for authentication
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_user" not in st.session_state:
        st.session_state.current_user = None
    
    # Main app title
    st.title("🎯Personalized Education Through AI Learning Assistant")
    
    # Add login button and form
    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        if not st.session_state.authenticated:
            if st.button("Login", key="main_login_button"):
                st.session_state.show_login = True
    with col3:
        if not st.session_state.authenticated:
            if st.button("Register", key="main_register_button"):
                st.session_state.show_register = True
        else:
            if st.button("Logout", key="main_logout_button"):
                st.session_state.authenticated = False
                st.session_state.current_user = None
                st.success("Logged out successfully!")
    
    # Login form
    if st.session_state.get("show_login", False):
        with st.form("login_form"):
            st.subheader("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                success, message = database.verify_user(username, password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.current_user = username
                    st.session_state.show_login = False
                    st.success("Login successful!")
                else:
                    st.error(message)
    
    # Register form
    if st.session_state.get("show_register", False):
        with st.form("register_form"):
            st.subheader("Register")
            new_username = st.text_input("Choose Username")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            email = st.text_input("Email Address")
            submit = st.form_submit_button("Register")
            
            if submit:
                if new_password != confirm_password:
                    st.error("Passwords do not match!")
                else:
                    success, message = database.create_user(new_username, new_password, email)
                    if success:
                        st.success(message)
                        st.session_state.show_register = False
                    else:
                        st.error(message)
    
    # File uploader and text input section (available to all)
    uploaded_file = st.file_uploader(
        "Upload a file (.txt, .pdf, .docx, .png, .jpeg, .jpg):",
        type=["txt", "pdf", "docx", "png", "jpeg", "jpg"]
    )
    text_content = ""
    if uploaded_file:
        text_content = extract_text_from_file(uploaded_file)

    st.write("Or paste text content below:")
    manual_text = st.text_area("Paste the text content here (this will override uploaded file content):")

    if manual_text.strip():
        text_content = manual_text

    # Add tabs for different features
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13, tab14 = st.tabs([
        "Generate Quiz", 
        "Generate Summary", 
        "Flashcards", 
        "Analytics", 
        "Video Resources",
        "Books & PDFs",
        "Latest News",
        "Learning Roadmap",
        "Learning Resources",
        "Relevant Certifications",
        "Code Practice",
        "Progress Dashboard",
        "Social Learning",
        "Gamification"
    ])

    # Basic features (available to all)
    with tab1:
        if not text_content:
            st.warning("Please upload a file or paste text content to generate quiz questions.")
        else:
            quiz_type = st.selectbox("Select quiz type:", ["Multiple Choice", "True/False"])
            quiz_level = st.selectbox("Select quiz level:", ["Easy", "Medium", "Hard"])
            
            # Initialize session state variables
            if "questions" not in st.session_state:
                st.session_state.questions = []
            if "selected_options" not in st.session_state:
                st.session_state.selected_options = []
            if "correct_answers" not in st.session_state:
                st.session_state.correct_answers = []
            if "quiz_generated" not in st.session_state:
                st.session_state.quiz_generated = False
            if "marks" not in st.session_state:
                st.session_state.marks = 0
            if "submitted" not in st.session_state:
                st.session_state.submitted = False
            
            if st.button("Generate Quiz"):
                with st.spinner("Generating quiz questions..."):
                    if quiz_type == "Multiple Choice":
                        questions = fetch_questions(text_content=text_content, quiz_level=quiz_level.lower())
                        if questions:
                            st.session_state.selected_options = [None] * len(questions)
                            st.session_state.correct_answers = [
                                q["options"].get(q["correct"], "Unknown") for q in questions
                            ]
                    else:
                        questions = fetch_true_false_questions(text_content=text_content, quiz_level=quiz_level.lower())
                        if questions:
                            st.session_state.selected_options = [None] * len(questions)
                            st.session_state.correct_answers = [
                                q["correct_answer"] for q in questions
                            ]
                    
                    if questions:
                        st.session_state.questions = questions
                        st.session_state.quiz_generated = True
                        st.session_state.submitted = False
                        st.session_state.marks = 0
                        
                        # Translate questions if language is not English
                        if selected_language != 'en':
                            st.session_state.questions = translate_content(questions, selected_language)
                    else:
                        st.error("Could not generate quiz questions. Please try again with different text or quiz level.")
                        st.session_state.quiz_generated = False

            if st.session_state.quiz_generated and st.session_state.questions:
                st.write("---")
                with st.form("quiz_form"):
                    for i, question in enumerate(st.session_state.questions):
                        if quiz_type == "Multiple Choice":
                            mcq_text = question["mcq"]
                            options = question["options"]
                            option_list = list(options.values())

                            st.subheader(f"Question {i+1}: {mcq_text}")
                            selected_option_index = -1
                            if (
                                st.session_state.selected_options[i] in option_list
                                and st.session_state.selected_options[i] is not None
                            ):
                                selected_option_index = option_list.index(st.session_state.selected_options[i])

                            selected_option = st.radio(
                                "", option_list, index=selected_option_index if selected_option_index != -1 else None, key=f"q{i}"
                            )
                        else:  # True/False
                            tf_text = question["question"]
                            st.subheader(f"Question {i+1}: {tf_text}")
                            selected_option = st.radio(
                                "", [True, False], index=None, key=f"q{i}"
                            )

                        st.session_state.selected_options[i] = selected_option

                    submit_button = st.form_submit_button("Submit Quiz")

                    if submit_button:
                        st.session_state.submitted = True
                        st.session_state.marks = 0
                        
                        for i, (selected, correct) in enumerate(zip(st.session_state.selected_options, st.session_state.correct_answers)):
                            if selected == correct:
                                st.session_state.marks += 1
                        
                        # Save quiz results
                        save_quiz_results()
                        
                        # Show results
                        st.success(f"Quiz completed! Your score: {st.session_state.marks}/{len(st.session_state.questions)}")
                        
                        # Update study metrics
                        if st.session_state.authenticated:
                            update_study_metrics("quiz_score", st.session_state.marks / len(st.session_state.questions))
                            update_study_metrics("topic", extract_main_topic(text_content))

    with tab2:
        if not text_content:
            st.warning("Please upload a file or paste text content to generate a summary.")
        else:
            if st.button("Generate Summary"):
                with st.spinner("Generating summary..."):
                    summary = generate_summary(text_content)
                    if summary:
                        st.subheader("Text Summary")
                        st.markdown(f'<div class="card">{summary}</div>', unsafe_allow_html=True)

    with tab3:
        if not text_content:
            st.warning("Please upload a file or paste text content to generate flashcards.")
        else:
            if st.button("Generate Flashcards"):
                with st.spinner("Generating flashcards..."):
                    flashcards = generate_flashcards(text_content)
                    if flashcards:
                        st.session_state.flashcards = flashcards
                        st.session_state.flipped_cards = set()
                    else:
                        st.error("Failed to generate flashcards. Please try again.")

    # Advanced features (require login)
    with tab4:
        if not st.session_state.authenticated:
            st.warning("Please login to access analytics features.")
            if st.button("Login", key="analytics_login_button"):
                st.session_state.show_login = True
        else:
            show_analytics()

    with tab5:
        if not text_content:
            st.warning("Please upload a file or paste text content to find related videos.")
        else:
            if st.button("Find Related Videos"):
                with st.spinner("Searching for relevant educational videos..."):
                    videos = get_youtube_recommendations(text_content)
                    if videos:
                        st.subheader("Recommended Educational Videos")
                        for video in videos:
                            st.markdown(f"""
                            <div style="border:1px solid #ddd; padding:10px; border-radius:5px; margin:5px;">
                                <img src="{video['thumbnail']}" style="width:100%;">
                                <h4>{video['title']}</h4>
                                <p>{video['description'][:100]}...</p>
                                <a href="{video['url']}" target="_blank">Watch Video</a>
                            </div>
                            """, unsafe_allow_html=True)

    with tab6:
        if not text_content:
            st.warning("Please upload a file or paste text content to find related books.")
        else:
            if st.button("Find Related Books"):
                with st.spinner("Finding relevant books..."):
                    books = get_book_suggestions(text_content)
                    if books:
                        st.subheader("📚 Recommended Books")
                        for book in books:
                            st.markdown(f"""
                            <div style="border:1px solid #ddd; padding:20px; border-radius:10px; margin:10px 0; background-color: white;">
                                <h3 style="color: #1e88e5; margin:0;">{book['title']}</h3>
                                <p style="color: #666; font-style:italic; margin:5px 0;">
                                    by {book['author']} | {book['publisher']} ({book['year']})
                                </p>
                                <p style="color: #333; margin:10px 0;">{book['description']}</p>
                                <div style="margin:10px 0;">
                                    <span style="background-color: #e3f2fd; padding:5px 10px; border-radius:15px; margin-right:10px;">
                                        {book['level']}
                                    </span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

        with tab7:
            if st.button("Find Related News"):
                if text_content:
                    with st.spinner("Finding recent news..."):
                        news_items = get_tech_news(text_content)
                        
                        if news_items:
                            st.subheader("📰 Latest Technology News")
                            
                            for news in news_items:
                                with st.container():
                                    st.markdown(f"""
                                    <div style="border:1px solid #ddd; padding:20px; border-radius:10px; margin:10px 0; background-color: white;">
                                        <a href="{news['url']}" target="_blank" style="text-decoration: none;">
                                            <h3 style="color: #1e88e5; margin:0;">{news['title']} 🔗</h3>
                                        </a>
                                        <div style="display: flex; gap: 10px; margin: 10px 0;">
                                            <span style="color: #666;">📰 {news['source']}</span>
                                            <span style="color: #666;">📅 {news['date']}</span>
                                            <span style="background-color: #e3f2fd; padding: 0 10px; border-radius: 15px;">
                                                {news['category']}
                                            </span>
                                        </div>
                                        <p style="color: #333; margin: 10px 0;">{news['summary']}</p>
                                        <a href="{news['url']}" target="_blank" style="
                                            background-color: #1e88e5;
                                            color: white;
                                            padding: 8px 15px;
                                            border-radius: 5px;
                                            text-decoration: none;
                                            display: inline-block;
                                            margin-top: 10px;
                                            ">Read Full Article</a>
                                    </div>
                                    """, unsafe_allow_html=True)
                else:
                    st.warning("Please upload a file or paste text content to find related news.")

        with tab8:
            if st.button("Generate Learning Roadmap"):
                if text_content:
                    with st.spinner("Creating your personalized learning roadmap..."):
                        roadmap = generate_roadmap(text_content)
                        
                        if roadmap:
                            st.subheader("🗺️ Your Learning Roadmap")
                            
                            # Prerequisites
                            st.markdown("### 📚 Prerequisites")
                            for prereq in roadmap["prerequisites"]:
                                with st.expander(f"🔍 {prereq['topic']}", expanded=True):
                                    st.markdown(f"""
                                    - **Description:** {prereq['description']}
                                    - **Estimated Time:** {prereq['estimated_time']}
                                    - **Resources:** {prereq['resources']}
                                    """)
                            
                            # Core Concepts
                            st.markdown("### 🎯 Core Concepts")
                            for concept in roadmap["core_concepts"]:
                                with st.expander(f"📘 {concept['topic']}", expanded=True):
                                    st.markdown(f"""
                                    - **Description:** {concept['description']}
                                    - **Estimated Time:** {concept['estimated_time']}
                                    - **Why Important:** {concept['importance']}
                                    """)
                            
                            # Advanced Topics
                            st.markdown("### 🚀 Advanced Topics")
                            for topic in roadmap["advanced_topics"]:
                                with st.expander(f"📚 {topic['topic']}", expanded=True):
                                    st.markdown(f"""
                                    - **Description:** {topic['description']}
                                    - **Prerequisites:** {topic['prerequisites']}
                                    """)
                            
                            # Projects
                            st.markdown("### 🛠️ Hands-on Projects")
                            for project in roadmap["projects"]:
                                with st.expander(f"🏗️ {project['name']}", expanded=True):
                                    st.markdown(f"""
                                    - **Description:** {project['description']}
                                    - **Skills Practiced:** {project['skills_practiced']}
                                    - **Difficulty:** {project['difficulty']}
                                    """)
                            
                            # Resources
                            st.markdown("### 🔧 Recommended Resources")
                            for resource in roadmap["resources"]:
                                with st.expander(f"🔨 {resource['type']}", expanded=True):
                                    st.markdown(f"""
                                    - **Suggestions:** {resource['suggestions']}
                                    - **Purpose:** {resource['purpose']}
                                    """)
                            
                            # Timeline
                            st.markdown("### ⏱️ Estimated Timeline")
                            st.info(f"Total Duration: {roadmap['timeline']['total_duration']}")
                            for milestone in roadmap['timeline']['milestones']:
                                with st.expander(f"📅 {milestone['phase']}", expanded=True):
                                    st.markdown(f"""
                                    - **Duration:** {milestone['duration']}
                                    - **Goals:** {milestone['goals']}
                                    """)
                else:
                    st.warning("Please upload a file or paste text content to generate a roadmap.")

        with tab9:
            if st.button("Find Learning Resources"):
                if text_content:
                    with st.spinner("Finding relevant learning resources..."):
                        resources = get_learning_resources(text_content)
                        
                        if resources:
                            st.subheader("🎓 Learning Resources")
                            
                            for resource in resources:
                                with st.container():
                                    st.markdown(f"""
                                    <div style="border:1px solid #ddd; padding:20px; border-radius:10px; margin:10px 0; background-color: white;">
                                        <h3 style="color: #1e88e5; margin:0;">{resource['platform']}: {resource['title']}</h3>
                                        <div style="display: flex; gap: 10px; margin: 10px 0;">
                                            <span style="background-color: #e3f2fd; padding: 0 10px; border-radius: 15px;">
                                                {resource['difficulty']}
                                            </span>
                                            <span style="background-color: #e8f5e9; padding: 0 10px; border-radius: 15px;">
                                                {resource['format']}
                                            </span>
                                        </div>
                                        <p style="color: #333; margin: 10px 0;">{resource['description']}</p>
                                        <a href="{resource['url']}" target="_blank" style="
                                            background-color: #1e88e5;
                                            color: white;
                                            padding: 8px 15px;
                                            border-radius: 5px;
                                            text-decoration: none;
                                            display: inline-block;
                                            margin-top: 10px;
                                            ">Start Learning</a>
                                    </div>
                                    """, unsafe_allow_html=True)
                        else:
                            st.warning("No relevant resources found. Please try with a specific programming language or technology.")
                else:
                    st.warning("Please upload a file or paste text content to find learning resources.")

        with tab10:
            if st.button("Find Relevant Certifications"):
                if text_content:
                    with st.spinner("Finding relevant certifications..."):
                        certificates = get_available_certificates(text_content)
                        
                        if certificates:
                            st.subheader("🎓 Recommended Certifications")
                            
                            for cert in certificates:
                                with st.container():
                                    st.markdown(f"""
                                    <div style="border:1px solid #ddd; padding:20px; border-radius:10px; margin:10px 0; background-color: white;">
                                        <h3 style="color: #1e88e5; margin:0;">{cert['name']}</h3>
                                        <div style="display: flex; gap: 10px; margin: 10px 0;">
                                            <span style="background-color: #e3f2fd; padding: 0 10px; border-radius: 15px;">
                                                {cert['platform']}
                                            </span>
                                            <span style="background-color: #e8f5e9; padding: 0 10px; border-radius: 15px;">
                                                {cert['level']}
                                            </span>
                                        </div>
                                        <p style="color: #333; margin: 5px 0;"><strong>Cost:</strong> {cert['cost']}</p>
                                        <p style="color: #333; margin: 5px 0;"><strong>Duration:</strong> {cert['duration']}</p>
                                        <p style="color: #333; margin: 10px 0;"><strong>What you'll learn:</strong> {cert['description']}</p>
                                        <a href="{cert['url']}" target="_blank" class="button" style="
                                            background-color: #1e88e5;
                                            color: white;
                                            padding: 8px 15px;
                                            border-radius: 5px;
                                            text-decoration: none;
                                            display: inline-block;
                                            margin-top: 10px;
                                            ">Visit Platform</a>
                                    </div>
                                    """, unsafe_allow_html=True)
                        else:
                            st.warning("Could not find relevant certifications. Please try with different content.")
                else:
                    st.warning("Please upload a file or paste text content to find relevant certifications.")

    with tab11:
        st.subheader("💻 Code Practice")
        st.markdown("""
        <style>
        .exercise-container {
            background-color: #ffffff;
            color: #333333;
            padding: 20px;
            border-radius: 10px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .code-editor {
            background-color: #f8f9fa;
            color: #333333;
            font-family: 'Courier New', monospace;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 10px;
        }
        .test-results {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
            border: 1px solid #dee2e6;
        }
        .hint-box {
            background-color: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
            border: 1px solid #bbdefb;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.subheader("🖥️ Interactive Code Practice")
        
        if "current_exercise" not in st.session_state:
            st.session_state.current_exercise = 0
        if "exercises" not in st.session_state:
            st.session_state.exercises = []
        if "show_hint" not in st.session_state:
            st.session_state.show_hint = False
        if "current_hint" not in st.session_state:
            st.session_state.current_hint = 0
        
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            if st.button("Generate New Exercises"):
                if text_content:
                    with st.spinner("Generating coding exercises..."):
                        st.session_state.exercises = generate_coding_exercises(text_content)
                        st.session_state.current_exercise = 0
                        st.session_state.show_hint = False
                        st.session_state.current_hint = 0
                else:
                    st.warning("Please upload a file or paste text content to generate exercises.")
        
        if st.session_state.exercises:
            exercise = st.session_state.exercises[st.session_state.current_exercise]
            
            # Exercise navigation
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                if st.button("⬅️ Previous") and st.session_state.current_exercise > 0:
                    st.session_state.current_exercise -= 1
                    st.session_state.show_hint = False
                    st.session_state.current_hint = 0
            with col3:
                if st.button("Next ➡️") and st.session_state.current_exercise < len(st.session_state.exercises) - 1:
                    st.session_state.current_exercise += 1
                    st.session_state.show_hint = False
                    st.session_state.current_hint = 0
            
            # Display exercise details with updated styling
            st.markdown(f"""
            <div class="exercise-container">
                <h3 style="color: #4CAF50;">{exercise['title']}</h3>
                <p><strong style="color: #64B5F6;">Difficulty:</strong> {exercise['difficulty']}</p>
                <p style="color: #ffffff;">{exercise['description']}</p>
                <h4 style="color: #FFB74D;">Sample Input/Output:</h4>
                <pre style="background-color: #2d2d2d; padding: 10px; border-radius: 5px;">
Input: {exercise['input_output']['sample_input']}
Output: {exercise['input_output']['sample_output']}</pre>
            </div>
            """, unsafe_allow_html=True)
            
            # Code editor with updated styling
            st.markdown('<div class="code-editor">', unsafe_allow_html=True)
            user_code = st.text_area(
                "Your Code:",
                value=exercise['starter_code'],
                height=200,
                key=f"code_editor_{st.session_state.current_exercise}"
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Test cases and execution with updated styling
            if st.button("Run Tests", type="primary"):
                st.markdown('<div class="test-results">', unsafe_allow_html=True)
                st.write("### Test Results")
                for i, test in enumerate(exercise['test_cases']):
                    with st.expander(f"Test Case {i + 1}"):
                        output = execute_code(user_code, test['input'])
                        if output.strip() == test['expected_output'].strip():
                            st.success("✅ Test passed!")
                        else:
                            st.error("❌ Test failed")
                            st.write(f"Expected: {test['expected_output']}")
                            st.write(f"Got: {output}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Hints system with updated styling
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("Show Hint"):
                    st.session_state.show_hint = True
                    if st.session_state.current_hint < len(exercise['hints']) - 1:
                        st.session_state.current_hint += 1
            
            if st.session_state.show_hint:
                st.markdown('<div class="hint-box">', unsafe_allow_html=True)
                with st.expander("💡 Hint", expanded=True):
                    st.write(exercise['hints'][st.session_state.current_hint])
                st.markdown('</div>', unsafe_allow_html=True)

    with tab12:
        st.markdown("""
        <style>
        .metric-card {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 10px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #1e88e5;
        }
        .metric-label {
            color: #333333;
            font-size: 16px;
        }
        .progress-chart {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.subheader("📊 Learning Progress Dashboard")
        
        # Get current progress metrics
        progress = track_progress()
        
        if progress:
            # Display key metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{} hrs</div>
                    <div class="metric-label">Total Study Time</div>
                </div>
                """.format(round(progress["total_time"]/60, 1)), unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{}</div>
                    <div class="metric-label">Topics Covered</div>
                </div>
                """.format(len(progress["topics"])), unsafe_allow_html=True)
            
            with col3:
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{}%</div>
                    <div class="metric-label">Average Quiz Score</div>
                </div>
                """.format(round(progress["quiz_performance"]["average"] * 100)), unsafe_allow_html=True)
            
            # Topic Progress
            st.subheader("Topic Progress")
            for topic, mastery in progress["mastery"].items():
                st.markdown(f"""
                <div class="progress-chart">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #ffffff;">{topic}</span>
                        <span style="color: #4CAF50;">{mastery}%</span>
                    </div>
                    <div style="background-color: #424242; height: 10px; border-radius: 5px; margin-top: 5px;">
                        <div style="width: {mastery}%; background-color: #4CAF50; height: 100%; border-radius: 5px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Activity Summary
            st.subheader("Activity Summary")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{}</div>
                    <div class="metric-label">Flashcards Reviewed</div>
                </div>
                """.format(progress["flashcards"]), unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                <div class="metric-card">
                    <div class="metric-value">{}</div>
                    <div class="metric-label">Exercises Completed</div>
                </div>
                """.format(progress["exercises"]), unsafe_allow_html=True)
            
            # Add export functionality
            if st.button("Export Progress Report"):
                progress_report = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "metrics": progress
                }
                st.download_button(
                    "Download Report",
                    data=json.dumps(progress_report, indent=2),
                    file_name="learning_progress_report.json",
                    mime="application/json"
                )

    with tab13:
        st.subheader("👥 Social Learning Community")
        
        if not st.session_state.authenticated:
            st.warning("Please login to access social features.")
            if st.button("Login", key="social_login_button"):
                st.session_state.show_login = True
        else:
            # Create new study group section
            st.markdown("### Create New Study Group")
            col1, col2 = st.columns([2, 1])
            with col1:
                group_name = st.text_input("Group Name", key="new_group_name")
                group_description = st.text_area("Description", key="new_group_description")
                group_topic = st.text_input("Main Topic", key="new_group_topic")
                max_members = st.number_input("Maximum Members", min_value=2, max_value=50, value=10, key="new_group_max_members")
            
            with col2:
                if st.button("Create Group"):
                    if group_name and group_description and group_topic:
                        new_group = database.create_study_group(group_name, group_description, group_topic, max_members)
                        if new_group:
                            st.success(f"Study group '{group_name}' created successfully!")
                        else:
                            st.error("Failed to create study group. Please try again.")
                    else:
                        st.error("Please fill in all fields.")
            
            # Display existing study groups
            study_groups = database.get_study_groups()
            if study_groups:
                st.subheader("Available Study Groups")
                
                for group in study_groups:
                    st.markdown(f"""
                    <div style="border:1px solid #ddd; padding:20px; border-radius:10px; margin:10px 0; background-color: white;">
                        <h3 style="color: #000000;">📚 {group['name']} - {group['topic']}</h3>
                        <p style="color: #000000;"><strong>Description:</strong> {group['description']}</p>
                        <p style="color: #000000;"><strong>Members:</strong> {group['member_count']}/{group['max_members']}</p>
                        <p style="color: #000000;"><strong>Created:</strong> {group['created_at']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Join group button
                    if st.button("Join Group", key=f"join_{group['id']}"):
                        success, message = database.join_study_group(group['id'], st.session_state.current_user)
                        if success:
                            st.success(message)
                            st.experimental_rerun()
                        else:
                            st.error(message)
                    
                    # Group content tabs
                    tab1, tab2, tab3, tab4 = st.tabs(["Forum", "Resources", "Progress", "Collaboration"])
                    
                    with tab1:
                        st.subheader("Forum Discussions")
                        
                        # Create new post section
                        st.markdown("### Create New Post")
                        post_title = st.text_input("Post Title", key=f"post_title_{group['id']}")
                        post_content = st.text_area("Post Content", key=f"post_content_{group['id']}")
                        
                        if st.button("Create Post", key=f"post_{group['id']}"):
                            if post_title and post_content:
                                new_post = database.create_forum_post(
                                    group['id'], 
                                    post_title, 
                                    post_content, 
                                    st.session_state.current_user
                                )
                                if new_post:
                                    st.success("Post created successfully!")
                                    st.experimental_rerun()
                                else:
                                    st.error("Failed to create post. Please try again.")
                            else:
                                st.error("Please fill in all fields.")
                        
                        # Display posts
                        st.markdown("### Forum Posts")
                        posts = database.get_forum_posts(group['id'])
                        for post in posts:
                            st.markdown(f"""
                            <div style="border: 1px solid rgb(221, 221, 221); padding: 20px; border-radius: 10px; margin: 10px 0px; background-color: rgb(14, 17, 23);">
                                <h4 style="color: rgb(255, 255, 255);">{post['title']}</h4>
                                <p style="color: rgb(170, 170, 170);"><strong style="color: rgb(200, 200, 200);">By {post['author']}</strong> on {post['created_at']}</p>
                                <p style="color: rgb(220, 220, 220);">{post['content']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Comments section
                            st.markdown("#### Comments")
                            for comment in post.get("comments", []):
                                st.markdown(f"""
                                <div style="border: 1px solid rgb(221, 221, 221); padding: 15px; border-radius: 8px; margin: 5px 0px; background-color: rgb(20, 23, 29);">
                                    <p style="color: rgb(220, 220, 220);">{comment['content']}</p>
                                    <p style="color: rgb(170, 170, 170);"><small style="color: rgb(200, 200, 200);">By {comment['author']}</small> on {comment['created_at']}</p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Add comment
                            new_comment = st.text_area("Add a comment", key=f"comment_{post['id']}")
                            if st.button("Post Comment", key=f"comment_btn_{post['id']}"):
                                if new_comment:
                                    comment = database.add_comment(
                                        post['id'], 
                                        new_comment, 
                                        st.session_state.current_user
                                    )
                                    if comment:
                                        st.success("Comment added successfully!")
                                        st.experimental_rerun()
                                    else:
                                        st.error("Failed to add comment. Please try again.")
                            st.markdown("---")  # Add separator between posts
                    
                    with tab2:
                        st.subheader("Shared Resources")
                        
                        # Share new resource section
                        st.markdown("### Share Resource")
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            resource_title = st.text_input("Resource Title", key=f"resource_title_{group['id']}")
                            resource_description = st.text_area("Description", key=f"resource_description_{group['id']}")
                            resource_url = st.text_input("URL", key=f"resource_url_{group['id']}")
                            resource_type = st.selectbox("Resource Type", ["Article", "Video", "Course", "Book", "Other"], key=f"resource_type_{group['id']}")
                        
                        with col2:
                            if st.button("Share Resource", key=f"resource_{group['id']}"):
                                if resource_title and resource_description and resource_url:
                                    new_resource = database.share_resource(
                                        group['id'], 
                                        resource_title, 
                                        resource_description, 
                                        resource_url, 
                                        resource_type, 
                                        st.session_state.current_user
                                    )
                                    if new_resource:
                                        st.success("Resource shared successfully!")
                                        st.experimental_rerun()
                                    else:
                                        st.error("Failed to share resource. Please try again.")
                                else:
                                    st.error("Please fill in all fields.")
                        
                        # Display shared resources
                        resources = database.get_group_resources(group['id'])
                        for resource in resources:
                            st.markdown(f"""
                            <div style="border:1px solid #ddd; padding:20px; border-radius:10px; margin:10px 0; background-color: white;">
                                <h4>{resource['title']}</h4>
                                <p>{resource['description']}</p>
                                <p><strong>Type:</strong> {resource['type']}</p>
                                <p><strong>Shared by:</strong> {resource['shared_by']}</p>
                                <p><strong>Shared on:</strong> {resource['shared_at']}</p>
                                <a href="{resource['url']}" target="_blank" style="
                                    background-color: #1e88e5;
                                    color: white;
                                    padding: 8px 15px;
                                    border-radius: 5px;
                                    text-decoration: none;
                                    display: inline-block;
                                    margin-top: 10px;
                                    ">View Resource</a>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    with tab3:
                        st.subheader("Learning Progress")
                        
                        # Share progress section
                        st.markdown("### Share Your Progress")
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            progress_topic = st.text_input("Topic", key=f"progress_topic_{group['id']}")
                            progress_data = st.text_area("Progress Details", key=f"progress_data_{group['id']}")
                        
                        with col2:
                            if st.button("Share Progress", key=f"progress_{group['id']}"):
                                if progress_topic and progress_data:
                                    new_progress = database.share_progress(
                                        group['id'], 
                                        progress_topic, 
                                        progress_data, 
                                        st.session_state.current_user
                                    )
                                    if new_progress:
                                        st.success("Progress shared successfully!")
                                        st.experimental_rerun()
                                    else:
                                        st.error("Failed to share progress. Please try again.")
                                else:
                                    st.error("Please fill in all fields.")
                        
                        # Display shared progress
                        progress_shares = database.get_group_progress(group['id'])
                        for progress in progress_shares:
                            st.markdown(f"""
                            <div style="border:1px solid #ddd; padding:20px; border-radius:10px; margin:10px 0; background-color: white;">
                                <h4>Progress in {progress['topic']}</h4>
                                <p>{progress['data']}</p>
                                <p><strong>Shared by:</strong> {progress['shared_by']}</p>
                                <p><strong>Shared on:</strong> {progress['shared_at']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    with tab4:
                        st.subheader("Collaborative Coding")
                        st.info("Collaborative coding feature coming soon! This will allow real-time code sharing and editing.")
            else:
                st.info("No study groups available yet. Create one to get started!")

    with tab14:
        st.subheader("🎮 Gamification Hub")
        
        if not st.session_state.authenticated:
            st.warning("Please login to access gamification features.")
            if st.button("Login", key="gamification_login_button"):
                st.session_state.show_login = True
        else:
            # Display user's current streak
            streak_info = database.get_user_streak(st.session_state.current_user)
            if streak_info:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current Streak", f"{streak_info['current_streak']} days 🔥")
                with col2:
                    st.metric("Longest Streak", f"{streak_info['max_streak']} days ⭐")
                with col3:
                    st.metric("Last Study", streak_info['last_activity'])
            
            # Display achievements
            st.markdown("### 🏆 Achievements")
            achievements = database.get_user_achievements(st.session_state.current_user)
            if achievements:
                for achievement in achievements:
                    st.write(f"🏆 {achievement['name']} - Achieved on {achievement['date']}")
            else:
                st.write("No achievements yet! Keep learning to earn some!")
            
            # Display badges
            st.markdown("### 🎖️ Badges")
            badges = database.get_user_badges(st.session_state.current_user)
            if badges:
                for badge in badges:
                    st.write(f"{badge['icon']} {badge['name']} - {badge['description']}")
            else:
                st.write("No badges earned yet! Keep learning to earn badges!")
            
            # Display leaderboards
            st.markdown("### 📊 Leaderboards")
            leaderboard = database.create_leaderboard(
                "Quiz Performance",
                "Overall quiz performance leaderboard",
                "quiz"
            )
            if leaderboard:
                entries = database.get_leaderboard(leaderboard["id"])
                if entries:
                    st.markdown("#### Top Performers")
                    for i, entry in enumerate(entries, 1):
                        st.markdown(f"""
                        <div style="border:1px solid #ddd; padding:10px; border-radius:5px; margin:5px 0; background-color: white;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="font-weight: bold;">#{i}</span> {entry['username']}
                                </div>
                                <div>
                                    Score: {entry['score']}
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No leaderboard entries yet. Complete quizzes to see your ranking!")
            else:
                st.error("Error loading leaderboard. Please try again later.")
            
            # Display available achievements and badges
            st.markdown("### 🎯 Available Achievements")
            st.markdown("""
            - **Perfect Score** (100 points) - Complete a quiz with 100% accuracy
            - **Hard Mode Master** (200 points) - Score 80% or higher on a hard difficulty quiz
            - **Quiz Master** (150 points) - Complete 10 quizzes
            - **Streak Master** (300 points) - Maintain a 7-day study streak
            - **Topic Expert** (250 points) - Master a specific topic
            """)
            
            st.markdown("### 🎖️ Available Badges")
            st.markdown("""
            - **Quiz Master** - Complete 10 quizzes
            - **Streak Champion** - Maintain a 30-day study streak
            - **Topic Expert** - Master 5 different topics
            - **Perfect Score** - Get 100% on any quiz
            - **Early Bird** - Complete a quiz before 9 AM
            """)

if __name__ == "__main__":
    main()
