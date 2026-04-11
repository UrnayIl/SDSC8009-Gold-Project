from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import requests
import time
import os
import hashlib

app = Flask(__name__)
CORS(app)

# ==========================
# 用户系统（修复版）
# ==========================
USER_FILE = "user_credentials.json"
CHAT_DIR = "chat_histories"

def init_auth():
    if not os.path.exists(USER_FILE):
        with open(USER_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    if not os.path.exists(CHAT_DIR):
        os.makedirs(CHAT_DIR)

def encrypt(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

# 注册：兼容新旧格式，修复 string indices 错误
def register_user(username, email, password):
    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        users = {}

    # 如果是旧版数据，清空重建
    for key in list(users.keys()):
        if isinstance(users[key], str):
            del users[key]

    for existing in users.values():
        if existing.get("username") == username or existing.get("email") == email:
            return False

    users[username] = {
        "username": username,
        "email": email,
        "password": encrypt(password)
    }

    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)
    return True

# 登录：兼容用户名/邮箱
def check_user(input_str, password):
    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        return None

    encrypted = encrypt(password)
    for user in users.values():
        if not isinstance(user, dict):
            continue
        if (user.get("username") == input_str or user.get("email") == input_str) and user.get("password") == encrypted:
            return user.get("username")
    return None

def save_chat(username, password, history):
    folder = os.path.join(CHAT_DIR, f"{username}_{encrypt(password)}")
    if not os.path.exists(folder):
        os.makedirs(folder)
    path = os.path.join(folder, "history.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def load_chat(username, password):
    folder = os.path.join(CHAT_DIR, f"{username}_{encrypt(password)}")
    path = os.path.join(folder, "history.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

init_auth()

# ==========================
# GPT 调用
# ==========================
def run_gpt(prompt, retry=2):
    url = "https://api.chatanywhere.tech/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "sk-Qi2svs6TgE7uEVfKJZ3VAkOf3kT5IRYn8Xb2obJq5MdyCRqa"
    }
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000,
        "temperature": 0.7
    }
    for _ in range(retry + 1):
        try:
            res = requests.post(url, headers=headers, json=data, timeout=80)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]
        except:
            pass
        time.sleep(1)
    return None

# ==========================
# 技能系统（完全你的逻辑）
# ==========================
SKILLS_FOLDER = "skills"
ALL_SKILLS_CACHE = {}

def load_all_skills():
    global ALL_SKILLS_CACHE
    ALL_SKILLS_CACHE = {}
    if not os.path.exists(SKILLS_FOLDER):
        return
    for skill_name in os.listdir(SKILLS_FOLDER):
        skill_dir = os.path.join(SKILLS_FOLDER, skill_name)
        if not os.path.isdir(skill_dir):
            continue
        skill_content = ""
        skill_file = os.path.join(skill_dir, "SKILL.md")
        if os.path.exists(skill_file):
            with open(skill_file, "r", encoding="utf-8") as f:
                skill_content = f.read()
        ALL_SKILLS_CACHE[skill_name] = {
            "name": skill_name,
            "content": skill_content
        }

load_all_skills()

AGENT_SKILLS_MAP = {
    "nutritionist": {
        "name": "🍽️ Personal Nutritionist",
        "skills": ["nutrition-analyzer", "weightloss-analyzer", "goal-analyzer"]
    },
    "trainer": {
        "name": "🏋️ Fitness Trainer",
        "skills": ["fitness-analyzer", "rehabilitation-analyzer", "goal-analyzer"]
    },
    "health_keeper": {
        "name": "🌿 Wellness Expert",
        "skills": ["sleep-analyzer", "tcm-constitution-analyzer"]
    },
    "therapist": {
        "name": "🧠 Mental Health Counselor",
        "skills": ["mental-health-analyzer"]
    },
    "team": {
        "name": "🏥 Team Consultation",
        "skills": list(ALL_SKILLS_CACHE.keys())
    }
}

def get_skill_pool(agent_type):
    if agent_type == "team":
        return ALL_SKILLS_CACHE.copy()
    else:
        target = AGENT_SKILLS_MAP[agent_type]["skills"]
        return {k: v for k, v in ALL_SKILLS_CACHE.items() if k in target}

def select_best_skill(query, pool):
    q = query.lower()
    if "weight" in q and "weightloss-analyzer" in pool:
        return pool["weightloss-analyzer"]
    if "goal" in q or "plan" in q and "goal-analyzer" in pool:
        return pool["goal-analyzer"]
    return next(iter(pool.values())) if pool else None

# ==========================
# 接口
# ==========================
@app.route("/api/register", methods=["POST"])
def register():
    d = request.json
    username = d.get("username")
    email = d.get("email")
    password = d.get("password")
    ok = register_user(username, email, password)
    return jsonify({"success": ok, "msg": "Success" if ok else "Username or email exists"})

@app.route("/api/login", methods=["POST"])
def login():
    d = request.json
    input_str = d.get("input")
    password = d.get("password")
    username = check_user(input_str, password)
    if username:
        return jsonify({"success": True, "username": username, "history": []})
    return jsonify({"success": False, "msg": "Invalid"})

@app.route("/api/chat", methods=["POST"])
def chat():
    d = request.json
    u = d.get("username")
    p = d.get("password")
    agent_type = d.get("agent_type")
    message = d.get("message")
    history = d.get("history", [])

    if not check_user(u, p):
        return jsonify({"reply": "Please login first"})

    skill_pool = get_skill_pool(agent_type)
    skill = select_best_skill(message, skill_pool)
    if not skill:
        return jsonify({"reply": "No skill"})

    full_history = load_chat(u, p)
    user_history_text = ""
    for h in full_history:
        if h["role"] == "user":
            user_history_text += f"User: {h['content']}\n"

    current_hist_text = ""
    for h in history:
        if h["role"] == "user":
            current_hist_text += f"User: {h['content']}\n"
        else:
            current_hist_text += f"AI: {h['content']}\n"

    prompt = f"""
You are {AGENT_SKILLS_MAP[agent_type]['name']}
Skill: {skill['content']}
Ask for more information if needed. Do not diagnose or prescribe medicine.
IMPORTANT: Reply ONLY in ENGLISH.

# ALL USER HISTORY (backend only, not shown to user):
{user_history_text}

# CURRENT CONVERSATION:
{current_hist_text}
User: {message}
Please answer:
"""

    reply = run_gpt(prompt) or "Service unavailable"

    new_hist = full_history + [
        {"role": "user", "content": message},
        {"role": "ai", "content": reply}
    ]
    save_chat(u, p, new_hist)

    frontend_history = history + [
        {"role": "user", "content": message},
        {"role": "ai", "content": reply}
    ]

    return jsonify({"reply": reply, "history": frontend_history})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5177, debug=True)