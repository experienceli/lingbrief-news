# 语闻 LingBrief — 语言学资讯聚合站（原型）

借鉴 AIHOT（aihot.virxact.com）思路的中文语言学资讯聚合原型：
**信源抓取 → 去重 → LLM 中文摘要+打分+推荐理由 → 每日 08:00 日报 → 静态站点 + RSS**。
完全零第三方依赖（仅 Python 3 标准库），托管零成本（GitHub Pages 免费静态托管）。

## 快速开始（本机预览）

```bash
./run.sh                          # 一键：抓取→摘要→生成 site/
python3 -m http.server 8000 --directory site   # 本地预览
# 浏览器打开 http://localhost:8000
```

或分步：`python3 src/pipeline.py`（更新 data/items.json 与 data/dailies/）→ `python3 src/build_site.py`（重建 site/）。

## 目录结构

```
语言学资讯站/
├── config.json             # 信源配置（增删信源在这里）
├── run.sh                  # 一键运行
├── .github/workflows/update.yml   # GitHub Actions：每日自动抓取+部署
├── src/
│   ├── fetch.py            # 抓取：RSS/Atom + 中文机构站链接列表（自动进详情页取正文）
│   ├── llm.py              # 摘要打分：DeepSeek API（有 key 用 LLM，无 key 自动降级规则引擎）
│   ├── pipeline.py         # 主流程：抓取→去重→摘要→日报 JSON
│   └── build_site.py       # 生成静态站点 + RSS
├── data/                   # items.json 主库、dailies/*.json 每日日报（随仓库持久化）
└── site/                   # 生成产物（index/all/calendar/daily/rss.xml），部署到 gh-pages 分支
```

## 部署到 GitHub Pages（免费，含每日自动更新）

### 1. 推送仓库

```bash
git add . && git commit -m "init"
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

> 仓库建议 public（GitHub Pages 免费版要求 public；私有仓库需 Pro）。

### 2. 开启 Pages

仓库 Settings → **Pages** → Build and deployment → Source 选 **Deploy from a branch** → 分支选 **gh-pages** → 目录 **/(root)** → Save。

### 3. （强烈建议）配置 DeepSeek Key

Settings → **Secrets and variables → Actions** → New repository secret：
- Name: `DEEPSEEK_API_KEY`
- Value: `sk-xxx`

不配置也能跑（自动降级为规则摘要+启发式打分），但有了 key 才是完整版效果：AI 摘要 + 真实打分 + 一句话推荐理由。

### 4. 触发首次构建

**Actions** 页 → **daily-update** → **Run workflow**（右侧按钮）。或等每天 08:00（北京时间）自动执行。

### 5. 访问站点

```
https://<你的用户名>.github.io/<仓库名>/
```

### 工作流做了什么（.github/workflows/update.yml）

1. checkout 仓库（**data/ 随仓库持久化**，每天在旧数据上增量抓取）
2. 运行 `pipeline.py`（抓取 4+ 信源 → 去重 → 摘要打分）→ `build_site.py`（重建 site/）
3. 有新增数据则 commit + push 回 main（data/ 始终最新）
4. `peaceiris/actions-gh-pages` 把 site/ 发布到 gh-pages 分支 → GitHub Pages 自动上线
5. 全程无需服务器/数据库/费用；免费额度内每天一次绰绰有余

## 接入 LLM（本机手动跑时）

```bash
export DEEPSEEK_API_KEY=sk-xxx
./run.sh
```

未配置时自动降级为规则引擎（摘要=原文截断 + 模板推荐理由 + 启发式打分），原型依然可用。
换其他厂商：改 config.json 的 llm.api_base / model（OpenAI 兼容接口均可）。

## 数据模型（data/items.json 每条）

```json
{
  "id": "sha1(url)前16位", "url": "原文链接", "title": "标题",
  "source": "来源名（如 中国社科院语言研究所）", "category": "conference|lecture|policy|journal|news|job|book|international",
  "raw_text": "原文摘要片段", "summary": "LLM/规则中文摘要", "reason": "推荐理由",
  "score": 0-100, "published_at": "YYYY-MM-DD", "discovered_at": "ISO时间"
}
```

## 新增信源（config.json）

- **RSS 型**（国际期刊 eTOC、LINGUIST List 等）：`{"type":"rss","url":"https://.../feed.xml","default_category":"international"}`
- **网页列表型**：`{"type":"linklist","url":"http://.../xshd/","path_hint":[".html"],"default_category":"news"}`，会进详情页提取正文摘要
- `path_hint` 用于过滤链接（如 ["/huiyi/"] 只收会议链接）；`category_hint` 可按 URL 自动归类

## 定时更新（本机 crontab 备选）

```bash
crontab -e
# 每天 08:00 运行（GitHub Actions 不可用时的备选）
0 8 * * * cd /path/to/语言学资讯站 && ./run.sh >> run.log 2>&1
```

## 故障排查

- **留学站点抓取失败**：教育部 moe.gov.cn 对海外 IP 偶有拦截；GitHub Actions 跑在海外，部分源可能报 [warn] —— 管道会跳过失败源继续，数据不丢（data/ 在仓库里持久化）
- **日报为 0 条**：当天无高分新条目时会自动放宽到最近 7/90 天窗口，再兜底取最新 20 条
- **LLM 一直降级**：检查 Secret 是否添加到仓库（不是 Environment）且名字为 `DEEPSEEK_API_KEY`

## 后续路线（对齐 AIHOT 的进阶功能）

1. 会议征稿**截止日期**结构化提取 + 日历倒计时提醒
2. 邮件订阅（Resend/自有 SMTP）+ 微信公众号排版推送
3. API v1（/api/v1/items JSON）+ llms.txt（给 Agent 用）
4. 热点榜（多信源重复提及统计）→ 主题页
5. 部署大陆服务器 + ICP 备案后接入更多中文信源

## 合规注意

- 大陆服务器托管需 ICP 备案（lingpress.com 即死于未备案被拦）
- 本站仅做**摘要 + 链接**；摘要建议用自己的话 + 保留原文出处；全文转载需授权
- 定位"学术信息资源"，避免"新闻"表述
