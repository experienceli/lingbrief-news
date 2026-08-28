# -*- coding: utf-8 -*-
"""摘要打分模块：优先调用 DeepSeek（DEEPSEEK_API_KEY），无 key 时降级为规则引擎。纯标准库。"""
import json, os, re, time, urllib.request
from datetime import datetime

CATEGORY_LABELS = {
    "conference": "会议征稿", "lecture": "讲座交流", "policy": "政策项目",
    "journal": "期刊论文", "news": "学界动态", "job": "岗位招聘", "book": "新书出版",
    "international": "国际视野",
}

SYSTEM_PROMPT = '你是"语言学界今日要闻"的资深编辑，为语言学学术资讯做中文摘要与打分。' '对每条资讯输出 JSON（必须是一个 JSON 对象）：' '{"items": [{"summary": "80字内中文摘要, 用自己的话, 事实准确", "reason": "40字内为什么值得语言学者关注", "score": 0-100整数, "category": "conference|lecture|policy|journal|news|job|book|international"}]} ' '规则：score 评审标准=学术价值40 + 时效性25 + 影响力35；信息缺失时给保守分；category 只从给定枚举选。'

def get_api_key(config):
    return os.environ.get(config.get("llm", {}).get("env_key", "DEEPSEEK_API_KEY"), "").strip()

def call_deepseek(prompt, config):
    llm = config.get("llm", {})
    body = {
        "model": llm.get("model", "deepseek-chat"),
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        "max_tokens": 4000,
    }
    req = urllib.request.Request(
        llm.get("api_base", "https://api.deepseek.com/chat/completions"),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + get_api_key(config)})
    with urllib.request.urlopen(req, timeout=90) as resp:
        d = json.loads(resp.read().decode("utf-8"))
    return d["choices"][0]["message"]["content"]

def parse_model_output(text):
    """容错解析 LLM 返回的 JSON（可能带 fenced code block）"""
    text = text.strip()
    fence = chr(96) * 3
    if fence in text:
        text = text.split(fence)[-2] if text.count(fence) >= 2 else text
    try:
        d = json.loads(text)
    except Exception:
        try:
            d = json.loads(text[text.find("{"):text.rfind("}") + 1])
        except Exception:
            return None
    return d.get("items") if isinstance(d, dict) else d

def rule_enrich(items, today):
    """无 LLM 时的降级：规则摘要 + 模板推荐理由 + 启发式打分"""
    tmpl = {
        "conference": "会议/征稿动态，留意投稿截止时间与会议时间地点，符合研究方向的建议转给课题组。",
        "lecture": "讲座/学术交流信息，可关注讲题与主讲人，线上讲座可安排旁听。",
        "policy": "政策或评审动态，涉及基金、项目、学科建设与语言文字工作，建议对照自身申报计划。",
        "journal": "期刊或论文动态，值得追踪最新一期的选题与理论方法走向。",
        "news": "学界要闻，帮你快速掌握领域最近发生了什么。",
        "job": "岗位招聘信息，符合条件的可投递或转发。",
        "book": "新书出版信息，可作教学与备课参考。",
        "international": "国际学界动态，了解域外研究趋势。",
    }
    for it in items:
        raw = it.get("raw_text", "") or it.get("summary", "")
        it["summary"] = (raw.strip()[:160]) or it.get("title", "")
        cat = it.get("category", "news")
        it["reason"] = tmpl.get(cat, "领域动态，值得一看。")
        score = 55 + it.get("weight", 5)
        for k in ["征稿", "征文", "招聘", "诚聘", "入选", "发布", "出版", "座谈", "研讨会", "论坛", "启动", "青年"]:
            if k in it.get("title", ""):
                score += 4
                break
        pub = it.get("published_at", "")
        if pub:
            try:
                age = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(pub, "%Y-%m-%d")).days
                score += max(0, 8 - age * 2)
            except Exception:
                pass
        it["score"] = min(99, max(40, score))
    return True

def enrich(items, config, today, verbose=True):
    """入口：优先 LLM 批量，失败/无 key 回退规则。返回 LLM 处理条数。"""
    if not get_api_key(config):
        rule_enrich(items, today)
        if verbose:
            print("  [llm] 未配置 API Key，使用规则降级模式（摘要=原文截断，打分=启发式）")
        return 0
    llm = config.get("llm", {})
    batch = llm.get("batch_size", 10)
    done = 0
    for i in range(0, len(items), batch):
        chunk = items[i:i + batch]
        lines = []
        for j, it in enumerate(chunk):
            lines.append("[%d] 来源:%s | 分类:%s | 标题:%s | 原文片段:%s" % (
                j, it["source"], CATEGORY_LABELS.get(it["category"], "其他"),
                it.get("title", ""), (it.get("raw_text") or "")[:400]))
        prompt = "请处理以下 %d 条语言学资讯，输出 items 数组（顺序与输入一致）：\n" % len(chunk) + "\n".join(lines)
        try:
            out = parse_model_output(call_deepseek(prompt, config))
        except Exception as e:
            print("  [warn] LLM 调用失败，本批回退规则: %s" % e)
            rule_enrich(chunk, today)
            done += len(chunk)
            continue
        if not out:
            rule_enrich(chunk, today)
            done += len(chunk)
            continue
        for j, it in enumerate(chunk):
            if j < len(out) and isinstance(out[j], dict):
                it["summary"] = (out[j].get("summary") or it.get("raw_text", ""))[:300]
                it["reason"] = (out[j].get("reason") or "")[:120]
                try:
                    it["score"] = int(out[j].get("score", 60))
                except Exception:
                    it["score"] = 60
                if out[j].get("category") in CATEGORY_LABELS:
                    it["category"] = out[j]["category"]
            else:
                rule_enrich([it], today)
        done += len(chunk)
    if verbose:
        print("  [llm] 已用 %s 处理 %d 条" % (llm.get("model", "deepseek-chat"), done))
    return done
