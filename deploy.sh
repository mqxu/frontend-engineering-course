#!/usr/bin/env bash
#
# 构建教程站点，把产物推到 gh-pages 分支，由 GitHub Pages 发布。
# 改完内容后执行 ./deploy.sh。发布方式的完整说明见 README 的“发布”一节。

set -euo pipefail

# 推送走 SSH。首次连接 github.com 时 ssh 会交互询问是否信任主机，脚本里要禁掉，
# 否则命令会一直等输入。accept-new 只自动接受第一次出现的主机密钥，之后若密钥
# 变化仍会拒绝。
export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"

cd "$(dirname "$0")"
ROOT="$(pwd)"

if ! git remote get-url origin > /dev/null 2>&1; then
  echo "✗ 没有配置 origin 远端，先执行 git remote add origin <仓库地址>"
  exit 1
fi
REMOTE="$(git remote get-url origin)"

# NODE_OPTIONS 置空：部分托管环境会注入文件系统拦截钩子，让 Rollup 建目录时报错。
# 普通终端里它本来就是空的，这一句没有副作用。
echo "① 构建静态站点"
NODE_OPTIONS= npm run build

DIST="$ROOT/docs/.vitepress/dist"
if [ ! -f "$DIST/index.html" ]; then
  echo "✗ 产物里没有 index.html，构建可能没成功，中止"
  exit 1
fi

echo "② 准备 gh-pages 内容"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cp -R "$DIST/." "$TMP/"
# .nojekyll 让 GitHub Pages 跳过 Jekyll，直接按静态文件发布
touch "$TMP/.nojekyll"

GIT_NAME="$(git -C "$ROOT" config user.name || echo mqxu)"
GIT_EMAIL="$(git -C "$ROOT" config user.email || echo '')"

echo "③ 提交并推送产物"
(
  cd "$TMP"
  git init -q -b gh-pages
  git add -A
  git -c user.name="$GIT_NAME" -c user.email="$GIT_EMAIL" \
      commit -q -m "chore: 部署站点 $(date '+%Y-%m-%d %H:%M')"
  git remote add origin "$REMOTE"
  # gh-pages 只存构建产物，历史没有保留价值，直接强制推送
  git push -q -f origin gh-pages
)

echo
echo "✓ 发布完成"
echo "  站点地址：https://mqxu.github.io/frontend-engineering-course/"
echo "  页面数：$(find "$DIST" -name '*.html' | wc -l | tr -d ' ')"
echo "  通常 1 分钟内生效。"
