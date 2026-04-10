from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# =============================================================================
# GPT API
# =============================================================================
def run_gpt_api(st: str):
    url = "https://api.chatanywhere.tech/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "sk-Qi2svs6TgE7uEVfKJZ3VAkOf3kT5IRYn8Xb2obJq5MdyCRqa"
    }
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": st}],
        "max_tokens": 2000,
        "temperature": 0.7,
        "n": 1
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=100)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except:
        pass
    return "AI service is temporarily unavailable"  # 英文错误提示

# =============================================================================
# 角色配置（名称改为英文）
# =============================================================================
AGENT_SKILLS_MAP = {
    "nutritionist": {
        "name": "🍽️ Personal Nutritionist",  # 英文名称
        "skills": ["nutrition-analyzer", "weightloss-analyzer", "goal-analyzer"]
    },
    "trainer": {
        "name": "🏋️ Fitness Trainer",
        "skills": ["fitness-analyzer", "rehabilitation-analyzer", "goal-analyzer"]
    },
    "health_keeper": {
        "name": "🌿 Wellness Expert",
        "skills": ["sleep-analyzer", "tcm-constitution-analyzer", "patiently-ai"]
    },
    "therapist": {
        "name": "🧠 Mental Health Counselor",
        "skills": ["mental-health-analyzer", "crisis-detection-intervention-ai",
                   "crisis-response-protocol", "jungian-psychologist", "adhd-daily-planner"]
    },
    "team": {
        "name": "🏥 Team Consultation",
        "skills": "ALL"
    }
}

ALL_SKILLS = [
    "adhd-daily-planner",
    "crisis-detection-intervention-ai",
    "crisis-response-protocol",
    "fitness-analyzer",
    "goal-analyzer",
    "health-trend-analyzer",
    "jungian-psychologist",
    "mental-health-analyzer",
    "nutrition-analyzer",
    "occupational-health-analyzer",
    "patiently-ai",
    "rehabilitation-analyzer",
    "sleep-analyzer",
    "tcm-constitution-analyzer",
    "weightloss-analyzer"
]

# =============================================================================
# 预加载技能
# =============================================================================
ALL_SKILLS_CACHE = {}

def preload_all_skills(skills_dir="skills"):
    global ALL_SKILLS_CACHE
    for folder in ALL_SKILLS:
        path = os.path.join(skills_dir, folder, "SKILL.md")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            name, desc = "", ""
            for line in content.split("\n"):
                if "name:" in line.lower():
                    name = line.split(":", 1)[1].strip()
                if "description:" in line.lower():
                    desc = line.split(":", 1)[1].strip()
                    break
            ALL_SKILLS_CACHE[folder] = {
                "name": name,
                "description": desc,
                "content": content,
                "folder": folder
            }

preload_all_skills()

# =============================================================================
# 工具函数（提示词改为英文）
# =============================================================================
def get_skill_pool(agent_type):
    if agent_type == "team":
        return ALL_SKILLS_CACHE.copy()
    else:
        target = AGENT_SKILLS_MAP[agent_type]["skills"]
        return {k: v for k, v in ALL_SKILLS_CACHE.items() if k in target}

def is_question_in_role_domain(agent_type, query, pool):
    if agent_type == "team":
        return True
    lines = [f"{k}: {v['description']}" for k, v in pool.items()]
    # 英文提示词
    prompt = f"Question: {query}\nProfessional scope: {lines}\nDoes it belong to this field? Answer only Yes/No"
    res = run_gpt_api(prompt)
    return res and "Yes" in res

def select_best_skill(query, pool):
    lines = [f"{k}: {v['description']}" for k, v in pool.items()]
    # 英文提示词
    prompt = f"Question: {query}\nSelect the best matching skill, return only the folder name:\n{lines}"
    res = run_gpt_api(prompt)
    if res:
        res = res.strip().strip("`*[] ")
        if res in pool:
            return pool[res]
    return next(iter(pool.values())) if pool else None

NO_SKILL_MSG = "Sorry, I cannot provide advice. Please consult a professional."  # 英文提示

# =============================================================================
# 聊天接口（Prompt强制英文输出）
# =============================================================================
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    agent = data.get("agent_type")
    msg = data.get("message")
    history = data.get("history", [])

    current_agent = agent
    skill_pool = get_skill_pool(current_agent)
    if current_agent != "team" and not is_question_in_role_domain(current_agent, msg, skill_pool):
        current_agent = "team"
        skill_pool = get_skill_pool("team")

    best = select_best_skill(msg, skill_pool)
    if not best:
        return jsonify({"reply": NO_SKILL_MSG, "skill": "None"})

    history_text = "\n".join([f"User: {h['user']}\nAI: {h['ai']}" for h in history])
    # 核心修改：Prompt添加强制英文输出要求 + 所有提示词改为英文
    prompt = f"""
You are {AGENT_SKILLS_MAP[current_agent]['name']}
Skill: {best['content']}
If information is insufficient, ask follow-up questions. Do not make diagnoses or prescribe medication. Remember the conversation context.
IMPORTANT: All responses must be in English, no Chinese allowed.

Conversation History:
{history_text}
User: {msg}
Please answer in English:
"""
    reply = run_gpt_api(prompt) or NO_SKILL_MSG
    return jsonify({"reply": reply, "skill_used": best['name'], "agent": current_agent})

# =============================================================================
# 运行
# =============================================================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5177, debug=True)