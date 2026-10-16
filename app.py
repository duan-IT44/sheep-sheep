# Task Management System v1.6
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

app.jinja_env.variable_start_string = "[["
app.jinja_env.variable_end_string = "]]"

DB_FILE = "task_system.db"

# ========== Database Initialization ==========
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_title TEXT NOT NULL,
            task_description TEXT,
            start_date TEXT,
            create_time TEXT DEFAULT CURRENT_TIMESTAMP,
            deadline TEXT,
            assigned_user_id INTEGER,
            task_status TEXT DEFAULT 'pending',
            FOREIGN KEY (assigned_user_id) REFERENCES user(user_id)
        )
    """)

    cursor.execute("PRAGMA table_info(task)")
    columns = [row[1] for row in cursor.fetchall()]
    if "start_date" not in columns:
        cursor.execute("ALTER TABLE task ADD COLUMN start_date TEXT")

    cursor.execute("SELECT COUNT(*) FROM user")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO user (username, password, full_name, role)
            VALUES (?, ?, ?, ?)
        """, [
            ("admin", "123456", "Supervisor", "admin"),
            ("dev1", "123456", "Alice", "developer"),
            ("dev2", "123456", "Bob", "developer"),
        ])

    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# ========== Page Routes ==========
@app.route("/")
def index():
    return render_template("login.html")

@app.route("/admin")
def admin_page():
    return render_template("admin.html")

@app.route("/dev")
def dev_page():
    return render_template("dev.html")


# ========== User APIs ==========
@app.route("/api/user/login", methods=["POST"])
def login():
    data = request.get_json()
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM user WHERE username=? AND password=?",
        (data["username"], data["password"])
    ).fetchone()
    conn.close()
    return jsonify(dict(user) if user else None)


@app.route("/api/user/password", methods=["PUT"])
def update_pwd():
    data = request.get_json()
    conn = get_db()
    conn.execute(
        "UPDATE user SET password=? WHERE user_id=?",
        (data["password"], data["userId"])
    )
    conn.commit()
    conn.close()
    return jsonify(1)


@app.route("/api/user/all", methods=["GET"])
def get_all_users():
    conn = get_db()
    users = conn.execute(
        "SELECT user_id, username, full_name, role FROM user ORDER BY user_id"
    ).fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])


@app.route("/api/user/add", methods=["POST"])
def add_user():
    data = request.get_json()
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO user (username, password, full_name, role)
            VALUES (?, ?, ?, ?)
        """, (
            data["username"],
            data["password"],
            data["fullName"],
            data.get("role", "developer")
        ))
        conn.commit()
        conn.close()
        return jsonify(1)
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Username already exists"}), 400


@app.route("/api/user/update", methods=["PUT"])
def update_user():
    data = request.get_json()
    conn = get_db()
    try:
        conn.execute("""
            UPDATE user SET username=?, full_name=?, role=?
            WHERE user_id=?
        """, (
            data["username"],
            data["fullName"],
            data["role"],
            data["userId"]
        ))
        conn.commit()
        conn.close()
        return jsonify(1)
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Username already exists"}), 400


@app.route("/api/user/delete", methods=["DELETE"])
def delete_user():
    data = request.get_json()
    conn = get_db()
    conn.execute("UPDATE task SET assigned_user_id=NULL WHERE assigned_user_id=?", (data["userId"],))
    conn.execute("DELETE FROM user WHERE user_id=?", (data["userId"],))
    conn.commit()
    conn.close()
    return jsonify(1)


@app.route("/api/user/developers", methods=["GET"])
def get_developers():
    conn = get_db()
    users = conn.execute(
        "SELECT user_id, full_name FROM user WHERE role='developer'"
    ).fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])


# ========== Admin Task APIs ==========
@app.route("/api/task/all", methods=["GET"])
def get_all_task():
    assignee_id = request.args.get("assigneeId")
    status = request.args.get("status")
    start_date = request.args.get("startDate")
    end_date = request.args.get("endDate")
    keyword = request.args.get("keyword")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", 10))

    conditions = []
    params = []

    if assignee_id:
        conditions.append("t.assigned_user_id = ?")
        params.append(assignee_id)
    if status:
        conditions.append("t.task_status = ?")
        params.append(status)
    if start_date:
        conditions.append("t.start_date = ?")
        params.append(start_date)
    if end_date:
        conditions.append("t.deadline = ?")
        params.append(end_date)
    if keyword:
        conditions.append("(t.task_title LIKE ? OR t.task_description LIKE ?)")
        params.append(f"%{keyword}%")
        params.append(f"%{keyword}%")

    where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    conn = get_db()
    total = conn.execute(f"SELECT COUNT(*) FROM task t{where_clause}", params).fetchone()[0]

    offset = (page - 1) * page_size
    query_sql = f"""
        SELECT t.*, u.full_name as assignee_name
        FROM task t
        LEFT JOIN user u ON t.assigned_user_id = u.user_id
        {where_clause}
        ORDER BY t.task_id DESC
        LIMIT ? OFFSET ?
    """
    tasks = conn.execute(query_sql, params + [page_size, offset]).fetchall()
    conn.close()

    return jsonify({
        "items": [dict(t) for t in tasks],
        "total": total,
        "page": page,
        "pageSize": page_size
    })


@app.route("/api/task/add", methods=["POST"])
def add_task():
    data = request.get_json()
    conn = get_db()
    conn.execute("""
        INSERT INTO task (task_title, task_description, start_date, deadline, assigned_user_id, task_status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    """, (
        data["taskTitle"],
        data.get("taskDescription", ""),
        data.get("startDate", ""),
        data.get("deadline", ""),
        data.get("assignedUserId")
    ))
    conn.commit()
    conn.close()
    return jsonify(1)


@app.route("/api/task/update", methods=["PUT"])
def update_task():
    data = request.get_json()
    conn = get_db()
    conn.execute("""
        UPDATE task 
        SET task_title=?, task_description=?, start_date=?, deadline=?, assigned_user_id=?
        WHERE task_id=?
    """, (
        data["taskTitle"],
        data.get("taskDescription", ""),
        data.get("startDate", ""),
        data.get("deadline", ""),
        data.get("assignedUserId"),
        data["taskId"]
    ))
    conn.commit()
    conn.close()
    return jsonify(1)


@app.route("/api/task/assign", methods=["PUT"])
def assign_task():
    data = request.get_json()
    conn = get_db()
    conn.execute(
        "UPDATE task SET assigned_user_id=? WHERE task_id=?",
        (data["assignedUserId"], data["taskId"])
    )
    conn.commit()
    conn.close()
    return jsonify(1)


@app.route("/api/task/status", methods=["PUT"])
def update_status():
    data = request.get_json()
    conn = get_db()
    conn.execute(
        "UPDATE task SET task_status=? WHERE task_id=?",
        (data["taskStatus"], data["taskId"])
    )
    conn.commit()
    conn.close()
    return jsonify(1)


@app.route("/api/task/delete", methods=["DELETE"])
def delete_task():
    data = request.get_json()
    conn = get_db()
    conn.execute("DELETE FROM task WHERE task_id=?", (data["taskId"],))
    conn.commit()
    conn.close()
    return jsonify(1)


@app.route("/api/task/stat", methods=["GET"])
def task_stat():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM task").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM task WHERE task_status='pending'").fetchone()[0]
    processing = conn.execute("SELECT COUNT(*) FROM task WHERE task_status='processing'").fetchone()[0]
    finished = conn.execute("SELECT COUNT(*) FROM task WHERE task_status='finished'").fetchone()[0]
    conn.close()
    return jsonify({
        "total": total,
        "pending": pending,
        "processing": processing,
        "finished": finished
    })


# ========== Developer Task APIs (NEW) ==========
@app.route("/api/task/my", methods=["GET"])
def get_my_task():
    """Get current developer's tasks with filtering and pagination"""
    user_id = request.args.get("userId")
    status = request.args.get("status")
    start_date = request.args.get("startDate")
    end_date = request.args.get("endDate")
    keyword = request.args.get("keyword")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", 10))

    conditions = ["assigned_user_id = ?"]
    params = [user_id]

    if status:
        conditions.append("task_status = ?")
        params.append(status)
    if start_date:
        conditions.append("start_date = ?")
        params.append(start_date)
    if end_date:
        conditions.append("deadline = ?")
        params.append(end_date)
    if keyword:
        conditions.append("(task_title LIKE ? OR task_description LIKE ?)")
        params.append(f"%{keyword}%")
        params.append(f"%{keyword}%")

    where_clause = " WHERE " + " AND ".join(conditions)

    conn = get_db()
    total = conn.execute(f"SELECT COUNT(*) FROM task{where_clause}", params).fetchone()[0]

    offset = (page - 1) * page_size
    query_sql = f"""
        SELECT * FROM task
        {where_clause}
        ORDER BY task_id DESC
        LIMIT ? OFFSET ?
    """
    tasks = conn.execute(query_sql, params + [page_size, offset]).fetchall()
    conn.close()

    return jsonify({
        "items": [dict(t) for t in tasks],
        "total": total,
        "page": page,
        "pageSize": page_size
    })


@app.route("/api/task/my/stat", methods=["GET"])
def my_task_stat():
    """Get statistics for current developer only"""
    user_id = request.args.get("userId")
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM task WHERE assigned_user_id=?", (user_id,)).fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM task WHERE assigned_user_id=? AND task_status='pending'", (user_id,)).fetchone()[0]
    processing = conn.execute("SELECT COUNT(*) FROM task WHERE assigned_user_id=? AND task_status='processing'", (user_id,)).fetchone()[0]
    finished = conn.execute("SELECT COUNT(*) FROM task WHERE assigned_user_id=? AND task_status='finished'", (user_id,)).fetchone()[0]
    conn.close()
    return jsonify({
        "total": total,
        "pending": pending,
        "processing": processing,
        "finished": finished
    })


if __name__ == "__main__":
    init_db()
    print("=" * 50)
    print("Task Management System is starting...")
    print("Open your browser at: http://localhost:8080")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8080, debug=True)