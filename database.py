import sqlite3
import hashlib
from datetime import datetime
import json

def init_db():
    """Initialize the database with required tables"""
    try:
        with sqlite3.connect('learning_assistant.db') as conn:
            c = conn.cursor()
            
            # Users table
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Quiz results table
            c.execute('''
                CREATE TABLE IF NOT EXISTS quiz_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    topic TEXT,
                    score INTEGER,
                    total_questions INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Study groups table
            c.execute('''
                CREATE TABLE IF NOT EXISTS study_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    topic TEXT,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            ''')
            
            # Group members table
            c.execute('''
                CREATE TABLE IF NOT EXISTS group_members (
                    group_id INTEGER,
                    user_id INTEGER,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (group_id, user_id),
                    FOREIGN KEY (group_id) REFERENCES study_groups (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Forum posts table
            c.execute('''
                CREATE TABLE IF NOT EXISTS forum_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER,
                    user_id INTEGER,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (group_id) REFERENCES study_groups (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Comments table
            c.execute('''
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER,
                    user_id INTEGER,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES forum_posts (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Learning progress table
            c.execute('''
                CREATE TABLE IF NOT EXISTS learning_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    topic TEXT,
                    time_spent INTEGER,
                    completed BOOLEAN DEFAULT 0,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Add streaks table
            c.execute('''
                CREATE TABLE IF NOT EXISTS user_streaks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    last_activity_date DATE,
                    current_streak INTEGER DEFAULT 1,
                    max_streak INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Achievements table
            c.execute('''
                CREATE TABLE IF NOT EXISTS user_achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    achievement_name TEXT NOT NULL,
                    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Badges table
            c.execute('''
                CREATE TABLE IF NOT EXISTS user_badges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    badge_name TEXT NOT NULL,
                    badge_description TEXT,
                    badge_icon TEXT,
                    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
        return True, "Database initialized successfully!"
    except Exception as e:
        return False, f"Error initializing database: {str(e)}"

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, email):
    """Create a new user"""
    conn = None
    try:
        conn = sqlite3.connect('learning_assistant.db')
        c = conn.cursor()
        
        hashed_password = hash_password(password)
        c.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)',
                 (username, hashed_password, email))
        
        conn.commit()
        return True, "User created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username or email already exists!"
    except Exception as e:
        return False, f"Error creating user: {str(e)}"
    finally:
        if conn:
            conn.close()

def verify_user(username, password):
    """Verify user credentials"""
    try:
        with sqlite3.connect('learning_assistant.db') as conn:
            c = conn.cursor()
            hashed_password = hash_password(password)
            c.execute('SELECT id FROM users WHERE username = ? AND password = ?',
                     (username, hashed_password))
            result = c.fetchone()
            
        if result:
            return True, "Login successful!"
        return False, "Invalid username or password!"
    except Exception as e:
        return False, f"Error verifying user: {str(e)}"

def save_quiz_results(user_id, topic, score, total_questions):
    """Save quiz results"""
    try:
        with sqlite3.connect('learning_assistant.db') as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO quiz_results (user_id, topic, score, total_questions)
                VALUES (?, ?, ?, ?)
            ''', (user_id, topic, score, total_questions))
            conn.commit()
        return True, "Quiz results saved successfully!"
    except Exception as e:
        return False, f"Error saving quiz results: {str(e)}"

def create_study_group(name, description, topic, created_by):
    """Create a new study group"""
    try:
        conn = sqlite3.connect('learning_assistant.db')
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO study_groups (name, description, topic, created_by)
            VALUES (?, ?, ?, ?)
        ''', (name, description, topic, created_by))
        
        group_id = c.lastrowid
        
        # Add creator as first member
        c.execute('''
            INSERT INTO group_members (group_id, user_id)
            VALUES (?, ?)
        ''', (group_id, created_by))
        
        conn.commit()
        conn.close()
        return True, "Study group created successfully!"
    except Exception as e:
        return False, f"Error creating study group: {str(e)}"

def join_study_group(group_id, user_id):
    """Join a study group"""
    try:
        conn = sqlite3.connect('learning_assistant.db')
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO group_members (group_id, user_id)
            VALUES (?, ?)
        ''', (group_id, user_id))
        
        conn.commit()
        conn.close()
        return True, "Joined study group successfully!"
    except sqlite3.IntegrityError:
        return False, "Already a member of this group!"
    except Exception as e:
        return False, f"Error joining study group: {str(e)}"

def create_forum_post(group_id, user_id, title, content):
    """Create a new forum post"""
    try:
        conn = sqlite3.connect('learning_assistant.db')
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO forum_posts (group_id, user_id, title, content)
            VALUES (?, ?, ?, ?)
        ''', (group_id, user_id, title, content))
        
        conn.commit()
        conn.close()
        return True, "Forum post created successfully!"
    except Exception as e:
        return False, f"Error creating forum post: {str(e)}"

def add_comment(post_id, user_id, content):
    """Add a comment to a forum post"""
    try:
        conn = sqlite3.connect('learning_assistant.db')
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO comments (post_id, user_id, content)
            VALUES (?, ?, ?)
        ''', (post_id, user_id, content))
        
        conn.commit()
        conn.close()
        return True, "Comment added successfully!"
    except Exception as e:
        return False, f"Error adding comment: {str(e)}"

def update_learning_progress(user_id, topic, time_spent, completed=False):
    """Update user's learning progress"""
    try:
        conn = sqlite3.connect('learning_assistant.db')
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO learning_progress (user_id, topic, time_spent, completed)
            VALUES (?, ?, ?, ?)
        ''', (user_id, topic, time_spent, completed))
        
        conn.commit()
        conn.close()
        return True, "Learning progress updated successfully!"
    except Exception as e:
        return False, f"Error updating learning progress: {str(e)}"

def get_user_progress(user_id):
    """Get user's learning progress"""
    try:
        conn = sqlite3.connect('learning_assistant.db')
        c = conn.cursor()
        
        c.execute('''
            SELECT topic, SUM(time_spent) as total_time, COUNT(*) as sessions
            FROM learning_progress
            WHERE user_id = ?
            GROUP BY topic
        ''', (user_id,))
        
        progress = c.fetchall()
        conn.close()
        
        return {
            'topics': [{'topic': row[0], 'total_time': row[1], 'sessions': row[2]} 
                      for row in progress],
            'total_time': sum(row[1] for row in progress)
        }
    except Exception as e:
        return {'topics': [], 'total_time': 0}

def get_study_groups():
    """Get all study groups"""
    try:
        with sqlite3.connect('learning_assistant.db') as conn:
            c = conn.cursor()
            c.execute('''
                SELECT sg.id, sg.name, sg.description, sg.topic, sg.created_by, 
                       u.username as creator_name,
                       COUNT(gm.user_id) as member_count
                FROM study_groups sg
                LEFT JOIN users u ON sg.created_by = u.id
                LEFT JOIN group_members gm ON sg.id = gm.group_id
                GROUP BY sg.id
            ''')
            
            columns = ['id', 'name', 'description', 'topic', 'created_by', 'creator_name', 'member_count']
            study_groups = [dict(zip(columns, row)) for row in c.fetchall()]
            
            return study_groups
    except Exception as e:
        print(f"Error fetching study groups: {str(e)}")
        return []

def get_user_streak(user_id):
    """Get user's current streak information"""
    try:
        with sqlite3.connect('learning_assistant.db') as conn:
            c = conn.cursor()
            
            # Check if user has any streak record
            c.execute('''
                SELECT last_activity_date, current_streak, max_streak 
                FROM user_streaks 
                WHERE user_id = ?
            ''', (user_id,))
            
            result = c.fetchone()
            
            if not result:
                # Initialize streak for new user
                today = datetime.now().date()
                c.execute('''
                    INSERT INTO user_streaks (user_id, last_activity_date, current_streak, max_streak)
                    VALUES (?, ?, 1, 1)
                ''', (user_id, today))
                conn.commit()
                return {
                    'current_streak': 1,
                    'max_streak': 1,
                    'last_activity': today.isoformat()
                }
            
            last_activity = datetime.strptime(result[0], '%Y-%m-%d').date()
            current_streak = result[1]
            max_streak = result[2]
            
            today = datetime.now().date()
            days_diff = (today - last_activity).days
            
            if days_diff > 1:
                # Streak broken
                current_streak = 1
                c.execute('''
                    UPDATE user_streaks 
                    SET current_streak = 1, last_activity_date = ?
                    WHERE user_id = ?
                ''', (today, user_id))
            elif days_diff == 1:
                # Streak continues
                current_streak += 1
                max_streak = max(current_streak, max_streak)
                c.execute('''
                    UPDATE user_streaks 
                    SET current_streak = ?, max_streak = ?, last_activity_date = ?
                    WHERE user_id = ?
                ''', (current_streak, max_streak, today, user_id))
            
            conn.commit()
            
            return {
                'current_streak': current_streak,
                'max_streak': max_streak,
                'last_activity': last_activity.isoformat()
            }
            
    except Exception as e:
        print(f"Error getting user streak: {str(e)}")
        return {
            'current_streak': 0,
            'max_streak': 0,
            'last_activity': None
        }

def update_user_streak(user_id):
    """Update user's streak for today's activity"""
    try:
        with sqlite3.connect('learning_assistant.db') as conn:
            c = conn.cursor()
            today = datetime.now().date()
            
            c.execute('''
                INSERT INTO user_streaks (user_id, last_activity_date, current_streak, max_streak)
                VALUES (?, ?, 1, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                last_activity_date = ?
                WHERE user_id = ?
            ''', (user_id, today, today, user_id))
            
            conn.commit()
        return True, "Streak updated successfully!"
    except Exception as e:
        return False, f"Error updating streak: {str(e)}"

def get_user_achievements(user_id):
    """Get all achievements for a user"""
    try:
        with sqlite3.connect('learning_assistant.db') as conn:
            c = conn.cursor()
            c.execute('''
                SELECT achievement_name, achieved_at
                FROM user_achievements
                WHERE user_id = ?
                ORDER BY achieved_at DESC
            ''', (user_id,))
            
            achievements = [{'name': row[0], 'date': row[1]} for row in c.fetchall()]
            return achievements
    except Exception as e:
        print(f"Error getting user achievements: {str(e)}")
        return []

def award_achievement(user_id, achievement_name):
    """Award a new achievement to a user"""
    try:
        with sqlite3.connect('learning_assistant.db') as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO user_achievements (user_id, achievement_name)
                VALUES (?, ?)
            ''', (user_id, achievement_name))
            conn.commit()
        return True, "Achievement awarded successfully!"
    except Exception as e:
        return False, f"Error awarding achievement: {str(e)}"

def get_user_badges(user_id):
    """Get all badges earned by a user"""
    try:
        with sqlite3.connect('learning_assistant.db') as conn:
            c = conn.cursor()
            c.execute('''
                SELECT badge_name, badge_description, badge_icon, earned_at
                FROM user_badges
                WHERE user_id = ?
                ORDER BY earned_at DESC
            ''', (user_id,))
            
            badges = [{
                'name': row[0],
                'description': row[1],
                'icon': row[2],
                'earned_at': row[3]
            } for row in c.fetchall()]
            return badges
    except Exception as e:
        print(f"Error getting user badges: {str(e)}")
        return []

def award_badge(user_id, badge_name, badge_description="", badge_icon="🏅"):
    """Award a new badge to a user"""
    try:
        with sqlite3.connect('learning_assistant.db') as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO user_badges (user_id, badge_name, badge_description, badge_icon)
                VALUES (?, ?, ?, ?)
            ''', (user_id, badge_name, badge_description, badge_icon))
            conn.commit()
        return True, "Badge awarded successfully!"
    except Exception as e:
        return False, f"Error awarding badge: {str(e)}"

def create_leaderboard(time_period=None, topic=None, limit=None):
    """
    Create a leaderboard based on quiz scores and learning progress
    
    Args:
        time_period (str, optional): 'week', 'month', 'all_time'
        topic (str, optional): Filter by specific topic
        limit (int, optional): Limit number of results
    """
    try:
        with sqlite3.connect('learning_assistant.db') as conn:
            c = conn.cursor()
            
            # Base query
            query = '''
                SELECT 
                    u.username,
                    COUNT(DISTINCT qr.id) as quizzes_taken,
                    COALESCE(AVG(CAST(qr.score AS FLOAT) / qr.total_questions * 100), 0) as avg_score,
                    COALESCE(SUM(lp.time_spent), 0) as total_study_time,
                    COALESCE(us.current_streak, 0) as current_streak,
                    COALESCE(us.max_streak, 0) as max_streak
                FROM users u
                LEFT JOIN quiz_results qr ON u.id = qr.user_id
                LEFT JOIN learning_progress lp ON u.id = lp.user_id
                LEFT JOIN user_streaks us ON u.id = us.user_id
            '''
            
            conditions = []
            params = []
            
            # Add time period filter
            if time_period:
                if time_period == 'week':
                    conditions.append("qr.timestamp >= date('now', '-7 days')")
                elif time_period == 'month':
                    conditions.append("qr.timestamp >= date('now', '-1 month')")
            
            # Add topic filter
            if topic:
                conditions.append("qr.topic = ?")
                params.append(topic)
            
            # Add WHERE clause if there are conditions
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            # Add GROUP BY and ORDER BY
            query += '''
                GROUP BY u.id, u.username
                ORDER BY 
                    avg_score DESC,
                    total_study_time DESC,
                    max_streak DESC
            '''
            
            # Add LIMIT clause
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            c.execute(query, params)
            
            columns = ['username', 'quizzes_taken', 'avg_score', 'total_study_time', 
                      'current_streak', 'max_streak']
            leaderboard = [dict(zip(columns, row)) for row in c.fetchall()]
            
            # Calculate ranks
            for i, entry in enumerate(leaderboard, 1):
                entry['rank'] = i
                entry['avg_score'] = round(entry['avg_score'], 2)
                entry['study_hours'] = round(entry['total_study_time'] / 3600, 1)
            
            return leaderboard
    except Exception as e:
        print(f"Error creating leaderboard: {str(e)}")
        return []

def get_user_rank(user_id):
    """Get a specific user's rank and stats"""
    try:
        with sqlite3.connect('learning_assistant.db') as conn:
            c = conn.cursor()
            
            c.execute('''
                WITH UserStats AS (
                    SELECT 
                        u.id,
                        u.username,
                        COUNT(DISTINCT qr.id) as quizzes_taken,
                        COALESCE(AVG(CAST(qr.score AS FLOAT) / qr.total_questions * 100), 0) as avg_score,
                        COALESCE(SUM(lp.time_spent), 0) as total_study_time,
                        COALESCE(us.current_streak, 0) as current_streak,
                        COALESCE(us.max_streak, 0) as max_streak,
                        RANK() OVER (ORDER BY 
                            COALESCE(AVG(CAST(qr.score AS FLOAT) / qr.total_questions * 100), 0) DESC,
                            COALESCE(SUM(lp.time_spent), 0) DESC
                        ) as rank
                    FROM users u
                    LEFT JOIN quiz_results qr ON u.id = qr.user_id
                    LEFT JOIN learning_progress lp ON u.id = lp.user_id
                    LEFT JOIN user_streaks us ON u.id = us.user_id
                    GROUP BY u.id, u.username
                )
                SELECT * FROM UserStats WHERE id = ?
            ''', (user_id,))
            
            result = c.fetchone()
            if result:
                return {
                    'username': result[1],
                    'quizzes_taken': result[2],
                    'avg_score': round(result[3], 2),
                    'study_hours': round(result[4] / 3600, 1),
                    'current_streak': result[5],
                    'max_streak': result[6],
                    'rank': result[7]
                }
            return None
    except Exception as e:
        print(f"Error getting user rank: {str(e)}")
        return None 