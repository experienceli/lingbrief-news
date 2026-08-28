# 语闻 LingBrief — 语言学资讯聚合站

借鉴 AIHOT（aihot.virxact.com）思路的中文语言学资讯聚合站：
**信源抓取 → 去重 → LLM 中文摘要+打分+推荐理由 → 每日 08:00 日报 → 静态站点 + RSS**。
零第三方依赖（仅 Python 3 标准库），托管零成本（GitHub Pages 免费托管 + Actions 每日自动更新）。

## 快速开始（本机预览）

```bash
./run.sh                          # 一键：抓取→摘要→生成 site/
python3 -m http.server 8000 --directory site   # 本地预览
```

## 栏目

| 页面 | 说明 |
|---|---|
| 首页·精选 | 按日期分组的高分条目时间线（分类徽章/评分/来源/推荐理由） |
| 全部动态 | 全量资讯 + 8 类筛选 + 标题/来源/摘要搜索 |
| 热点榜 | 近 14 天主题热度：按 config.json 的 topics 词表统计（提及数 × 信源数） |
| 每日日报 | 每日 08:00 自动生成的高分精选集 + 历史归档 |
| 会议日历 | 会议/讲座/政策按时间排列，自动提取征稿截止日期并倒计时 |
| 期刊速递 | 期刊论文动态 + 新书出版信息 |
| 关于 | 信源清单、栏目说明、版权合规声明 |
| rss.xml | 最新 50 条 RSS（可订阅） |

## 当前信源（config.json 可随时增删）

1. 中国社科院语言研究所·学术活动 / 国内会议 / 要闻（ling.cass.cn，抓取+详情页解析）
2. 教育部语言文字信息管理司·通知公告（moe.gov.cn）
3. LINGUIST List（国际：Jobs / Confs / Calls，专用解析，自动分类）
4. 商务印书馆·新书（关键词过滤，只收语言学相关书目）
5. 北京大学中国语言文学系·公告（链接正则防噪 + 关键词过滤）

## 部署到 GitHub Pages（已完成，含每日自动更新）

项目已配好 GitHub Actions：**推送代码即自动重建部署**（push 触发 + 每天北京 08:00 定时触发）。
日常更新流程：

1. 在电脑上改 config.json（加信源）/ 改 src/ 下代码
2. 打开 GitHub Desktop → 左下角 **Push origin**（点一下即可）
3. 等 2~5 分钟，Actions 自动跑完，网站自动更新 —— 无需手动操作

> 仓库设置：Settings → Pages → Deploy from a branch → **gh-pages**（已配好；首次需在 Actions 里手动 Run workflow 一次生成 gh-pages 分支）。
> LLM：Settings → Secrets and variables → Actions → 添加 `DEEPSEEK_API_KEY`（可选，不配自动降级为规则摘要）。

## 目录结构

```
语言学资讯站/
├── config.json                  # 信源 + 主题词表（日常主要改这里）
├── run.sh                       # 一键运行
├── 部署操作手册.md               # 面向新手的界面级部署说明
├── .github/workflows/update.yml # 每日调度 + push 触发自动更新部署
├── src/
│   ├── fetch.py                 # RSS/机构站列表/linglist 三种抓取器
│   ├── llm.py                   # DeepSeek 摘要打分（无 key 自动降级）
│   ├── pipeline.py              # 抓取→去重→摘要→日报
│   └── build_site.py            # 生成 7 个页面 + RSS
├── data/                        # items.json + dailies/（随仓库持久化）
└── site/                        # 生成产物（部署到 gh-pages）
```

## 新增信源（config.json）

- **RSS 型**（期刊 eTOC 等）：`{"type":"rss","url":"...feed.xml","default_category":"journal"}`
- **网页列表型**：`{"type":"linklist","url":"列表页","path_hint":[".html"],"default_category":"news"}`
  - `path_hint`：只收含这些子串的链接；`link_pattern`：链接正则（防收导航页）
  - `include_keywords`：标题须命中任一词才收录（可选）；`category_hint`：按 URL 归类
- **LINGUIST List**：`{"type":"linglist","url":"https://linguistlist.org/issues/"}`（专用解析）

## 主题词表（热点榜）

config.json 的 `topics`：每个主题一组关键词（中文词直接匹配；英文词自动按字母边界匹配，
避免 "AI" 误中 "Explorations"）。修改后 push 即生效。

## 故障排查

- **某源抓取失败**：日志有 [warn] 即跳过该源继续，数据不丢（data/ 在仓库持久化）
- **热点榜条目少**：主题须 ≥2 条命中才上榜，数据积累后自然充实
- **LLM 一直降级**：检查 Secret 名是否为 `DEEPSEEK_API_KEY`

## 合规注意

- 本站仅做**摘要 + 链接**，不转载全文；摘要自撰并注明来源，供学界个人非商业使用
- 定位"学术信息资源"，避免"新闻"表述；大陆服务器托管才需 ICP 备案
