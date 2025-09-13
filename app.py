from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Database setup
def init_db():
    """Initialize the database with tables and sample data"""
    conn = sqlite3.connect('blog.db')
    c = conn.cursor()
    
    # Drop existing tables if they exist (for clean setup)
    c.execute('DROP TABLE IF EXISTS comments')
    c.execute('DROP TABLE IF EXISTS articles')
    
    # Create articles table
    c.execute('''
        CREATE TABLE articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create comments table
    c.execute('''
        CREATE TABLE comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (article_id) REFERENCES articles (id)
        )
    ''')
    
    # Insert sample data
    sample_articles = [
        ("Welcome to Our Blog", "This is our first blog post. Welcome to our community! Feel free to leave comments and share your thoughts.", "Admin"),
        ("Flask Web Development", "Flask is a lightweight web framework for Python that makes it easy to build web applications. It's perfect for beginners and experienced developers alike.", "John Doe"),
        ("Security Best Practices", "Always sanitize user input and use proper authentication mechanisms. Security should be a top priority in any web application.", "Security Expert")
    ]
    
    c.executemany('INSERT INTO articles (title, content, author) VALUES (?, ?, ?)', sample_articles)
    
    # Insert sample comments
    sample_comments = [
        (1, "Alice", "Great introduction! Looking forward to more posts."),
        (1, "Bob", "Thanks for creating this blog. Very informative!"),
        (2, "Charlie", "Flask is indeed amazing. I've been using it for years."),
        (3, "Dave", "Security is so important. Thanks for the reminder!")
    ]
    
    c.executemany('INSERT INTO comments (article_id, author, content) VALUES (?, ?, ?)', sample_comments)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

# Database helper functions
def get_db_connection():
    conn = sqlite3.connect('blog.db')
    conn.row_factory = sqlite3.Row
    return conn

def ensure_db_exists():
    """Ensure database exists and is properly initialized"""
    if not os.path.exists('blog.db'):
        init_db()
        return
    
    # Check if tables exist and have the right structure
    try:
        conn = get_db_connection()
        conn.execute('SELECT id, title, content, author, created_at FROM articles LIMIT 1')
        conn.execute('SELECT id, article_id, author, content, created_at FROM comments LIMIT 1')
        conn.close()
    except sqlite3.OperationalError:
        # Tables don't exist or have wrong structure, reinitialize
        init_db()

@app.route('/')
def index():
    ensure_db_exists()
    
    conn = get_db_connection()
    
    # Get all articles
    articles = conn.execute('SELECT * FROM articles ORDER BY created_at DESC').fetchall()
    
    # Get comment counts for each article
    articles_with_counts = []
    for article in articles:
        comment_count = conn.execute(
            'SELECT COUNT(*) FROM comments WHERE article_id = ?', 
            (article['id'],)
        ).fetchone()[0]
        
        # Convert Row to dict and add comment count
        article_dict = dict(article)
        article_dict['comment_count'] = comment_count
        articles_with_counts.append(article_dict)
    
    conn.close()
    return render_template('index.html', articles=articles_with_counts)

@app.route('/post/<int:post_id>')
def post(post_id):
    ensure_db_exists()
    
    conn = get_db_connection()
    
    # Get the article
    article = conn.execute('SELECT * FROM articles WHERE id = ?', (post_id,)).fetchone()
    if not article:
        flash('Article not found!', 'error')
        conn.close()
        return redirect(url_for('index'))
    
    # Get comments for this article
    comments = conn.execute('''
        SELECT * FROM comments 
        WHERE article_id = ? 
        ORDER BY created_at ASC
    ''', (post_id,)).fetchall()
    
    conn.close()
    return render_template('post.html', article=article, comments=comments)

@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    ensure_db_exists()
    
    author = request.form.get('author', '').strip()
    content = request.form.get('content', '').strip()
    
    if not author or not content:
        flash('Both name and comment are required!', 'error')
        return redirect(url_for('post', post_id=post_id))
    
    if len(author) > 100:
        flash('Name must be less than 100 characters!', 'error')
        return redirect(url_for('post', post_id=post_id))
    
    if len(content) > 1000:
        flash('Comment must be less than 1000 characters!', 'error')
        return redirect(url_for('post', post_id=post_id))
    
    conn = get_db_connection()
    
    # Verify article exists
    article = conn.execute('SELECT id FROM articles WHERE id = ?', (post_id,)).fetchone()
    if not article:
        flash('Article not found!', 'error')
        conn.close()
        return redirect(url_for('index'))
    
    # Insert comment
    conn.execute('''
        INSERT INTO comments (article_id, author, content) 
        VALUES (?, ?, ?)
    ''', (post_id, author, content))
    
    conn.commit()
    conn.close()
    
    flash('Comment added successfully!', 'success')
    return redirect(url_for('post', post_id=post_id))

@app.route('/create', methods=['GET', 'POST'])
def create_article():
    ensure_db_exists()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        author = request.form.get('author', '').strip()
        
        if not title or not content or not author:
            flash('All fields are required!', 'error')
            return render_template('create.html')
        
        if len(title) > 200:
            flash('Title must be less than 200 characters!', 'error')
            return render_template('create.html')
        
        if len(author) > 100:
            flash('Author name must be less than 100 characters!', 'error')
            return render_template('create.html')
        
        if len(content) > 10000:
            flash('Content must be less than 10000 characters!', 'error')
            return render_template('create.html')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO articles (title, content, author) 
            VALUES (?, ?, ?)
        ''', (title, content, author))
        conn.commit()
        
        # Get the ID of the newly created article
        new_article_id = cursor.lastrowid
        conn.close()
        
        flash('Article created successfully!', 'success')
        return redirect(url_for('post', post_id=new_article_id))
    
    return render_template('create.html')

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    print("Starting Flask Blog Application...")
    print("Initializing database...")
    ensure_db_exists()
    print("Database ready!")
    print("Starting server on http://localhost:5000")
    app.run(debug=True)