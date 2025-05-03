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

# Load environment variables
load_dotenv()

# Configure API key
api_key = os.getenv("GENIE_API_KEY")
print(f"API key length: {len(api_key)}")

# Configure genai with specific settings
genai.configure(
    api_key=api_key,
    transport="rest",
    client_options={
        "api_endpoint": "generativelanguage.googleapis.com",
        "credentials_file": None,
    }
)

# Configure Tesseract
pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

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
        model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest")
        response = model.generate_content(prompt)
        return response.text
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
        model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest")
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
        model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest")
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
        return questions_data.get("mcqs", [])
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
        model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest")
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
        return questions_data.get("true_false", [])
    except Exception as e:
        st.error(f"Error parsing response: {e}")
        return []

def save_quiz_results():
    """Save quiz results to session state history"""
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
        
        model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest")
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
        
        model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
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
        
        model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
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
        
        model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
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
        
        model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
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
        
        model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
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

def test_connection(max_retries=3):
    for attempt in range(max_retries):
        try:
            print(f"\nAttempt {attempt + 1} of {max_retries}")
            
            # List available models
            print("Listing available models...")
            models = genai.list_models()
            print("Available models:", [m.name for m in models])
            
            # Try different model versions
            model_versions = ['gemini-pro', 'gemini-1.0-pro', 'gemini-pro-vision']
            
            for model_name in model_versions:
                try:
                    print(f"\nTrying model: {model_name}")
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content('Say hello!')
                    print(f"Success with {model_name}!")
                    print("Response:", response.text)
                    return True
                except Exception as e:
                    print(f"Failed with {model_name}: {str(e)}")
            
            time.sleep(2)  # Wait before retry
            
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry
            continue
    
    return False

def main():
    """Main function to run the Streamlit app"""
    st.title("🎯Personalized Education Through AI Learning Assistant")
    st.markdown("""
    <style>
        .stButton button {
            width: 100%;
            height: 100%;
            white-space: normal;
            padding: 1rem;
            background-color: white;
            color: black;
            border: 2px solid #e6e6e6;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 200px;
            aspect-ratio: 1;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            font-size: 16px;
            text-align: center;
            overflow-y: auto;
            max-height: 200px;
        }
        .stButton button:hover {
            transform: scale(1.02);
            box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
        }
        .card {
            padding: 2rem;
            border-radius: 10px;
            border: 2px solid #e6e6e6;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            background-color: white;
            color: black;
        }
        [data-testid="column"] {
            width: calc(33.33% - 1rem) !important;
            margin: 0.5rem !important;
        }
        .flashcard-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            padding: 1rem;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 0.5rem;
        }
        .reset-button button {
            min-height: 50px !important;
        }
        .stMarkdown p {
            color: white;
        }
    </style>
    """, unsafe_allow_html=True)

    # File uploader and text input section
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

    # Add tabs for Quiz, Summary, and Flashcards
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "Generate Quiz", 
        "Generate Summary", 
        "Flashcards", 
        "Analytics", 
        "Video Resources",
        "Books & PDFs",
        "Latest News",
        "Learning Roadmap",
        "Learning Resources",
        "Relevant Certifications"
    ])

    with tab1:
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

        if st.button("Generate Quiz", key="generate_quiz"):
            if text_content:
                with st.spinner("Generating quiz questions..."):
                    if quiz_type == "Multiple Choice":
                        st.session_state.questions = fetch_questions(text_content=text_content, quiz_level=quiz_level.lower())
                        if st.session_state.questions:
                            st.session_state.selected_options = [None] * len(st.session_state.questions)
                            st.session_state.correct_answers = [
                                q["options"].get(q["correct"], "Unknown") for q in st.session_state.questions
                            ]
                    else:  # True/False
                        st.session_state.questions = fetch_true_false_questions(text_content=text_content, quiz_level=quiz_level.lower())
                        if st.session_state.questions:
                            st.session_state.selected_options = [None] * len(st.session_state.questions)
                            st.session_state.correct_answers = [
                                q["correct_answer"] for q in st.session_state.questions
                            ]
                    
                    if st.session_state.questions:
                        st.session_state.quiz_generated = True
                        st.session_state.submitted = False
                        st.session_state.marks = 0
                    else:
                        st.session_state.quiz_generated = False
                        st.error("Could not generate quiz questions. Please try again with different text or quiz level.")
            else:
                st.warning("Please upload a file or paste text content to generate quiz questions.")
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

            if st.session_state.submitted:
                correct_count = 0
                for i in range(len(st.session_state.questions)):
                    if st.session_state.selected_options[i] == st.session_state.correct_answers[i]:
                        correct_count += 1
                st.session_state.marks = correct_count

                st.header("Quiz Result:")
                for i, question in enumerate(st.session_state.questions):
                    st.subheader(f"Question {i+1}: {question['mcq'] if 'mcq' in question else question['question']}")
                    # Add a white background container with padding for better visibility
                    st.markdown("""
                        <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 10px 0;">
                            <p style="color: #333; margin: 5px 0;"><strong>Your answer:</strong> {}</p>
                            <p style="color: #333; margin: 5px 0;"><strong>Correct answer:</strong> {}</p>
                        </div>
                    """.format(
                        st.session_state.selected_options[i] if st.session_state.selected_options[i] else "No answer selected",
                        st.session_state.correct_answers[i]
                    ), unsafe_allow_html=True)
                    
                    if st.session_state.selected_options[i] == st.session_state.correct_answers[i]:
                        st.success("✅ Correct!")
                    else:
                        st.error("❌ Incorrect")
                    st.write("---")

                st.subheader(f"Final Score: {st.session_state.marks} out of {len(st.session_state.questions)}")

    with tab2:
        if st.button("Generate Summary", key="generate_summary"):
            if text_content:
                with st.spinner("Generating summary..."):
                    summary = generate_summary(text_content)
                    if summary:
                        st.subheader("Text Summary")
                        st.markdown(f'<div class="card">{summary}</div>', unsafe_allow_html=True)
            else:
                st.warning("Please upload a file or paste text content to generate a summary.")

    with tab3:
        if "flashcards" not in st.session_state:
            st.session_state.flashcards = []
        if "flipped_cards" not in st.session_state:
            st.session_state.flipped_cards = set()

        if st.button("Generate Flashcards", key="generate_flashcards"):
            if text_content:
                with st.spinner("Generating flashcards..."):
                    st.session_state.flashcards = generate_flashcards(text_content)
                    st.session_state.flipped_cards = set()
                    
                    if not st.session_state.flashcards:
                        st.error("Failed to generate flashcards. Please try again.")
            else:
                st.warning("Please upload a file or paste text content to generate flashcards.")

        if st.session_state.flashcards:
            # Create 3x3 grid layout
            for row in range(3):
                cols = st.columns(3)
                for col in range(3):
                    card_index = row * 3 + col
                    if card_index < len(st.session_state.flashcards):
                        with cols[col]:
                            card = st.session_state.flashcards[card_index]
                            is_flipped = card_index in st.session_state.flipped_cards
                            card_content = card['back'] if is_flipped else card['front']
                            
                            if st.button(
                                card_content,
                                key=f"card_{card_index}",
                                use_container_width=True,
                                help="Click to flip card"
                            ):
                                if card_index in st.session_state.flipped_cards:
                                    st.session_state.flipped_cards.remove(card_index)
                                else:
                                    st.session_state.flipped_cards.add(card_index)

            # Add reset button centered below the grid
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("Reset All Cards", key="reset_button", help="Click to flip all cards back to front"):
                    st.session_state.flipped_cards = set()

    with tab4:
        show_analytics()

    with tab5:
        if st.button("Find Related Videos"):
            if text_content:
                with st.spinner("Searching for relevant educational videos..."):
                    videos = get_youtube_recommendations(text_content)
                    
                    if videos:
                        st.subheader("Recommended Educational Videos")
                        
                        # Display videos in a grid
                        cols = st.columns(2)
                        for idx, video in enumerate(videos):
                            with cols[idx % 2]:
                                st.markdown(f"""
                                <div style="border:1px solid #ddd; padding:10px; border-radius:5px; margin:5px;">
                                    <img src="{video['thumbnail']}" style="width:100%;">
                                    <h4>{video['title']}</h4>
                                    <p>{video['description'][:100]}...</p>
                                    <a href="{video['url']}" target="_blank">Watch Video</a>
                                </div>
                                """, unsafe_allow_html=True)
                    else:
                        st.warning("No relevant videos found.")
            else:
                st.warning("Please upload a file or paste text content to find related videos.")

    with tab6:
        if st.button("Find Related Books"):
            if text_content:
                with st.spinner("Finding relevant books..."):
                    books = get_book_suggestions(text_content)
                    
                    if books:
                        st.subheader("📚 Recommended Books")
                        
                        for book in books:
                            with st.container():
                                st.markdown(f"""
                                <div style="border:1px solid #ddd; padding:20px; border-radius:10px; margin:10px 0; background-color: white;">
                                    <h3 style="color: #1e88e5; margin:0;">{book['title']}</h3>
                                    <p style="color: #666; font-style:italic; margin:5px 0;">
                                        by {book['author']} | {book['publisher']} ({book['year']})
                                    </p>
                                    <p style="color: #333; margin:10px 0;">
                                        <strong>ISBN-13:</strong> {book['isbn']}
                                    </p>
                                    <p style="color: #333; margin:10px 0;">{book['description']}</p>
                                    <div style="margin:10px 0;">
                                        <span style="background-color: #e3f2fd; padding:5px 10px; border-radius:15px; margin-right:10px;">
                                            {book['level']}
                                        </span>
                                    </div>
                                    <p style="color: #666; margin:10px 0;">
                                        <strong>Topics:</strong> {book['topics']}
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
                    else:
                        st.warning("No relevant books found. Please try again.")
            else:
                st.warning("Please upload a file or paste text content to find related books.")

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
                        st.warning("Could not find recent verified news articles. Try adjusting the topic or checking back later.")
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
                        st.warning("Could not generate roadmap. Please try again.")
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

if __name__ == "__main__":
    print("Testing Gemini API connection...")
    success = test_connection()
    
    if not success:
        print("\nTroubleshooting steps:")
        print("1. Make sure you're connected to a VPN (US or UK region)")
        print("2. Verify your API key at https://makersuite.google.com/app/apikey")
        print("3. Enable the API at https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com")
        print("4. Check if your Google Cloud project has billing enabled")
    else:
        main()
