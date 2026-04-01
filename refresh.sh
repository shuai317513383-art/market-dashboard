#!/bin/bash
# 刷新看板数据并推送到GitHub
cd "$(dirname "$0")"
echo "正在抓取最新数据..."
python3 gen_dash_v3.py
echo "正在生成HTML..."
python3 build_final.py
mv market_v7.html index.html
echo "正在提交更新..."
git add -A
git commit -m "更新 $(date '+%m/%d %H:%M')" 2>/dev/null || echo "无需更新"
git push origin main 2>&1 | tail -3
echo "完成!"
