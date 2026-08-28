# -*- coding: utf-8 -*-
"""静态站点生成器 v2（Aihot 风格）：首页精选时间线 / 全部动态 / 热点榜 / 每日日报 / 会议日历 / 期刊速递 / 关于。零依赖。"""
import json, os, sys, html, time, re
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

DATA_DIR = os.path.join(ROOT, "data")
DAILY_DIR = os.path.join(DATA_DIR, "dailies")
SITE_DIR = os.path.join(ROOT, "site")
CONFIG_PATH = os.path.join(ROOT, "config.json")

CATS = {
    "conference": ("会议征稿", "#e05d3f"),
    "lecture": ("讲座交流", "#8f6fd8"),
    "policy": ("政策项目", "#2f7fd8"),
    "journal": ("期刊论文", "#12957f"),
    "news": ("学界动态", "#c8962e"),
    "job": ("岗位招聘", "#5d9e3f"),
    "book": ("新书出版", "#c2528f"),
    "international": ("国际视野", "#5b6ee1"),
}
NAV = [("index.html", "首页·精选"), ("all.html", "全部动态"), ("hot.html", "热点榜"),
       ("daily.html", "每日日报"), ("calendar.html", "会议日历"), ("journal.html", "期刊速递"),
       ("about.html", "关于")]

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#14181f;--sub:#616a75;--line:#e6e9ee;--accent:#e05d3f;--accent-soft:#fdf1ec}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--ink);line-height:1.7}
a{color:inherit;text-decoration:none}
.wrap{max-width:880px;margin:0 auto;padding:0 16px}
header.site{position:sticky;top:0;z-index:10;background:#fff;border-bottom:1px solid var(--line)}
header.site .wrap{display:flex;align-items:center;gap:12px;padding:12px 16px;flex-wrap:wrap}
.logo{font-weight:800;font-size:17px;letter-spacing:.5px}
.logo em{font-style:normal;color:var(--accent)}
nav{display:flex;gap:2px;margin-left:auto;flex-wrap:wrap}
nav a{padding:5px 11px;border-radius:8px;font-size:13.5px;color:var(--sub)}
nav a.active,nav a:hover{background:#f1f3f6;color:var(--ink);font-weight:600}
.today{font-size:12.5px;color:var(--sub)}
main{padding:26px 0 60px}
h1.page{font-size:21px;font-weight:800}
.subtitle{color:var(--sub);font-size:13px;margin:4px 0 18px}
.badge{display:inline-block;font-size:11px;padding:2px 8px;border-radius:999px;color:#fff;vertical-align:middle}
.src-pill{display:inline-block;font-size:11.5px;background:#f1f3f5;color:#5a6472;padding:2px 8px;border-radius:6px}
.day-head{display:flex;align-items:center;gap:10px;margin:26px 0 12px;color:var(--sub);font-size:13.5px;font-weight:600}
.day-head::after{content:"";flex:1;height:1px;background:var(--line)}
.day-head .n{font-weight:400}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:12px;transition:box-shadow .15s}
.card:hover{box-shadow:0 4px 14px rgba(20,24,31,.07)}
.card .meta{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--sub);margin-bottom:6px;flex-wrap:wrap}
.card h3{font-size:15.5px;font-weight:700;margin-bottom:7px}
.card h3 a:hover{color:var(--accent)}
.card .summary{font-size:13.8px;color:#3c4552}
.card .reason{margin-top:9px;font-size:12.8px;background:var(--accent-soft);border-left:3px solid var(--accent);padding:7px 10px;border-radius:0 8px 8px 0;color:#8a4a35}
.card .reason b{color:var(--accent);margin-right:4px}
.card .foot{margin-top:9px;display:flex;gap:12px;font-size:12px;color:var(--sub);align-items:center;flex-wrap:wrap}
.foot a.link{color:#2f6fd0}
.score{font-weight:800;color:var(--accent)}
.score.hi{color:#d43c1e}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 18px}
.filters button{border:1px solid var(--line);background:#fff;border-radius:999px;padding:5px 14px;font-size:13px;cursor:pointer;color:var(--sub)}
.filters button.active{background:var(--ink);color:#fff;border-color:var(--ink)}
.search{width:100%;padding:9px 14px;border:1px solid var(--line);border-radius:10px;font-size:14px;margin-bottom:14px}
input.search:focus{outline:2px solid #d4dbe4}
.rank{display:flex;gap:14px;align-items:flex-start;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:12px}
.rank .num{font-size:22px;font-weight:800;min-width:34px;color:var(--accent)}
.rank .num.t2{color:#8a5a2c}
.rank .num.t3{color:#5a6472}
.rank h3{font-size:15.5px;font-weight:700}
.rank .sub{font-size:12px;color:var(--sub);margin:3px 0 8px}
.heatbar{height:5px;background:#eef1f4;border-radius:3px;margin-bottom:10px;overflow:hidden}
.heatbar i{display:block;height:100%;background:linear-gradient(90deg,#f0a58e,var(--accent));border-radius:3px}
.rank ul{list-style:none}
.rank li{font-size:13px;padding:3px 0;color:#3c4552}
.rank li a:hover{color:var(--accent)}
.rank li .rs{color:var(--sub);font-size:12px;margin-left:6px}
.cal-month{font-weight:800;margin:22px 0 10px}
.dcount{font-size:12px;color:var(--accent);font-weight:600}
.tag{display:inline-block;font-size:10.5px;background:#eef1f5;color:#5a6472;border-radius:4px;padding:1px 6px;margin:0 2px 2px 0}
.empty{padding:40px;text-align:center;color:var(--sub)}
.daily-head{display:flex;gap:14px;align-items:baseline;margin-bottom:16px;flex-wrap:wrap}
.archives{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin-bottom:20px}
.archives a{display:inline-block;margin:2px 8px 2px 0;font-size:13px;color:var(--sub)}
.archives a:hover{color:var(--accent)}
.about h2{font-size:16px;font-weight:700;margin:20px 0 8px}
.about p,.about li{font-size:14px;color:#3c4552;margin-bottom:6px}
footer.site{border-top:1px solid var(--line);padding:20px 0;color:var(--sub);font-size:12px;text-align:center}
@media(max-width:600px){.card{padding:13px;border-radius:10px}.rank{padding:13px}.today{display:none}}
"""

def esc(s):
    return html.escape(str(s or ""), quote=True)

def badge(cat):
    label, color = CATS.get(cat, (cat, "#999"))
    return '<span class="badge" style="background:%s">%s</span>' % (color, esc(label))

def score_class(score):
    return "score hi" if score >= 70 else "score"

def card_html(it, show_day=False):
    cat = it.get("category", "news")
    pub = it.get("published_at") or ""
    score = it.get("score", 0)
    src = esc(it.get("source", ""))
    reason = esc((it.get("reason") or "")[:130])
    summary = esc(it.get("summary", "")) or esc((it.get("raw_text") or "")[:120])
    title = esc(it.get("title", ""))
    url = esc(it.get("url", ""))
    return ('<article class="card"><div class="meta">%s<span class="%s">%s</span>'
            '<span class="src-pill">%s</span><span>%s</span></div>'
            '<h3><a href="%s" target="_blank" rel="noopener">%s</a></h3>'
            '<div class="summary">%s</div>'
            '<div class="reason"><b>推荐理由</b>%s</div>'
            '<div class="foot"><span>来源：%s</span><a class="link" href="%s" target="_blank" rel="noopener">阅读原文 ↗</a></div>'
            '</article>') % (badge(cat), score_class(score), score, src, pub,
                            url, title, summary, reason, src, url)

WEEK = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

def fmt_day(iso):
    try:
        d = datetime.strptime(iso, "%Y-%m-%d")
        return "%d月%d日 · %s" % (d.month, d.day, WEEK[d.weekday()])
    except Exception:
        return iso

def item_date(it):
    return it.get("published_at") or it.get("discovered_at", "")[:10] or ""

def load_items():
    p = os.path.join(DATA_DIR, "items.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return []

def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)

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

def page(title, body, active, extra_js=""):
    today = datetime.now().strftime("%Y年%m月%d日")
    nav_html = "".join('<a href="%s"%s>%s</a>' % (h, ' class="active"' if h == active else "", t) for h, t in NAV)
    footer_note = ("语闻 LingBrief — 语言学资讯聚合（原型，非官方）· 内容版权归原来源所有，本站仅作摘要与链接 · "
                   "每天 08:00 自动更新 · <a href='about.html' style='color:#2f6fd0'>关于与信源列表</a>")
    return ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="description" content="语言学资讯每日精选：期刊、会议、讲座、政策、招聘、新书一站式聚合">'
            '<title>%s · 语闻 LingBrief</title><style>%s</style></head><body>'
            '<header class="site"><div class="wrap"><div class="logo">语闻<em> LingBrief</em></div>'
            '%s<div class="today">%s</div></div></header>'
            '<main><div class="wrap">%s</div></main>'
            '<footer class="site"><div class="wrap">%s</div></footer>%s</body></html>'
            ) % (esc(title), CSS, nav_html, today, body, footer_note, extra_js)

def write_page(name, content):
    with open(os.path.join(SITE_DIR, name), "w", encoding="utf-8") as f:
        f.write(content)

# ---------------- 主题热度（热点榜） ----------------
def topic_hit(word, hay):
    """主题词匹配：英文/数字词用字母边界，避免 'AI' 误中 'Explorations'；中文词直接包含"""
    if re.search(r"[a-zA-Z0-9]", word):
        return re.search(r"(?<![a-zA-Z0-9])" + re.escape(word) + r"(?![a-zA-Z0-9])", hay, re.I) is not None
    return word.lower() in hay.lower()

def compute_topics(items, topics_cfg, days=14):
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = [it for it in items if (item_date(it) >= cutoff or not item_date(it))]
    recs = []
    for topic, words in topics_cfg.items():
        matched = []
        for it in recent:
            hay = ((it.get("title") or "") + " " + (it.get("summary") or ""))
            if any(topic_hit(w, hay) for w in words):
                matched.append(it)
        if len(matched) >= 2:
            srcs = len({it.get("source") for it in matched})
            avg = sum(it.get("score", 0) for it in matched) / len(matched)
            recs.append({"topic": topic, "items": matched, "sources": srcs,
                         "count": len(matched), "avg": round(avg, 1)})
    recs.sort(key=lambda r: (-r["count"], -r["sources"], -r["avg"]))
    return recs[:10]

def extract_deadline(it):
    """从标题/摘要里找截止日期（原型版：正则匹配 中文日期）"""
    hay = (it.get("title") or "") + " " + (it.get("summary") or "")
    if not re.search(r"(截止|截稿|提交|投稿|征稿.{0,20}日)", hay):
        return ""
    pats = [r"(20d{2})年(d{1,2})月(d{1,2})日", r"(d{1,2})月(d{1,2})日"]
    year = datetime.now().year
    for pat in pats:
        m = re.search(pat, hay)
        if m:
            if len(m.groups()) == 3:
                yy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
            else:
                mm, dd = int(m.group(1)), int(m.group(2))
                yy = year
                if yy < 2000 or yy > 2100:
                    yy = year
            try:
                dt = datetime(yy, mm, dd)
                diff = (dt - datetime.now()).days
                if diff >= -3:
                    return "截止 %d-%02d-%02d（%d 天后）" % (yy, mm, dd, diff)
            except Exception:
                continue
    return ""

# ---------------- 各页面 ----------------
def build_index(items):
    groups = {}
    for it in items:
        groups.setdefault(item_date(it), []).append(it)
    date_keys = sorted([d for d in groups if d], reverse=True)
    body = '<h1 class="page">今日精选</h1><div class="subtitle">%s · 共 %d 条 · 按发布时间分组，高分优先</div>' % (
        datetime.now().strftime("%Y年%m月%d日"), len(items))
    for d in date_keys:
        body += '<div class="day-head">%s<span class="n">%d 条</span></div>' % (fmt_day(d), len(groups[d]))
        body += "".join(card_html(it) for it in
                        sorted(groups[d], key=lambda x: -x.get("score", 0)))
    write_page("index.html", page("今日精选", body, "index.html"))

def build_all(items):
    pills = '<div class="filters"><button data-cat="" class="active">全部</button>' + "".join(
        '<button data-cat="%s">%s</button>' % (k, esc(v[0])) for k, v in CATS.items()) + "</div>"
    items_json = json.dumps(items, ensure_ascii=False)
    cats_json = json.dumps(CATS, ensure_ascii=False)
    body = ('<h1 class="page">全部动态</h1><div class="subtitle">%d 条 · 支持分类与关键词筛选 · 点击标题阅读原文</div>'
            '<input class="search" id="q" placeholder="搜索标题 / 来源 / 摘要…">' % len(items))
    body += pills + '<div id="list">' + "".join(card_html(it) for it in items) + "</div>"
    js = """<script>
var CATS=%s;var ITEMS=%s;var cat='',q='';
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(m){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]});}
function bd(c){var m=CATS[c]||[c,'#999'];return '<span class="badge" style="background:'+m[1]+'">'+esc(m[0])+'</span>';}
function card(i){return '<article class="card"><div class="meta">'+bd(i.category)+'<span class="score">'+i.score+'</span><span class="src-pill">'+esc(i.source)+'</span><span>'+esc(i.published_at||'')+'</span></div><h3><a href="'+esc(i.url)+'" target="_blank">'+esc(i.title)+'</a></h3><div class="summary">'+esc(i.summary||'')+'</div><div class="reason"><b>推荐理由</b>'+esc(i.reason||'')+'</div><div class="foot"><span>来源：'+esc(i.source)+'</span><a class="link" href="'+esc(i.url)+'" target="_blank">阅读原文 ↗</a></div></article>';}
function render(){var out=ITEMS.filter(function(i){var okC=!cat||i.category===cat;var okQ=!q||(i.title+' '+i.source+' '+(i.summary||'')).toLowerCase().indexOf(q.toLowerCase())>=0;return okC&&okQ;});
document.getElementById('list').innerHTML=out.length?out.map(card).join(''):'<div class="empty">没有匹配的条目</div>';
document.querySelectorAll('.filters button').forEach(function(b){b.classList.toggle('active',b.dataset.cat===cat);});}
document.querySelectorAll('.filters button').forEach(function(b){b.onclick=function(){cat=b.dataset.cat;render();};});
document.getElementById('q').oninput=function(e){q=e.target.value;render();};render();
</script>""" % (cats_json, items_json)
    write_page("all.html", page("全部动态", body, "all.html", js))

def build_hot(items, cfg):
    recs = compute_topics(items, cfg.get("topics", {}))
    body = ('<h1 class="page">热点榜</h1><div class="subtitle">近 14 天 · 按主题关键词自动统计（提及数 × 信源数），原型版</div>')
    if not recs:
        body += '<div class="empty">暂无热点数据（条目积累后自动出现）</div>'
    maxc = max((r["count"] for r in recs), default=1)
    for idx, r in enumerate(recs, 1):
        num_cls = "num" + ("" if idx == 1 else " t2" if idx == 2 else " t3" if idx == 3 else "")
        li = "".join('<li><a href="%s" target="_blank">%s</a><span class="rs">%s · %s</span></li>' % (
            esc(it.get("url", "")), esc(it.get("title", ""))[:60], esc(it.get("source", "")), it.get("score", 0))
            for it in r["items"][:5])
        body += ('<div class="rank"><div class="%s">%d</div><div style="flex:1">'
                 '<h3>%s</h3><div class="sub">%d 条资讯 · %d 个来源 · 均分 %.1f</div>'
                 '<div class="heatbar"><i style="width:%d%%"></i></div><ul>%s</ul></div></div>'
                 ) % (num_cls, idx, esc(r["topic"]), r["count"], r["sources"], r["avg"],
                      max(8, int(r["count"] / maxc * 100)), li)
    write_page("hot.html", page("热点榜", body, "hot.html"))

def build_daily(items, dailies):
    today = datetime.now().strftime("%Y-%m-%d")
    archive_html = "".join('<a href="daily.html?d=%s">%s</a>' % (d, d)
                           for d in sorted(dailies.keys(), reverse=True))
    body = ('<h1 class="page">每日日报</h1><div class="subtitle">每日 08:00 自动生成 · 精选当日高分资讯</div>'
            '<div class="archives">%s</div>' % (archive_html or "<span>暂无</span>"))
    latest = dailies.get(today) or (list(dailies.values())[-1] if dailies else None)
    if latest:
        body += ('<div class="daily-head"><h2>%s</h2><span class="subtitle">%s 生成</span></div>'
                 % (esc(latest["title"]), esc(latest.get("generated_at", ""))))
        body += "".join(card_html(it) for it in latest["items"])
    else:
        body += '<div class="empty">暂无日报，运行 pipeline 后生成</div>'
    write_page("daily.html", page("每日日报", body, "daily.html"))

def build_calendar(items):
    cal_items = [it for it in items if it.get("category") in ("conference", "lecture", "policy", "job")]
    months = {}
    for it in cal_items:
        months.setdefault(item_date(it)[:7], []).append(it)
    body = ('<h1 class="page">会议 · 讲座 · 政策日历</h1>'
            '<div class="subtitle">%d 条相关信息，按时间倒序；含截止日期时自动标注"征稿中"徽标与倒计时</div>' % len(cal_items))
    for m in sorted(months.keys(), reverse=True):
        body += '<div class="cal-month">%s</div>' % m
        for it in sorted(months[m], key=lambda x: -x.get("score", 0)):
            dl = extract_deadline(it)
            dl_html = ('<span class="dcount">%s</span>' % e) if (e := dl) else ""
            body += ('<div class="card"><div class="meta">%s<span>%s</span>%s</div>'
                     '<h3><a href="%s" target="_blank" rel="noopener">%s</a></h3>'
                     '<div class="summary">%s</div></div>') % (
                badge(it.get("category")), item_date(it), dl_html, esc(it.get("url", "")),
                esc(it.get("title", "")), esc(it.get("summary", ""))[:200])
    if not cal_items:
        body += '<div class="empty">暂无会议类条目</div>'
    write_page("calendar.html", page("会议日历", body, "calendar.html"))

def build_journal(items, cfg):
    words = cfg.get("topics", {}).get("期刊动态", [])
    j_items = [it for it in items if it.get("category") == "journal"
               or any(topic_hit(w, (it.get("title") or "") + " " + (it.get("summary") or "")) for w in words)]
    b_items = [it for it in items if it.get("category") == "book"]
    body = '<h1 class="page">期刊速递</h1><div class="subtitle">期刊目录与论文动态 · 新书出版信息</div>'
    body += '<h2 style="font-size:16px;margin:4px 0 10px">期刊 · 论文</h2>'
    body += ("".join(card_html(it) for it in j_items[:15]) if j_items
             else '<div class="empty">暂无期刊类条目（LINGUIST List 的期刊目录、期刊官网目录等源接入后自动出现）</div>')
    body += '<h2 style="font-size:16px;margin:18px 0 10px">新书速递</h2>'
    body += ("".join(card_html(it) for it in b_items[:15]) if b_items
             else '<div class="empty">暂无新书条目</div>')
    write_page("journal.html", page("期刊速递", body, "journal.html"))

def build_about(cfg):
    srcs = cfg.get("sources", [])
    names = "".join("<li>%s<span class='tag'>%s</span><span class='tag'>%s</span></li>" %
                    (esc(s["name"]), esc(s["type"]), esc(s.get("default_category", ""))) for s in srcs if s.get("enabled"))
    body = ('<h1 class="page">关于本站</h1><div class="subtitle">语闻 LingBrief — 语言学资讯聚合（原型）</div>'
            '<div class="about">'
            '<h2>这是什么</h2>'
            '<p>每天自动抓取语言学相关机构、期刊、国际学术平台的信息，生成中文摘要、打分与"推荐理由"，'
            '每天 08:00 发布今日日报。信源抓取→去重→摘要→发布 全程自动，零人工运营。</p>'
            '<h2>当前信源（%d 个）</h2><ul>%s</ul>'
            '<p style="color:#616a75">在 config.json 中可随时增删信源：RSS 直接填 feed 地址；'
            '中文机构站填列表页 URL + path_hint；LINGUIST List 用专用类型。</p>'
            '<h2>栏目说明</h2>'
            '<p>今日精选：按日期分组的高分条目；全部动态：全量+筛选搜索；热点榜：近 14 天主题热度统计；'
            '每日日报：每日高分精选集；会议日历：会议/讲座/政策按时间排列并标注征稿截止；期刊速递：期刊论文与书目。</p>'
            '<h2>版权与合规</h2>'
            '<p>本站仅展示自撰中文摘要与原文链接，不转载全文；摘要基于公开信息，注明来源。供学界个人非商业使用。'
            '若内容涉及你的机构和版权，请联系修正或删除。</p>'
            '<h2>技术</h2>'
            '<p>Python（标准库）+ 静态站点 + GitHub Actions 每日定时任务；可选接入 DeepSeek 大模型提升摘要质量。'
            '零服务器、零数据库成本。</p>'
            '</div>') % (len([s for s in srcs if s.get("enabled")]), names)
    write_page("about.html", page("关于", body, "about.html"))

def build_rss(items):
    items = sorted(items, key=lambda x: item_date(x) or x.get("discovered_at", ""), reverse=True)[:50]
    pub = time.strftime("%a, %d %b %Y %H:%M:%S +0800", time.localtime())
    items_xml = ""
    for it in items:
        desc = esc(it.get("summary", ""))
        reason = esc(it.get("reason", ""))
        items_xml += ('<item><title><![CDATA[%s]]></title><link>%s</link>'
                      '<description><![CDATA[%s]]></description>'
                      '<category>%s</category><guid isPermaLink="false">%s</guid>'
                      '<pubDate>%s</pubDate></item>') % (
            it.get("title", ""), esc(it.get("url", "")),
            desc + chr(10) + "推荐理由:" + reason,
            CATS.get(it.get("category"), ("", ""))[0], it.get("id", ""), pub)
    rss = ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
           '<title>语闻 LingBrief — 语言学资讯</title><link>https://example.com/</link>'
           '<description>语言学资讯每日精选</description><language>zh-cn</language>'
           '<lastBuildDate>%s</lastBuildDate>%s</channel></rss>') % (pub, items_xml)
    with open(os.path.join(SITE_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss)

def build():
    os.makedirs(SITE_DIR, exist_ok=True)
    cfg = load_config()
    items = load_items()
    dailies = load_dailies()
    build_index(items)
    build_all(items)
    build_hot(items, cfg)
    build_daily(items, dailies)
    build_calendar(items)
    build_journal(items, cfg)
    build_about(cfg)
    build_rss(items)
    print("站点已生成于 %s (%d 条资讯, %d 期日报)" % (SITE_DIR, len(items), len(dailies)))

if __name__ == "__main__":
    build()
