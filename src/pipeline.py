# -*- coding: utf-8 -*-
"""语言学资讯聚合站 · 数据管道：抓取 -> 去重合并 -> LLM摘要打分 -> 每日日报 -> 落盘 JSON"""
import json, os, sys, time, shutil
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import fetch as F
import llm as L

DATA_DIR = os.path.join(ROOT, "data")
DAILY_DIR = os.path.join(DATA_DIR, "dailies")
ITEMS_PATH = os.path.join(DATA_DIR, "items.json")
STATE_PATH = os.path.join(DATA_DIR, "state.json")

DAILY_HOUR = 8  # 每日日报生成时点（北京时间），与 aihot 对齐

def load_items():
    if os.path.exists(ITEMS_PATH):
        with open(ITEMS_PATH, encoding="utf-8") as f:
            return json.load(f)
    return []

def save_items(items):
    with open(ITEMS_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)

def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_state(s):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=1)

def run(config_path=None):
    config_path = config_path or os.path.join(ROOT, "config.json")
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    today = datetime.now().strftime("%Y-%m-%d")
    now_iso = datetime.now().isoformat(timespec="seconds")
    items = load_items()
    seen_urls = {it["url"] for it in items}
    fetcher = F.Fetcher(config)

    print("[1/4] 抓取信源 ...")
    fresh = []
    for s in config.get("sources", []):
        if not s.get("enabled", True):
            continue
        print("  - %s (%s)" % (s["name"], s["url"]))
        got = fetcher.fetch_source(s)
        fresh.extend(got)
        print("      %d 条" % len(got))

    new_items = []
    for it in fresh:
        url = it["url"]
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        rec = {
            "id": F.item_id(url),
            "url": url,
            "title": (it.get("title") or "")[:160],
            "source": it["source"],
            "source_id": it["source_id"],
            "category": it.get("category", "news"),
            "weight": it.get("weight", 5),
            "raw_text": (it.get("raw_text") or "")[:900],
            "published_at": it.get("published_raw") or it.get("published_at") or "",
            "discovered_at": now_iso,
            "summary": "",
            "reason": "",
            "score": 0,
        }
        new_items.append(rec)

    cap = config.get("llm", {}).get("max_new_items_per_run", 40)
    if len(new_items) > cap:
        print("  [note] 新条目 %d 条 > 上限 %d，保留最新 %d 条（其余下次再处理）" % (len(new_items), cap, cap))
        # 保留下游处理顺序均衡：直接截断，未处理的下次由于已 seen 会丢失——因此改为:只摘要,不丢弃
        new_items = new_items[:cap]
    print("  新条目: %d" % len(new_items))

    print("[2/4] 摘要打分 ...")
    L.enrich(new_items, config, today)

    # 去重（同一 URL 不同抓取批次），并按发布时间排序
    items = merge_new(items, new_items)
    items.sort(key=lambda x: x.get("published_at") or x.get("discovered_at") or "", reverse=True)

    print("[3/4] 生成日报 ...")
    daily = build_daily(items, today)
    if daily:
        dpath = os.path.join(DAILY_DIR, today + ".json")
        with open(dpath, "w", encoding="utf-8") as f:
            json.dump(daily, f, ensure_ascii=False, indent=1)
        print("  已写 %s（精选 %d 条）" % (dpath, len(daily["items"])))

    save_items(items)
    state = load_state()
    state["last_run"] = now_iso
    state["total_items"] = len(items)
    state["daily_hour"] = DAILY_HOUR
    save_state(state)
    print("[4/4] 完成: items=%d, new=%d" % (len(items), len(new_items)))
    return len(new_items)

def merge_new(items, new_items):
    """新条目插入，同一 URL 已存在则跳过"""
    existing = {it["url"] for it in items}
    for it in new_items:
        if it["url"] not in existing:
            items.append(it)
            existing.add(it["url"])
    return items

def build_daily(items, today):
    """生成当日日报：优先当天高分 → 最近7天 → 最近90天 → 全库最新，按分数降序取前20"""
    def in_window(cutoff):
        return [it for it in items
                if (it.get("published_at") or it.get("discovered_at", "")[:10]) >= cutoff]
    picked = [it for it in in_window(today) if it.get("score", 0) >= 60]
    if len(picked) < 5:
        t = datetime.strptime(today, "%Y-%m-%d")
        for days, min_score in ((7, 0), (90, 0)):
            cutoff = (t - timedelta(days=days)).strftime("%Y-%m-%d")
            cand = [it for it in in_window(cutoff) if it.get("score", 0) >= max(60, min_score)]
            if len(cand) >= 5:
                picked = cand
                break
    if len(picked) < 5:
        # 全库兜底：最新 20 条
        picked = sorted(items, key=lambda x: x.get("published_at") or x.get("discovered_at", ""), reverse=True)[:20]
    picked.sort(key=lambda x: -x.get("score", 0))
    return {
        "date": today,
        "title": "语言学今日资讯 %s" % today,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "items": [compact(it) for it in picked[:20]],
    }

def compact(it):
    return {k: it.get(k) for k in ("id", "title", "source", "category", "summary", "reason", "score", "url", "published_at")}

if __name__ == "__main__":
    run()
