#!/bin/zsh
# 手動上線：叫 GitHub 立刻跑一次發布流程（從 Drive 抓最新檔）
set -e
cd "$(dirname "$0")"
gh workflow run publish.yml
sleep 3
gh run watch "$(gh run list --workflow=publish.yml --limit 1 --json databaseId -q '.[0].databaseId')" --exit-status
echo "已上線：$(gh api "repos/{owner}/{repo}/pages" -q .html_url)"
