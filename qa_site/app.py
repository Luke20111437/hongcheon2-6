from flask import Flask, render_template, request, redirect, url_for, abort, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

ADMIN_PASSWORD = "6325"
ADMIN_LOGIN_PASSWORD = "6325"
CATEGORIES = ["국어", "영어", "수학", "과학", "역사", "그 외"]

# DB 초기화 함수
def init_db():
    conn = sqlite3.connect('qa.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            title TEXT,
            content TEXT,
            created_at TEXT,
            password TEXT,
            category TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER,
            content TEXT,
            created_at TEXT,
            FOREIGN KEY(question_id) REFERENCES questions(id)
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('qa.db')
    c = conn.cursor()
    c.execute('''
        SELECT q.*, COUNT(a.id) as answer_count
        FROM questions q
        LEFT JOIN answers a ON q.id = a.question_id
        GROUP BY q.id
        ORDER BY answer_count = 0 DESC, q.created_at DESC
    ''')
    questions = c.fetchall()
    conn.close()
    return render_template('index.html', questions=questions, categories=CATEGORIES)

@app.route('/category/<string:category>')
def category_view(category):
    if category not in CATEGORIES:
        abort(404)
    conn = sqlite3.connect('qa.db')
    c = conn.cursor()
    c.execute('''
        SELECT q.*, COUNT(a.id) as answer_count
        FROM questions q
        LEFT JOIN answers a ON q.id = a.question_id
        WHERE q.category = ?
        GROUP BY q.id
        ORDER BY answer_count = 0 DESC, q.created_at DESC
    ''', (category,))
    questions = c.fetchall()
    conn.close()
    return render_template('index.html', questions=questions, categories=CATEGORIES, current_category=category)

@app.route('/ask', methods=['GET', 'POST'])
def ask():
    if request.method == 'POST':
        name = request.form.get('name')
        title = request.form.get('title')
        content = request.form.get('content')
        password = request.form.get('password')
        category = request.form.get('category')
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        conn = sqlite3.connect('qa.db')
        c = conn.cursor()
        c.execute("INSERT INTO questions (name, title, content, created_at, password, category) VALUES (?, ?, ?, ?, ?, ?)",
                  (name, title, content, created_at, password, category))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('ask.html', categories=CATEGORIES)

@app.route('/question/<int:question_id>', methods=['GET', 'POST'])
def question(question_id):
    conn = sqlite3.connect('qa.db')
    c = conn.cursor()

    if request.method == 'POST':
        content = request.form.get('content')
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        c.execute("INSERT INTO answers (question_id, content, created_at) VALUES (?, ?, ?)",
                  (question_id, content, created_at))
        conn.commit()

    c.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
    question = c.fetchone()
    c.execute("SELECT * FROM answers WHERE question_id = ? ORDER BY id", (question_id,))
    answers = c.fetchall()
    conn.close()
    return render_template('question.html', question=question, answers=answers)

@app.route('/delete/<int:question_id>', methods=['POST'])
def delete_question(question_id):
    password = request.form.get('password')
    adminpw = request.args.get('adminpw')
    conn = sqlite3.connect('qa.db')
    c = conn.cursor()
    c.execute("SELECT password FROM questions WHERE id = ?", (question_id,))
    row = c.fetchone()
    if not row:
        abort(404)

    if adminpw == ADMIN_PASSWORD or (row[0] and row[0] == password):
        c.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        c.execute("DELETE FROM answers WHERE question_id = ?", (question_id,))
        conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/edit/<int:question_id>', methods=['GET', 'POST'])
def edit_question(question_id):
    adminpw = request.args.get('adminpw')
    if adminpw != ADMIN_PASSWORD:
        abort(403)
    conn = sqlite3.connect('qa.db')
    c = conn.cursor()
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        c.execute("UPDATE questions SET title = ?, content = ? WHERE id = ?", (title, content, question_id))
        conn.commit()
        conn.close()
        return redirect(url_for('question', question_id=question_id))
    c.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
    question = c.fetchone()
    conn.close()
    return render_template('edit.html', question=question)

@app.route('/answer_delete/<int:answer_id>')
def delete_answer(answer_id):
    adminpw = request.args.get('adminpw')
    if adminpw != ADMIN_PASSWORD:
        abort(403)
    conn = sqlite3.connect('qa.db')
    c = conn.cursor()
    c.execute("SELECT question_id FROM answers WHERE id = ?", (answer_id,))
    row = c.fetchone()
    if not row:
        abort(404)
    question_id = row[0]
    c.execute("DELETE FROM answers WHERE id = ?", (answer_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('question', question_id=question_id))

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_LOGIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error=True)
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    conn = sqlite3.connect('qa.db')
    c = conn.cursor()
    c.execute('''
        SELECT q.*, COUNT(a.id) as answer_count
        FROM questions q
        LEFT JOIN answers a ON q.id = a.question_id
        GROUP BY q.id
        ORDER BY answer_count = 0 DESC, q.created_at DESC
    ''')
    questions = c.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', questions=questions, categories=CATEGORIES)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
