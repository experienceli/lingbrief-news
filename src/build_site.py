# -*- coding: utf-8 -*-
"""静态站点生成器：首页精选 / 全量筛选 / 会议日历 / 日报归档 / RSS。零依赖，输出到 site/。"""
import json, os, sys, html, time
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

DATA_DIR = os.path.join(ROOT, "data")
DAILY_DIR = os.path.join(DATA_DIR, "dailies")
SITE_DIR = os.path.join(ROOT, "site")

CATS = {
    "conference": ("会议征稿", "#e05d3f"),
    "lecture":    ("讲座交流", "#8f6fd8"),
    "policy":     ("政策项目", "#2f7fd8"),
    "journal":    ("期刊论文", "#12957f"),
    "news":       ("学界动态", "#c8962e"),
    "job":        ("岗位招聘", "#5d9e3f"),
    "book":       ("新书出版", "#c2528f"),
    "international": ("国际视野", "#5b6ee1"),
}
CAT_KEYS = list(CATS.keys())

CSS = """
:root{--bg:#f7f8fa;--card:#fff;--ink:#1a1d23;--sub:#6b7280;--line:#e5e7eb;--accent:#e05d3f}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--ink);line-height:1.65}
a{color:inherit;text-decoration:none}
.wrap{max-width:860px;margin:0 auto;padding:0 16px}
header.site{border-bottom:1px solid var(--line);background:#fff}
header.site .wrap{display:flex;align-items:center;gap:16px;padding:14px 16px;flex-wrap:wrap}
.logo{font-weight:700;font-size:18px}
.logo b{color:var(--accent)}
nav{display:flex;gap:4px;margin-left:auto;flex-wrap:wrap}
nav a{padding:6px 12px;border-radius:8px;font-size:14px;color:var(--sub)}
nav a.active,nav a:hover{background:#f1f3f6;color:var(--ink)}
.today{font-size:13px;color:var(--sub)}
main{padding:24px 0 64px}
h1.page{font-size:20px;margin-bottom:4px}
.subtitle{color:var(--sub);font-size:13px;margin-bottom:20px}
.badge{display:inline-block;font-size:11px;padding:2px 8px;border-radius:999px;color:#fff;vertical-align:middle}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-bottom:14px}
.card .meta{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--sub);margin-bottom:6px;flex-wrap:wrap}
.card h2{font-size:16px;font-weight:600;margin-bottom:8px}
.card h2 a:hover{color:var(--accent)}
.card .summary{font-size:14px;color:#374151}
.card .reason{margin-top:10px;font-size:13px;background:#fff7f2;border-left:3px solid var(--accent);padding:8px 10px;border-radius:0 8px 8px 0;color:#7c3f2a}
.card .reason b{color:var(--accent)}
.card .foot{margin-top:10px;display:flex;gap:14px;font-size:12px;color:var(--sub);align-items:center;flex-wrap:wrap}
.score{font-weight:700;color:var(--accent)}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}
.filters button{border:1px solid var(--line);background:#fff;border-radius:999px;padding:5px 14px;font-size:13px;cursor:pointer;color:var(--sub)}
.filters button.active{background:var(--ink);color:#fff;border-color:var(--ink)}
.search{width:100%;padding:9px 14px;border:1px solid var(--line);border-radius:10px;font-size:14px;margin-bottom:14px}
input.search:focus{outline:2px solid #cbd5e1}
.cal-month{font-weight:700;margin:22px 0 10px;color:var(--ink)}
.day-pill{display:inline-block;font-size:12px;background:#eef1f5;padding:2px 8px;border-radius:6px;margin-right:6px}
.dcount{font-size:12px;color:var(--accent);font-weight:600}
.empty{padding:40px;text-align:center;color:var(--sub)}
footer.site{border-top:1px solid var(--line);padding:20px 0;color:var(--sub);font-size:12px;text-align:center}
.daily-head{display:flex;gap:14px;align-items:baseline;margin-bottom:16px;flex-wrap:wrap}
.archives{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin-bottom:20px}
.archives a{display:inline-block;margin:2px 8px 2px 0;font-size:13px;color:var(--sub)}
.archives a:hover{color:var(--accent)}
@media(max-width:600px){.card{padding:14px}}
"""

def esc(s):
    return html.escape(str(s or ""), quote=True)

def badge(cat):
    label, color = CATS.get(cat, (cat, "#999"))
    return '<span class="badge" style="background:%s">%s</span>' % (color, esc(label))

def card_html(it):
    cat = it.get("category", "news")
    pub = it.get("published_at") or ""
    score = it.get("score", 0)
    src = esc(it.get("source", ""))
    reason = esc(it.get("reason", ""))
    summary = esc(it.get("summary", "")) or esc((it.get("raw_text") or "")[:120])
    title = esc(it.get("title", ""))
    url = esc(it.get("url", ""))
    return ('<article class="card" data-cat="%s" data-title="%s">'
            '<div class="meta">%s<span class="score">%s</span><span>%s</span></div>'
            '<h2><a href="%s" target="_blank" rel="noopener">%s</a></h2>'
            '<div class="summary">%s</div>'
            '<div class="reason"><b>推荐理由</b> %s</div>'
            '<div class="foot"><span>来源：%s</span>'
            '<span>%s</span><a href="%s" target="_blank" rel="noopener">阅读原文 ↗</a></div>'
            '</article>') % (esc(cat), esc((it.get("title") or "")).replace('"', "&quot;"),
                             badge(cat), score, pub, url, title, summary, reason, src, pub, url)

def load_items(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def page(title, body, active, extra_js=""):
    nav = [("index.html", "今日精选"), ("all.html", "全部资讯"), ("calendar.html", "会议日历"),
           ("daily.html", "日报归档"), ("rss.xml", "RSS")]
    nav_html = "".join('<a href="%s"%s>%s</a>' % (h, ' class="active"' if h == active else "", t) for h, t in nav)
    today = datetime.now().strftime("%Y年%m月%d日")
    return ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>%s · 语言学资讯聚合</title><style>%s</style></head><body>'
            '<header class="site"><div class="wrap"><div class="logo">语闻<b>·</b>LingBrief</div>'
            '%s<div class="today">%s</div></div></header>'
            '<main><div class="wrap">%s</div></main>'
            '<footer class="site"><div class="wrap">语闻 LingBrief — 语言学资讯聚合原型（非官方）· '
            '内容版权归原来源所有，本站仅作摘要与链接 · 数据每日自动更新</div></footer>%s</body></html>'
            ) % (esc(title), CSS, nav_html, today, body, extra_js)

def build():
    os.makedirs(SITE_DIR, exist_ok=True)
    items = load_items(os.path.join(DATA_DIR, "items.json")) if os.path.exists(os.path.join(DATA_DIR, "items.json")) else []
    today = datetime.now().strftime("%Y-%m-%d")
    dailies = load_dailies()

    # ---------- 首页：今日精选 ----------
    today_items = [it for it in items if (it.get("published_at") or it.get("discovered_at", "")[:10]) == today]
    if not today_items:
        today_items = items[:12]
    today_items = [it for it in today_items if it.get("score", 0) >= 55] or today_items[:12]
    body = ('<h1 class="page">今日精选</h1><div class="subtitle">%s 共 %d 条 · 高分优先 · 点击标题阅读原文</div>'
            % (today, len(today_items)))
    body += "".join(card_html(it) for it in sorted(today_items, key=lambda x: -x.get("score", 0)))
    write_page("index.html", page("今日精选", body, "index.html"))

    # ---------- 全部资讯 ----------
    pill_html = '<div class="filters"><button data-cat="" class="active">全部</button>' + "".join(
        '<button data-cat="%s">%s</button>' % (k, esc(v[0])) for k, v in CATS.items()) + "</div>"
    items_json = json.dumps(items, ensure_ascii=False)
    body = ('<h1 class="page">全部资讯</h1><div class="subtitle">%d 条 · 支持分类与关键词筛选</div>'
            '<input class="search" id="q" placeholder="搜索标题 / 来源 / 摘要…">' % len(items))
    body += pill_html + '<div id="list">' + "".join(card_html(it) for it in items) + "</div>"
    js = """<script>
var CATS=%s;var ITEMS=%s;
var cat='',q='';
function render(){var out=ITEMS.filter(function(i){
  var okC=!cat||i.category===cat;var okQ=!q||(i.title+' '+i.source+' '+(i.summary||'')).toLowerCase().indexOf(q.toLowerCase())>=0;
  return okC&&okQ;});
  var el=document.getElementById('list');
  el.innerHTML=out.length?out.map(card).join(''):'<div class="empty">没有匹配的条目</div>';
  document.querySelectorAll('.filters button').forEach(function(b){b.classList.toggle('active',b.dataset.cat===cat)});}
function card(i){return '<article class="card" data-cat="'+i.category+'"><div class="meta">'+badge(i.category)+'<span class="score">'+i.score+'</span><span>'+(i.published_at||'')+'</span></div><h2><a href="'+i.url+'" target="_blank">'+esc(i.title)+'</a></h2><div class="summary">'+esc(i.summary||'')+'</div><div class="reason"><b>推荐理由</b> '+esc(i.reason||'')+'</div><div class="foot"><span>来源：'+esc(i.source)+'</span><a href="'+i.url+'" target="_blank">阅读原文 ↗</a></div></article>';}
function badge(c){var m=CATS[c]||[c,'#999'];return '<span class="badge" style="background:'+m[1]+'">'+esc(m[0])+'</span>';}
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(m){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]});}
document.querySelectorAll('.filters button').forEach(function(b){b.onclick=function(){cat=b.dataset.cat;render();};});
document.getElementById('q').oninput=function(e){q=e.target.value;render();};render();
</script>""" % (json.dumps(CATS, ensure_ascii=False), items_json)
    write_page("all.html", page("全部资讯", body, "all.html", js))

    # ---------- 会议日历 ----------
    cal_items = [it for it in items if it.get("category") in ("conference", "lecture", "policy")]
    now = datetime.now()
    months = {}
    for it in cal_items:
        d = it.get("published_at", "")[:7]
        months.setdefault(d, []).append(it)
    body = ('<h1 class="page">会议 · 讲座 · 政策日历</h1><div class="subtitle">%d 条相关信息，按时间倒序；"距今"为公告发布天数</div>' % len(cal_items))
    for m in sorted(months.keys(), reverse=True):
        body += '<div class="cal-month">%s</div>' % m
        for it in sorted(months[m], key=lambda x: -x.get("score", 0)):
            pub = it.get("published_at", "")
            days = ""
            if pub:
                try:
                    days = (datetime.strptime(pub, "%Y-%m-%d") - now).days
                    days = (now - datetime.strptime(pub, "%Y-%m-%d")).days
                    days = '<span class="dcount">%d 天前发布</span>' % days
                except Exception:
                    days = ""
            body += ('<div class="card"><div class="meta">%s<span>%s</span>%s</div>'
                     '<h2><a href="%s" target="_blank" rel="noopener">%s</a></h2>'
                     '<div class="summary">%s</div></div>') % (
                badge(it.get("category")), pub, days, esc(it.get("url", "")), esc(it.get("title", "")),
                esc(it.get("summary", ""))[:220])
    if not cal_items:
        body += '<div class="empty">暂无会议类条目</div>'
    write_page("calendar.html", page("会议日历", body, "calendar.html"))

    # ---------- 日报归档 ----------
    archive_html = "".join('<a href="daily.html?d=%s">%s</a>' % (d, d) for d in sorted(dailies.keys(), reverse=True))
    latest = dailies.get(today) or (list(dailies.values())[-1] if dailies else None)
    body = ('<h1 class="page">日报归档</h1><div class="subtitle">每日 08:00 生成 · 精选当日高分资讯</div>'
            '<div class="archives">%s</div>' % (archive_html or "<span>暂无</span>"))
    if latest:
        body += ('<div class="daily-head"><h2>%s</h2><span class="subtitle">%s 生成</span></div>' % (
            esc(latest["title"]), esc(latest.get("generated_at", ""))))
        body += "".join(card_html(it) for it in latest["items"])
    else:
        body += '<div class="empty">暂无日报，运行 pipeline 后生成</div>'
    write_page("daily.html", page("日报归档", body, "daily.html"))

    # ---------- RSS ----------
    build_rss(items)

    # ---------- 索引站内搜索提示 ----------
    print("站点已生成于 %s （%d 条资讯）" % (SITE_DIR, len(items)))

def load_dailies():
    out = {}
    if os.path.isdir(DAILY_DIR):
        for fn in sorted(os.listdir(DAILY_DIR)):
            if fn.endswith(".json"):
                try:
                    with open(os.path.join(DAILY_DIR, fn), encoding="utf-8") as f:
                        out[fn[:-5]] = json.load(f)
                except Exception:
                    continue
    return out

def build_rss(items):
    items = sorted(items, key=lambda x: x.get("published_at") or x.get("discovered_at", "")[:10], reverse=True)[:50]
    pub = time.strftime("%a, %d %b %Y %H:%M:%S +0800", time.localtime())
    title = "语闻 LingBrief — 语言学资讯"
    items_xml = ""
    for it in items:
        desc = esc(it.get("summary", ""))
        items_xml += ('<item><title><![CDATA[%s]]></title><link>%s</link>'
                      '<description><![CDATA[%s\n推荐理由:%s]]></description>'
                      '<category>%s</category><guid isPermaLink="false">%s</guid>'
                      '<pubDate>%s</pubDate></item>') % (
            it.get("title", ""), esc(it.get("url", "")), desc, it.get("reason", ""),
            CATS.get(it.get("category"), ("", ""))[0], it.get("id", ""), pub)
    rss = ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
           '<title>%s</title><link>%s</link><description>语言学资讯每日精选</description>'
           '<language>zh-cn</language><lastBuildDate>%s</lastBuildDate>%s</channel></rss>'
           ) % (title, "https://example.com/", pub, items_xml)
    with open(os.path.join(SITE_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss)
    print("RSS: %d 条 → site/rss.xml" % len(items))

def write_page(name, content):
    with open(os.path.join(SITE_DIR, name), "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    build()
