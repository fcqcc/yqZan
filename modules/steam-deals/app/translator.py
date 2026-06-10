"""游戏名和简介智能翻译 — 用 DashScope API"""
import httpx
import json
import os

DASHSCOPE_KEY = "sk-51bc840d42c6446bac35a56502e98b3a"
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


def translate_text(text: str, context: str = "游戏") -> str:
    """翻译一段英文到中文"""
    if not text or len(text) < 3:
        return ""

    prompt = f"请将以下{context}相关的英文翻译成自然的中文（不要直译，要符合中文游戏玩家习惯）：\n\n{text}"

    try:
        r = httpx.post(API_URL, json={
            "model": "qwen-plus",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 300
        }, headers={
            "Authorization": f"Bearer {DASHSCOPE_KEY}",
            "Content-Type": "application/json"
        }, timeout=30)
        data = r.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  翻译失败: {e}")
    return ""


def translate_deals(deals: list[dict]) -> list[dict]:
    """批量翻译游戏名和简介"""
    updated = []
    for d in deals:
        changes = {}
        name = d.get("name", "")

        # 翻译游戏名（如果没有中文名）
        if not d.get("name_cn") or d["name_cn"].strip() == "":
            cn = translate_text(name, "游戏名称")
            if cn and cn != name:
                changes["name_cn"] = cn
                d["name_cn"] = cn
                print(f"  {name} → {cn}")

        # 翻译简介（如果太长，截取翻译）
        desc = d.get("short_description", "")
        if desc and len(desc) > 20:
            cn_desc = translate_text(desc[:200], "游戏介绍")
            if cn_desc and len(cn_desc) > 10:
                changes["short_description"] = cn_desc
                d["short_description"] = cn_desc

        if changes:
            updated.append(d)

    print(f"  翻译完成: {len(updated)} 款")
    return deals
