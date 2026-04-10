from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import requests
import time

app = Flask(__name__)
CORS(app)

# =============================================================================
# GPT API 调用（超时 60 秒 + 重试）
# =============================================================================
def run_gpt_api(st: str, retry: int = 2):
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

    for attempt in range(retry + 1):
        try:
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(data),
                timeout=80
            )
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                print(f"API失败 {attempt+1}：{response.status_code}")
        except Exception as e:
            print(f"API异常 {attempt+1}：{str(e)}")

        if attempt < retry:
            time.sleep(1)

    return None

# =============================================================================
# 角色配置（英文）
# =============================================================================
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
# 技能加载（安全版，不报错）
# =============================================================================
ALL_SKILLS_CACHE = {}

def preload_all_skills(skills_dir="skills"):
    global ALL_SKILLS_CACHE
    ALL_SKILLS_CACHE = {}
    for skill_name in ALL_SKILLS:
        ALL_SKILLS_CACHE[skill_name] = {
            "name": skill_name,
            "description": "Health service",
            "content": "You are a professional health expert, answer user questions in English.",
            "folder": skill_name
        }

preload_all_skills()

# =============================================================================
# 工具函数
# =============================================================================
def get_skill_pool(agent_type):
    if agent_type == "team":
        return ALL_SKILLS_CACHE.copy()
    else:
        target = AGENT_SKILLS_MAP[agent_type]["skills"]
        return {k: v for k, v in ALL_SKILLS_CACHE.items() if k in target}

def select_best_skill(query, pool):
    if ("weight loss" in query.lower() or "lose weight" in query.lower()) and "weightloss-analyzer" in pool:
        return pool["weightloss-analyzer"]
    if ("goal" in query.lower() or "plan" in query.lower()) and "goal-analyzer" in pool:
        return pool["goal-analyzer"]
    if pool:
        return next(iter(pool.values()))
    return None

NO_SKILL_MSG = "Sorry, I cannot provide advice. Please consult a professional."
API_ERROR_MSG = "AI service is temporarily unavailable."

# =============================================================================
# 🔥 核心修复：兼容前端 history 格式
# =============================================================================
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    agent = data.get("agent_type")
    msg = data.get("message")
    history = data.get("history", [])

    current_agent = agent
    skill_pool = get_skill_pool(current_agent)
    best = select_best_skill(msg, skill_pool)
    
    if not best:
        return jsonify({"reply": NO_SKILL_MSG, "agent": current_agent})

    # --------------------------
    # 🔥 修复这里！适配前端新格式
    # --------------------------
    history_lines = []
    for h in history:
        if h.get("role") == "user":
            history_lines.append(f"User: {h.get('content', '')}")
        elif h.get("role") == "ai":
            history_lines.append(f"AI: {h.get('content', '')}")
    history_text = "\n".join(history_lines)

    # Prompt 强制英文
    prompt = f"""
You are {AGENT_SKILLS_MAP[current_agent]['name']}
Skill: {best['content']}
Ask for more information if needed. Do not diagnose or prescribe medicine.
IMPORTANT: Reply ONLY in ENGLISH.

Conversation History:
{history_text}
User: {msg}
Please answer:
"""
    reply = run_gpt_api(prompt)
    if not reply:
        reply = API_ERROR_MSG

    return jsonify({
        "reply": reply,
        "agent": current_agent
    })

# =============================================================================
# 运行
# =============================================================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5177, debug=True)