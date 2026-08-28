# -*- coding: utf-8 -*-
"""抓取模块：通用 RSS/Atom 解析 + 中文机构网站链接列表抓取。仅用标准库。"""
import json, re, time, gzip, io, hashlib
import urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
TIMEOUT = 25

def http_get(url, timeout=TIMEOUT, headers=None):
    """GET 返回解码后的文本（自动处理 gzip / 常见中文编码）"""
    h = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml,*/*;q=0.8",
         "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        ctype = (resp.headers.get("Content-Type") or "").lower()
        ctype_enc = ""
        m = re.search(r"charset=([\w-]+)", ctype)
        if m:
            ctype_enc = m.group(1).lower()
        return decode_bytes(raw, ctype_enc), raw

def decode_bytes(raw, hint=""):
    """字节→文本：优先响应头/meta 声明，再试 utf-8 / gb18030"""
    for enc in ([hint] if hint and hint not in ("utf-8", "utf8") else []):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    if raw[:2] in (b"\x1f\x8b",):
        try: raw = gzip.decompress(raw)
        except Exception: pass
    text = None
    for enc in ("utf-8", "gb18030"):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        text = raw.decode("utf-8", errors="replace")
    # meta 声明修正
    m = re.search(r'charset=["\']?([\w-]+)', text[:2000], re.I)
    if m and m.group(1).lower() not in ("utf-8", "utf8"):
        try:
            text = raw.decode(m.group(1).lower())
        except Exception:
            pass
    return text

def strip_tags(html_text):
    """粗暴去标签，得到可读文本"""
    t = re.sub(r"<script.*?</script>", " ", html_text, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html_unescape(t)
    return re.sub(r"\s+", " ", t).strip()

def html_unescape(t):
    import html as _h
    return _h.unescape(t)

def normalize_url(base, href):
    if not href or href.startswith("javascript:"):
        return None
    href = href.split("#")[0]
    return urllib.parse.urljoin(base, href)

def parse_rss(xml_text, source):
    """标准 RSS 2.0 / Atom 解析 → item 列表（标题/链接/摘要/日期）"""
    items = []
    try:
        root = ET.fromstring(xml_text.encode("utf-8"))
    except Exception:
        return items
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    def local(tag):
        return tag.split("}")[-1]
    # find channel items
    entries = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    for e in entries:
        get = lambda t: (e.findtext(t) or e.findtext("{http://www.w3.org/2005/Atom}" + t) or "").strip()
        try:
            title = get("title")
            link = e.find("link")
            if link is not None:
                link = link.get("href") or (link.text or "")
            elif e.findtext("guid"):
                link = get("guid")
            link = (link or "").strip()
            if not title or not link:
                continue
            desc = get("description") or get("summary")
            pub = get("pubDate") or get("published") or get("updated")
            items.append({"title": title, "url": link, "raw_text": strip_tags(desc)[:600], "published_raw": pub})
        except Exception:
            continue
    return items

def parse_link_list(html_text, base_url, path_hints, source, link_pattern=None):
    """通用中文机构站列表页解析：提取详情页链接（多为 tYYYYMMDD_xxx.html 形式或通配）。返回按页序的 [{url,title,brief}]"""
    found = []
    pattern = re.compile(r'<a[^>]+href="([^"]+.(?:html|htm|shtml))"[^>]*>\s*<[^>]+>\s*([^<]{6,})', re.I)
    # 兼容多级结构：直接全局提 href，再用最近标题匹配
    anchors = re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>[^<]*?(?:<[^>]+>)*\s*([^<]{6,})?', html_text, re.I)
    seen = set()
    for m in anchors:
        href = m.group(1)
        if not re.search(r"\.(?:html|htm|shtml)", href, re.I):
            continue
        if link_pattern and not re.search(link_pattern, href):
            continue
        if not any(h in href for h in (path_hints or [".html"])):
            continue
        url = normalize_url(base_url, href)
        if not url:
            continue
        if re.search(r"\.(html|htm|shtml)$", url.split("?")[0], re.I):
            title = (m.group(2) or "").strip()
            # 图片/空锚点先出现时不得占用 URL，否则带标题的锚点会被误判重复
            if title and url not in seen:
                seen.add(url)
                found.append({"url": url, "title": title})
    # 去重保序
    out, seen2 = [], set()
    for f in found:
        if f["url"] not in seen2:
            seen2.add(f["url"])
            out.append(f)
    return out

def extract_detail(html_text, url):
    """详情页提取：标题 + 正文摘要段"""
    title = ""
    m = re.search(r'<title>(.*?)</title>', html_text, flags=re.S | re.I)
    if m:
        title = strip_tags(m.group(1)).split("_")[0].strip()
    # 正文 <p>（去掉脚本样式后，取前几个有实质内容的段）
    body = re.sub(r"<script.*?</script>", " ", html_text, flags=re.S | re.I)
    body = re.sub(r"<style.*?</style>", " ", body, flags=re.S | re.I)
    paras = re.findall(r"<p[^>]*>(.*?)</p>", body, flags=re.S | re.I)
    texts = []
    for p in paras:
        t = strip_tags(p)
        if len(t) >= 20 and "版权所有" not in t and "网站地图" not in t:
            texts.append(t)
        if len(texts) >= 3:
            break
    summary = " ".join(texts[:2])[:600]
    return title, summary

class Fetcher:
    def __init__(self, config):
        self.cfg = config.get("fetch", {})
        self.ua = self.cfg.get("user_agent", UA)
        self.timeout = self.cfg.get("timeout", TIMEOUT)
        self.delay = self.cfg.get("delay_seconds", 1.0)

    def fetch_source(self, s):
        """返回 [{title,url,raw_text,published_raw,source,source_id,weight,category}]"""
        out = []
        url = s["url"]
        if s["type"] == "rss":
            try:
                text, _ = http_get(url, self.timeout)
                for it in parse_rss(text, s):
                    cat = infer_category(it["url"], s)
                    out.append({**it, "source": s["name"], "source_id": s["id"],
                                "weight": s.get("weight", 5), "category": cat})
            except Exception as e:
                print("  [warn] rss fail %s: %s" % (url, e))
        elif s["type"] == "linglist":
            try:
                got = fetch_linglist(url, s, self.delay, self.timeout,
                                     self.cfg.get("max_details_per_source", 12))
                out.extend(got)
            except Exception as e:
                print("  [warn] linglist fail %s: %s" % (url, e))
        elif s["type"] == "linklist":
            try:
                time.sleep(self.delay)
                text, _ = http_get(url, self.timeout)
                links = parse_link_list(text, url, s.get("path_hint") or [".html"], s, s.get("link_pattern"))
                maxdet = self.cfg.get("max_details_per_source", 12)
                for l in links[:maxdet]:
                    if not match_include(l["title"], s):
                        continue
                    cat = infer_category(l["url"], s)
                    try:
                        time.sleep(self.delay)
                        dtext, _ = http_get(l["url"], self.timeout)
                        title, summary = extract_detail(dtext, l["url"])
                        if not title:
                            title = l["title"]
                        out.append({"title": title[:120], "url": l["url"], "raw_text": summary,
                                    "published_raw": extract_date_from_url(l["url"]),
                                    "source": s["name"], "source_id": s["id"],
                                    "weight": s.get("weight", 5), "category": cat})
                    except Exception as e:
                        print("  [warn] detail fail %s: %s" % (l["url"], e))
            except Exception as e:
                print("  [warn] list fail %s: %s" % (url, e))
        return out

def infer_category(url, src):
    for cat, subs in (src.get("category_hint") or {}).items():
        if any(sub and sub in url for sub in subs) if subs else False:
            return cat
    return src.get("default_category", "news")

def extract_date_from_url(url):
    m = re.search(r"t(\d{8})_", url)
    if m:
        d = m.group(1)
        return "%s-%s-%s" % (d[:4], d[4:6], d[6:8])
    return ""

LINGLIST_PREFIX_CAT = {
    "Jobs": "job", "Confs": "conference", "Calls": "conference",
    "Books": "book", "TOC": "journal", "Journals": "journal",
    "Announcements": "news", "Support": "news", "Discussion": "news",
}

def match_include(title, src):
    """可选的关键词过滤：配置 include_keywords 时，标题须命中其一才保留"""
    kws = src.get("include_keywords") or []
    if not kws:
        return True
    return any(k in title for k in kws)

def fetch_linglist(list_url, source, delay, timeout, max_details):
    """LINGUIST List 列表页 /issues/ → 每期详情页。标题前缀 Jobs/Confs/Calls
    决定分类；详情页抓正文与英文日期。"""
    out = []
    text, _ = http_get(list_url, timeout)
    seen = set()
    for m in re.finditer(r'<a[^>]+href="(/issues/\d+/\d+/)"[^>]*>(.*?)</a>', text, flags=re.S | re.I):
        href = m.group(1)
        if href in seen:
            continue
        raw_title = strip_tags(m.group(2)).strip()
        if len(raw_title) < 10 or not raw_title.startswith(("Jobs", "Confs", "Calls", "Books", "TOC", "Announcements", "Support", "Discussion")):
            continue
        seen.add(href)
        prefix = raw_title.split(":")[0].strip()
        title = re.sub(r"^(?:Confs|Jobs|Calls|Books|TOC|Announcements|Support|Discussion):\s*", "", raw_title)
        title = re.sub(r"^(Confs|Jobs|Calls|Books|TOC|Announcements|Support|Discussion):\s*\1:\s*", "", title)
        if not title or len(title) < 8:
            continue
        if len(out) >= max_details:
            break
        try:
            time.sleep(delay)
            dtext, _ = http_get(urllib.parse.urljoin(list_url, href), timeout)
            title2, body_text = extract_linglist_detail(dtext)
            cat = LINGLIST_PREFIX_CAT.get(prefix, source.get("default_category", "international"))
            out.append({
                "title": (title2 or title)[:140], "url": urllib.parse.urljoin(list_url, href),
                "raw_text": body_text[:900],
                "published_raw": parse_ll_date(body_text),
                "source": source["name"], "source_id": source["id"],
                "weight": source.get("weight", 6), "category": cat,
            })
        except Exception as e:
            print("  [warn] linglist detail fail %s: %s" % (href, e))
    return out

def extract_linglist_detail(html_text):
    """LINGUIST List 详情页：标题（og:title/页内标题）+ 正文前两段"""
    title = ""
    m = re.search(r'property="og:title" content="([^"]+)"', html_text)
    if m:
        title = m.group(1).strip()
    if not title:
        m = re.search(r"<title>(.*?)</title>", html_text, flags=re.S | re.I)
        if m:
            title = strip_tags(m.group(1)).strip()
    title = re.sub(r"^LINGUIST List \d+\.\d+\s*", "", title)
    title = re.sub(r"^(Confs|Jobs|Calls|Books|TOC|Announcements|Support|Discussion):\s*\1:\s*", "", title)
    body = re.sub(r"<script.*?</script>", " ", html_text, flags=re.S | re.I)
    body = re.sub(r"<style.*?</style>", " ", body, flags=re.S | re.I)
    paras = [strip_tags(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", body, flags=re.S | re.I)]
    paras = [p for p in paras if len(p) >= 80]
    summary = " ".join(paras[:2])[:900]
    return title, summary

MONTHS_EN = {"Jan":"01","Feb":"02","Mar":"03","Apr":"04","May":"05","Jun":"06",
             "Jul":"07","Aug":"08","Sep":"09","Oct":"10","Nov":"11","Dec":"12"}

def parse_ll_date(text):
    """从 'Fri Aug 28 2026' 形式解析发布日期"""
    m = re.search(r"([A-Z][a-z]{2})\s+([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{4})", text)
    if m and m.group(2) in MONTHS_EN:
        return "%s-%s-%s" % (m.group(4), MONTHS_EN[m.group(2)], m.group(3).zfill(2))
    return ""


def item_id(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
