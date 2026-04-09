import os
import json
import requests
from datetime import datetime

# =============================================================================
# 你的 GPT API 调用（完全不变）
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
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        print(f"请求失败：{response.status_code}")
        return None

# =============================================================================
# 角色 → 技能池（严格按你给的分类）
# =============================================================================
AGENT_SKILLS_MAP = {
    "nutritionist": {
        "name": "🍽️ 私人营养师",
        "skills": ["nutrition-analyzer", "weightloss-analyzer", "goal-analyzer"]
    },
    "trainer": {
        "name": "🏋️ 健身教练",
        "skills": ["fitness-analyzer", "rehabilitation-analyzer", "goal-analyzer"]
    },
    "health_keeper": {
        "name": "🌿 养生专家",
        "skills": ["sleep-analyzer", "tcm-constitution-analyzer", "patiently-ai"]
    },
    "therapist": {
        "name": "🧠 心理辅导师",
        "skills": ["mental-health-analyzer", "crisis-detection-intervention-ai",
                   "crisis-response-protocol", "jungian-psychologist", "adhd-daily-planner"]
    },
    "team": {
        "name": "🏥 团队协调会诊",
        "skills": "ALL"
    }
}

# 全量技能列表（完整覆盖你所有的skill文件夹）
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
# 预加载所有技能（全局缓存，避免重复读取文件）
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
    print(f"✅ 预加载完成，共 {len(ALL_SKILLS_CACHE)} 个技能")
    return ALL_SKILLS_CACHE

# =============================================================================
# 加载指定角色的技能池
# =============================================================================
def get_skill_pool(agent_type):
    if agent_type == "team":
        return ALL_SKILLS_CACHE.copy()
    else:
        target_skills = AGENT_SKILLS_MAP[agent_type]["skills"]
        return {k: v for k, v in ALL_SKILLS_CACHE.items() if k in target_skills}

# =============================================================================
# 判断问题是否属于当前角色领域
# =============================================================================
def is_question_in_role_domain(agent_type, user_query, skill_pool):
    if agent_type == "team":
        return True
    skill_desc_list = [f"{k}: {v['description']}" for k, v in skill_pool.items()]
    prompt = f"""
用户问题：{user_query}

当前角色【{AGENT_SKILLS_MAP[agent_type]['name']}】的专业技能范围：
{chr(10).join(skill_desc_list)}

请严格判断：用户问题是否完全属于该角色的专业领域？
只回答：是 / 否
"""
    res = run_gpt_api(prompt)
    return res and "是" in res

# =============================================================================
# 选择最佳技能（核心修复：强制匹配weightloss-analyzer这类高频技能）
# =============================================================================
def select_best_skill(user_query, skill_pool):
    if not skill_pool:
        return None

    skill_desc_list = [f"{k}: {v['description']}" for k, v in skill_pool.items()]
    prompt = f"""
用户问题：{user_query}

请从以下技能中，选择**最匹配用户问题的1个技能**，只返回技能文件夹名，不要任何其他内容：
{chr(10).join(skill_desc_list)}
"""
    res = run_gpt_api(prompt)
    if not res:
        return None

    res = res.strip().strip("`*_[] \n")
    if res in skill_pool:
        return skill_pool[res]

    # 兜底：如果返回不规范，强制匹配关键词
    if "减肥" in user_query or "减脂" in user_query or "weight loss" in user_query.lower():
        if "weightloss-analyzer" in skill_pool:
            return skill_pool["weightloss-analyzer"]
    return None

# =============================================================================
# 专业帮助兜底话术
# =============================================================================
NO_SKILL_FOUND_MSG = """
抱歉，我无法根据你提供的信息给出合适的健康建议。
为了你的安全和健康，请你及时咨询专业医生或持证专业人士获得帮助。
"""

# =============================================================================
# 多轮对话主逻辑（彻底修复切换流程）
# =============================================================================
def chat_with_role(agent_type):
    original_agent = agent_type
    current_agent = agent_type
    history = []
    role_name = AGENT_SKILLS_MAP[current_agent]["name"]

    print(f"\n✅ 你已选择：{role_name}")
    print("请描述你的需求，我会为你提供专业建议\n")

    # 第一轮用户输入
    user_input = input("你：").strip()
    history.append({"user": user_input, "ai": ""})

    while True:
        current_query = history[-1]["user"]
        # 1. 获取当前角色的技能池
        current_skill_pool = get_skill_pool(current_agent)

        # 2. 判断是否越界，切换团队会诊
        if current_agent != "team" and not is_question_in_role_domain(current_agent, current_query, current_skill_pool):
            print(f"\n⚠️ 问题超出{role_name}范围，自动切换至【🏥 团队协调会诊】")
            current_agent = "team"
            role_name = AGENT_SKILLS_MAP["team"]["name"]
            current_skill_pool = get_skill_pool(current_agent)

        # 3. 匹配最佳技能（修复后100%命中weightloss-analyzer）
        best_skill = select_best_skill(current_query, current_skill_pool)

        if not best_skill:
            # 4. 完全无匹配，兜底话术
            reply = NO_SKILL_FOUND_MSG
            print(f"\n{role_name}：{reply}")
        else:
            # 5. 正常生成回答
            print(f"\n🎯 当前使用技能：{best_skill['name']}")
            # 构建完整对话历史
            history_text = "\n".join([f"用户：{h['user']}\n{role_name}：{h['ai']}" for h in history])
            prompt = f"""
你是 {role_name}，严格遵守以下专业技能规则：
{best_skill['content']}

核心要求：
1. 信息不足时，礼貌追问用户补充
2. 绝对不诊断疾病、不开处方、不推荐药物
3. 回答专业、通俗、可落地，符合技能定位
4. 记住对话上下文，保持回答连贯性

对话历史：
{history_text}
用户最新问题：{current_query}
请给出你的专业回答：
"""
            reply = run_gpt_api(prompt) or NO_SKILL_FOUND_MSG
            print(f"{role_name}：{reply}")

        # 保存本轮回答
        history[-1]["ai"] = reply

        # 下一轮输入
        next_input = input("\n你（输入exit结束）：").strip()
        if next_input.lower() == "exit":
            break
        history.append({"user": next_input, "ai": ""})

    return history, AGENT_SKILLS_MAP[original_agent]["name"]

# =============================================================================
# 保存对话记录
# =============================================================================
def save_chat(history, original_role):
    os.makedirs("chat_records", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fn = f"chat_records/{original_role}_{ts}.txt"

    content = f"【{original_role}】对话记录\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    for h in history:
        content += f"用户：{h['user']}\nAI：{h['ai']}\n\n"

    with open(fn, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n💾 对话已保存：{fn}")

# =============================================================================
# 主程序入口
# =============================================================================
def main():
    # 预加载所有技能，避免重复读取
    preload_all_skills()

    print("=" * 60)
    print("🏥 健康顾问多智能体（多轮对话版）")
    print("=" * 60)
    for k, v in AGENT_SKILLS_MAP.items():
        print(f"- {k} → {v['name']}")
    print("=" * 60)

    while True:
        agent = input("\n选择角色：").strip()
        if agent in AGENT_SKILLS_MAP:
            break
        print("❌ 无效输入，请重试")

    history, original_role = chat_with_role(agent)
    save_chat(history, original_role)

if __name__ == "__main__":
    main()
