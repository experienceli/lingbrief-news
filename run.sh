#!/usr/bin/env bash
# 语言学资讯聚合站 · 一键运行：抓取 -> 摘要 -> 生成静态站点
set -e
cd "$(dirname "$0")"
python3 src/pipeline.py && python3 src/build_site.py
echo "完成。站点在 site/ 目录，可本地预览: python3 -m http.server 8000 --directory site"

