# 任务分配管理系统 v1.1
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

# 让 Jinja2 改用 [[ ]] 作为变量分隔符，把 {{ }} 让给 Vue
app.jinja_env.variable_start_string = "[["
app.jinja_env.variable_end_string = "]]"

DB_FILE = "task_system.db"

# ========== 数据库初始化 ==========
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
            create_time TEXT DEFAULT CURRENT_TIMESTAMP,
            deadline TEXT,
            assigned_user_id INTEGER,
            task_status TEXT DEFAULT 'pending',
            FOREIGN KEY (assigned_user_id) REFERENCES user(user_id)
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM user")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO user (username, password, full_name, role)
            VALUES (?, ?, ?, ?)
        """, [
            ("admin", "123456", "主管", "admin"),
            ("dev1", "123456", "员工甲", "developer"),
            ("dev2", "123456", "员工乙", "developer"),
        ])

    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# ========== 页面路由 ==========
@app.route("/")
def index():
    return render_template("login.html")

@app.route("/admin")
def admin_page():
    return render_template("admin.html")

@app.route("/dev")
def dev_page():
    return render_template("dev.html")


# ========== API 接口 ==========

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


@app.route("/api/task/all", methods=["GET"])
def get_all_task():
    conn = get_db()
    tasks = conn.execute("""
        SELECT t.*, u.full_name as assignee_name
        FROM task t
        LEFT JOIN user u ON t.assigned_user_id = u.user_id
        ORDER BY t.task_id DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(t) for t in tasks])


@app.route("/api/task/my", methods=["GET"])
def get_my_task():
    user_id = request.args.get("userId")
    conn = get_db()
    tasks = conn.execute(
        "SELECT * FROM task WHERE assigned_user_id=? ORDER BY task_id DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return jsonify([dict(t) for t in tasks])


@app.route("/api/task/add", methods=["POST"])
def add_task():
    data = request.get_json()
    conn = get_db()
    conn.execute("""
        INSERT INTO task (task_title, task_description, deadline, assigned_user_id, task_status)
        VALUES (?, ?, ?, ?, 'pending')
    """, (
        data["taskTitle"],
        data.get("taskDescription", ""),
        data.get("deadline", ""),
        data.get("assignedUserId")
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


@app.route("/api/user/developers", methods=["GET"])
def get_developers():
    conn = get_db()
    users = conn.execute(
        "SELECT user_id, full_name FROM user WHERE role='developer'"
    ).fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

@app.route("/api/user/all", methods=["GET"])
def get_all_users():
    """查询所有用户"""
    conn = get_db()
    users = conn.execute(
        "SELECT user_id, username, full_name, role FROM user ORDER BY user_id"
    ).fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])


@app.route("/api/user/add", methods=["POST"])
def add_user():
    """添加新员工"""
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
        return jsonify({"error": "用户名已存在"}), 400


@app.route("/api/user/delete", methods=["DELETE"])
def delete_user():
    """删除员工（同时清空其名下任务的负责人）"""
    data = request.get_json()
    conn = get_db()
    conn.execute("UPDATE task SET assigned_user_id=NULL WHERE assigned_user_id=?", (data["userId"],))
    conn.execute("DELETE FROM user WHERE user_id=?", (data["userId"],))
    conn.commit()
    conn.close()
    return jsonify(1)



if __name__ == "__main__":
    init_db()
    print("=" * 50)
    print("任务分配管理系统正在启动...")
    print("请在浏览器中打开: http://localhost:8080")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8080, debug=True)