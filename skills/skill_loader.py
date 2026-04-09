import os
import glob

# 技能库根目录
SKILL_ROOT = os.path.dirname(__file__)

def load_agent_skills(agent_type: str) -> str:
    """
    加载对应智能体的所有 SKILL.md 技能
    :param agent_type: nutritionist / trainer / health_keeper / therapist
    :return: 拼接好的专业技能文本（给AI用）
    """
    agent_skill_dir = os.path.join(SKILL_ROOT, agent_type)
    if not os.path.exists(agent_skill_dir):
        return "无技能配置"

    # 查找所有子文件夹下的 SKILL.md
    skill_files = glob.glob(f"{agent_skill_dir}/*/SKILL.md")
    skill_content = ""

    # 读取每个技能文件
    for idx, file in enumerate(skill_files, 1):
        try:
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
                skill_content += f"\n===== 技能 {idx} =====\n{content}\n"
        except:
            continue

    return skill_content

def build_agent_system_prompt(agent_type: str) -> str:
    """
    【核心】生成带完整 Skill 库的系统指令
    从文件夹自动读取所有技能！
    """
    agent_names = {
        "nutritionist": "🍽️ 私人营养师",
        "trainer": "🏋️ 健身教练",
        "health_keeper": "🌿 养生专家",
        "therapist": "🧠 心理辅导师"
    }

    # 加载该角色的所有 MD 技能
    skills = load_agent_skills(agent_type)

    # 最终系统 Prompt
    return f"""
    你是 {agent_names[agent_type]}，专业私人健康顾问。
    你的全部专业技能（来自 Skill 库）：
    {skills}

    通用规则：
    1. 只回答本领域问题，不跨领域
    2. 语言通俗、落地、亲切
    3. 不诊断疾病、不开处方、不推荐药物
    4. 记住用户对话历史，个性化服务
    """
