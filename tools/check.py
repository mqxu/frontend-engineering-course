#!/usr/bin/env python3
"""教程站点内容校验。

用法：
    python3 tools/check.py            # 全量检查
    python3 tools/check.py --links    # 额外检查内部链接（建议内容写完后跑）

检查项：
    1. 文件可读且为 UTF-8
    2. frontmatter 格式（--- 成对）
    3. 代码块围栏成对，且带文件名的写法规范
    4. ::: 容器成对（tip / warning / danger / details / info）
    5. 自定义组件标签闭合（<Demo>、<UnitMeta>）
    6. Vue 模板里花括号、尖括号的基本平衡
    7. 排版规则：直角引号、中西文之间缺空格
    8. 内部链接指向的文件是否存在
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

CONTAINERS = ("tip", "warning", "danger", "details", "info")

# 允许出现在正文里的 HTML 标签（VitePress 与 Vue 组件）
ALLOWED_TAGS = {
    "Demo", "UnitMeta", "div", "span", "p", "ul", "ol", "li", "table", "thead", "tbody",
    "tr", "th", "td", "strong", "em", "b", "i", "code", "pre", "br", "hr", "a", "img",
    "h1", "h2", "h3", "h4", "blockquote", "kbd", "sub", "sup", "small", "template", "script",
    "style", "section", "header", "footer", "nav", "button", "input", "label", "details",
    "summary", "Row", "Col", "Badge", "Card", "Steps", "Checklist", "Svg",
}


class Issue:
    def __init__(self, path: Path, line: int, kind: str, msg: str):
        self.path, self.line, self.kind, self.msg = path, line, kind, msg

    def __str__(self) -> str:
        rel = self.path.relative_to(ROOT)
        return f"  [{self.kind}] {rel}:{self.line}  {self.msg}"


def strip_code(text: str) -> list[tuple[int, str]]:
    """去掉代码块与行内代码，返回 (行号, 该行净化后的文本)。"""
    out: list[tuple[int, str]] = []
    in_fence = False
    for i, raw in enumerate(text.split("\n"), 1):
        line = raw
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            out.append((i, ""))
            continue
        if in_fence:
            out.append((i, ""))
            continue
        line = re.sub(r"`[^`]*`", "", line)
        out.append((i, line))
    return out


def check_file(path: Path) -> list[Issue]:
    issues: list[Issue] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        return [Issue(path, 0, "编码", f"不是合法 UTF-8：{e}")]
    except (PermissionError, OSError) as e:
        return [Issue(path, 0, "读取", f"无法读取：{e}")]

    lines = text.split("\n")

    # --- frontmatter ---
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end < 0:
            issues.append(Issue(path, 1, "frontmatter", "开头的 --- 没有配对结束"))
    elif re.match(r"^---\s*\n", text):
        issues.append(Issue(path, 1, "frontmatter", "疑似 frontmatter 但格式不正确"))

    # --- 代码块围栏 ---
    fences = [i for i, l in enumerate(lines, 1) if re.match(r"^\s*(```|~~~)", l)]
    if len(fences) % 2 == 1:
        issues.append(Issue(path, fences[-1], "代码块", f"围栏数为奇数（{len(fences)}），有未闭合的代码块"))

    # 代码块开头的语言标记（```js [文件名] 这一行的语法检查）
    for i, l in enumerate(lines, 1):
        m = re.match(r"^\s*```(\w+)\s*(\[.*\])?\s*$", l)
        if m and m.group(2) is None and m.group(1).isdigit():
            issues.append(Issue(path, i, "代码块", "语言标记疑似写成了数字"))

    # --- 容器配对 ---
    depth = 0
    open_stack: list[tuple[int, str]] = []
    for i, l in enumerate(lines, 1):
        m = re.match(r"^:::(\s*)(\w+)?", l)
        if not m:
            continue
        name = (m.group(2) or "").strip()
        if name:
            if name not in CONTAINERS:
                issues.append(Issue(path, i, "容器", f"未知的容器类型 ::: {name}"))
            depth += 1
            open_stack.append((i, name))
        else:
            if depth == 0:
                issues.append(Issue(path, i, "容器", "多余的 ::: 结束标记"))
            else:
                depth -= 1
                open_stack.pop()
    for ln, name in open_stack:
        issues.append(Issue(path, ln, "容器", f"::: {name} 没有对应的结束标记"))

    # --- 组件标签闭合 ---
    for tag in ("Demo", "UnitMeta"):
        opens = len(re.findall(rf"<{tag}[\s/>]", text))
        closes = len(re.findall(rf"</{tag}>", text))
        self_closed = len(re.findall(rf"<{tag}(?![A-Za-z])[^>]*/>", text, re.S))
        if opens != closes + self_closed:
            issues.append(
                Issue(path, 0, "组件", f"<{tag}> 开标签 {opens} 个，闭标签 {closes} 个，自闭合 {self_closed} 个，不匹配")
            )

    # --- 排版规则 ---
    for i, l in strip_code(text):
        if not l:
            continue
        # 直角引号
        if "「" in l or "」" in l:
            issues.append(Issue(path, i, "排版", "出现直角引号，请改用全角引号 “ ”"))
        # 中西文之间缺空格（排除链接、属性等）
        cleaned = re.sub(r"https?://\S+", "", l)
        cleaned = re.sub(r"\[[^\]]*\]\([^)]*\)", "", cleaned)
        bad = re.findall(r"[\u4e00-\u9fa5][A-Za-z0-9]|[A-Za-z0-9][\u4e00-\u9fa5]", cleaned)
        if bad:
            sample = "、".join(sorted(set(bad))[:4])
            issues.append(Issue(path, i, "排版", f"中文与西文直接相邻：{sample}"))

    return issues


def collect_links(path: Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8")
    found = []
    for i, l in enumerate(text.split("\n"), 1):
        for m in re.finditer(r"\]\((/[^)#\s]*)(#[^)\s]*)?\)", l):
            found.append((i, m.group(1)))
    return found


def link_target(url: str) -> list[Path]:
    url = url.split("#")[0].rstrip("/")
    rel = url.lstrip("/")
    if not rel:
        return [(DOCS / "index.md")]
    return [DOCS / f"{rel}.md", DOCS / rel / "index.md", DOCS / rel]


def main() -> int:
    do_links = "--links" in sys.argv
    show_all = "--all" in sys.argv or "--links" in sys.argv
    only = None
    for arg in sys.argv[1:]:
        if arg.startswith("--only="):
            only = arg.split("=", 1)[1]

    files = sorted(DOCS.rglob("*.md"))
    if not files:
        print("没有找到任何 md 文件")
        return 1

    all_issues: list[Issue] = []
    for f in files:
        all_issues.extend(check_file(f))

    print(f"检查了 {len(files)} 个 Markdown 文件")

    # 按类别统计
    kinds: dict[str, int] = {}
    for it in all_issues:
        kinds[it.kind] = kinds.get(it.kind, 0) + 1
    if kinds:
        print("\n问题统计：")
        for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]):
            print(f"  {k}: {v}")

    # 按文件统计（便于定位）
    by_file: dict[str, int] = {}
    for it in all_issues:
        key = str(it.path.relative_to(ROOT))
        by_file[key] = by_file.get(key, 0) + 1
    if by_file and not show_all:
        print("\n问题最多的文件（前 20）：")
        for k, v in sorted(by_file.items(), key=lambda kv: -kv[1])[:20]:
            print(f"  {v:>4}  {k}")

    # 打印明细（每类最多 12 条；--all / --links 时全打）
    shown: dict[str, int] = {}
    for it in all_issues:
        if only and it.kind != only:
            continue
        if not show_all and shown.get(it.kind, 0) >= 12:
            continue
        shown[it.kind] = shown.get(it.kind, 0) + 1
        print(it)

    if do_links:
        print("\n检查内部链接……")
        existing = {f.resolve() for f in files}
        broken = []
        for f in files:
            for line, url in collect_links(f):
                cands = link_target(url)
                # 静态资源链接（图片）不检查
                if re.search(r"\.(png|jpg|jpeg|svg|gif|webp|ico)$", url, re.I):
                    continue
                if not any(c.exists() or c.resolve() in existing for c in cands):
                    broken.append((f, line, url))
        if broken:
            print(f"  失效链接 {len(broken)} 条：")
            for f, line, url in broken[:40]:
                print(f"    {f.relative_to(ROOT)}:{line}  →  {url}")
            if len(broken) > 40:
                print(f"    ……还有 {len(broken) - 40} 条")
        else:
            print("  内部链接全部有效")

    print()
    if all_issues:
        print(f"共 {len(all_issues)} 处需要处理")
        return 1
    print("语法与排版检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
