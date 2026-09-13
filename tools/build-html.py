#!/usr/bin/env python3
"""把 docs/ 下的全部 Markdown 打成一个单文件 HTML 教程。

用法：
    python3 tools/build-html.py                    # 输出到 ../../前端工程化开发-完整教程.html
    python3 tools/build-html.py -o /tmp/out.html   # 指定输出路径

做这些事：
    1. 从 docs/.vitepress/sidebar.mts 读出目录顺序，按模块 / 单元分组
    2. 把每个 md 渲染成 HTML（自研块扫描器 + markdown-it）
    3. 处理课程专有语法：<UnitMeta />、<Demo>、::: 容器、```lang [文件名]
    4. 内部链接 /unit01/xxx 转成页内锚点
    5. 拼成一个带左侧目录、滚动高亮、阅读进度条、代码复制、目录搜索的单文件页面
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SIDEBAR = DOCS / ".vitepress" / "sidebar.mts"

md = MarkdownIt("gfm-like", {"html": True, "linkify": False}).enable("table")


# ---------------------------------------------------------------------------
# 目录：从 sidebar.mts 提取
# ---------------------------------------------------------------------------

LINK_RE = re.compile(r"\{\s*text:\s*'((?:[^'\\]|\\.)*)'\s*,\s*link:\s*'([^']+)'\s*\}")

MODULES = [
    ("模块一 · 工程化认知与工具链", [1, 2, 3]),
    ("模块二 · Vue 3 核心基础", [4, 5, 6]),
    ("模块三 · 组件化开发", [7, 8]),
    ("模块四 · 应用架构", [9, 10]),
    ("模块五 · 综合项目实战", [11, 12]),
]
UNIT_MODULE = {n: name for name, ns in MODULES for n in ns}


def slug_of(doc_rel: str) -> str:
    """docs/unit11/01-requirements.md -> unit11-01-requirements"""
    s = doc_rel[:-3] if doc_rel.endswith(".md") else doc_rel
    s = s[len("docs/"):] if s.startswith("docs/") else s
    if s.endswith("/index"):
        s = s[: -len("/index")]
    elif s == "index":
        s = ""
    return s.replace("/", "-") or "home"


def link_to_slug(link: str) -> str:
    """站点内链接 /unit11/04-list-page -> 页内锚点"""
    s = link.split("#")[0].split("?")[0]
    s = s.strip("/")
    return s.replace("/", "-") or "home"


def read_toc() -> list[tuple[str, list[tuple[str, str]]]]:
    """返回 [(分组名, [(标题, 链接)])]"""
    text = SIDEBAR.read_text(encoding="utf-8")

    # 只取 export 之前的四段定义（guide / units / projectSidebar / caseSidebar / appendixSidebar）
    found: list[tuple[str, str]] = []
    for m in LINK_RE.finditer(text):
        title = m.group(1).replace("\\'", "'")
        link = m.group(2)
        if link in ("/guide/", "/unit01/", "/project/", "/cases/", "/appendix/") and any(
            l == link for _, l in found
        ):
            continue
        found.append((title, link))

    sections: list[tuple[str, list[tuple[str, str]]]] = []
    buckets: dict[str, list[tuple[str, str]]] = {
        "课程导学": [],
        "综合项目": [],
        "案例库": [],
        "附录": [],
    }
    unit_items: dict[int, list[tuple[str, str]]] = {}

    for title, link in found:
        m = re.match(r"^/unit(\d{2})", link)
        if link.startswith("/guide/"):
            buckets["课程导学"].append((title, link))
        elif m:
            unit_items.setdefault(int(m.group(1)), []).append((title, link))
        elif link.startswith("/project/"):
            buckets["综合项目"].append((title, link))
        elif link.startswith("/cases/"):
            buckets["案例库"].append((title, link))
        elif link.startswith("/appendix/"):
            buckets["附录"].append((title, link))

    sections.append(("首页", [("教程首页", "/")]))
    sections.append(("课程导学", buckets["课程导学"]))
    for name, ns in MODULES:
        items: list[tuple[str, str]] = []
        for n in ns:
            items.extend(unit_items.get(n, []))
        sections.append((name, items))
    sections.append(("综合项目", buckets["综合项目"]))
    sections.append(("案例库", buckets["案例库"]))
    sections.append(("附录", buckets["附录"]))
    return sections


# ---------------------------------------------------------------------------
# 渲染：块扫描器
# ---------------------------------------------------------------------------

FENCE_RE = re.compile(r"^\s*(`{3,})\s*(\w*)\s*(?:\[(.*?)\])?\s*$")
CONTAINER_RE = re.compile(r"^:::\s*(\w+)?\s*(.*)$")


def fence_close(line: str, n: int) -> bool:
    """闭合围栏：反引号数不少于开围栏，且后面没有内容。"""
    m = re.match(r"^\s*(`{3,})\s*$", line)
    return bool(m) and len(m.group(1)) >= n

CONTAINER_META = {
    "tip": ("提示", "tip"),
    "info": ("说明", "tip"),
    "warning": ("注意", "warn"),
    "danger": ("不要这么做", "danger"),
    "details": ("展开看更多", "details"),
}


def esc(s: str) -> str:
    return html.escape(s, quote=False)


def render_code(lang: str, filename: str, code: str) -> str:
    head = []
    if lang:
        head.append(f'<span class="cb-lang">{esc(lang)}</span>')
    if filename:
        head.append(f'<span class="cb-file">{esc(filename)}</span>')
    head.append('<button class="cb-copy" type="button">复制</button>')
    return (
        '<div class="code-block">'
        f'<div class="cb-head">{"".join(head)}</div>'
        f'<pre class="cb-body"><code>{esc(code)}</code></pre>'
        "</div>"
    )


def render_container(kind: str, title: str, inner_html: str, open_attr: str = "") -> str:
    label, cls = CONTAINER_META.get(kind, (kind, kind))
    if kind == "details":
        summary = title or label
        return (
            f'<details class="box box-details">'
            f"<summary>{esc(summary)}</summary>"
            f'<div class="box-body">{inner_html}</div>'
            "</details>"
        )
    head = f'<div class="box-title">{esc(title)}</div>' if title else ""
    return f'<div class="box box-{cls}">{head}<div class="box-body">{inner_html}</div></div>'


ATTR_RE = re.compile(
    r'([:@]?[\w-]+)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'|\[(.*?)\])',
    re.S,
)


def parse_attrs(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in ATTR_RE.finditer(raw):
        key = m.group(1)
        val = m.group(2) or m.group(3) or m.group(4) or ""
        out[key] = val
    return out


def parse_js_string_array(raw: str) -> list[str]:
    return [m.group(1).replace("\\'", "'") for m in re.finditer(r"'((?:[^'\\]|\\.)*)'", raw)]


def render_unit_meta(raw: str) -> str:
    a = parse_attrs(raw)
    pills = []
    if a.get("module"):
        pills.append(f'<span class="um-pill um-module">{esc(a["module"])}</span>')
    if a.get("hours"):
        pills.append(f'<span class="um-pill">{esc(a["hours"])}</span>')
    if a.get("week"):
        pills.append(f'<span class="um-pill">{esc(a["week"])}</span>')

    goals = parse_js_string_array(a.get(":goals", ""))
    outcomes = parse_js_string_array(a.get(":outcomes", ""))

    parts = [
        '<section class="um">',
        '<header class="um-head">',
        f'<span class="um-unit">{esc(a.get("unit", ""))}</span>',
        f'<h2 class="um-title">{esc(a.get("title", ""))}</h2>',
        f'<div class="um-meta">{"".join(pills)}</div>',
        "</header>",
    ]
    if goals:
        items = "".join(f"<li>{esc(g)}</li>" for g in goals)
        parts.append(
            '<div class="um-block"><div class="um-label">学完这个单元，你应该能够</div>'
            f'<ul class="um-goals">{items}</ul></div>'
        )
    if outcomes:
        tags = "".join(f'<span class="um-tag">{esc(o)}</span>' for o in outcomes)
        parts.append(
            '<div class="um-block"><div class="um-label">课堂产出</div>'
            f'<div class="um-tags">{tags}</div></div>'
        )
    parts.append("</section>")
    return "".join(parts)


def render_demo(raw: str) -> str:
    a = parse_attrs(raw.split(">", 1)[0] if ">" in raw else raw)
    title = a.get("title", "可运行示例")
    desc = a.get("desc", "")

    # 从 <template #code> 里抽代码块
    m = re.search(r"```(\w*)\s*(?:\[(.*?)\])?\n(.*?)\n\s*```", raw, re.S)
    code_html = ""
    if m:
        code_html = render_code(m.group(1), m.group(2) or "", m.group(3))

    note = (
        '<div class="demo-note">这是一个可运行示例。在 VitePress 站点里它可以直接运行，'
        "下面是对应的源码。</div>"
    )
    return (
        '<div class="demo-card">'
        f'<div class="demo-head"><span class="demo-badge">可运行示例</span>{esc(title)}</div>'
        + (f'<div class="demo-desc">{esc(desc)}</div>' if desc else "")
        + note
        + code_html
        + "</div>"
    )


def scan_blocks(lines: list[str], depth: int = 0) -> str:
    """把 md 行切成块，逐块渲染。"""
    out: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if not buf:
            return
        text = "\n".join(buf).strip()
        buf.clear()
        if text:
            out.append(md.render(text))

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # --- 代码围栏 ---
        m = FENCE_RE.match(line)
        if m:
            flush()
            lang, fname = m.group(2) or "", m.group(3) or ""
            nticks = len(m.group(1))
            body: list[str] = []
            i += 1
            while i < n and not fence_close(lines[i], nticks):
                body.append(lines[i])
                i += 1
            i += 1
            out.append(render_code(lang, fname, "\n".join(body)))
            continue

        # --- 自定义容器 ---
        m = CONTAINER_RE.match(line)
        if m and m.group(1):
            flush()
            kind = m.group(1)
            title = (m.group(2) or "").strip()
            inner: list[str] = []
            depth_inner = 1
            i += 1
            open_ticks = 0
            while i < n:
                cur = lines[i]
                fm = FENCE_RE.match(cur)
                if fm:
                    if open_ticks == 0:
                        open_ticks = len(fm.group(1))
                    elif fence_close(cur, open_ticks):
                        open_ticks = 0
                    inner.append(cur)
                    i += 1
                    continue
                if open_ticks == 0:
                    cm = CONTAINER_RE.match(cur)
                    if cm and cm.group(1):
                        depth_inner += 1
                    elif cm:
                        depth_inner -= 1
                        if depth_inner == 0:
                            i += 1
                            break
                inner.append(cur)
                i += 1
            out.append(render_container(kind, title, scan_blocks(inner, depth + 1)))
            continue

        # --- 独立容器的结束标记（不该出现，防御） ---
        if CONTAINER_RE.match(line) and not CONTAINER_RE.match(line).group(1):
            i += 1
            continue

        # --- <UnitMeta ... /> ---
        if "<UnitMeta" in line:
            chunk = line
            while "/>" not in chunk and i + 1 < n:
                i += 1
                chunk += "\n" + lines[i]
            flush()
            out.append(render_unit_meta(chunk))
            i += 1
            continue

        # --- <Demo ...> ... </Demo> ---
        if "<Demo" in line and "</Demo>" not in line:
            flush()
            chunk = line
            while "</Demo>" not in chunk and i + 1 < n:
                i += 1
                chunk += "\n" + lines[i]
            out.append(render_demo(chunk))
            i += 1
            continue

        # --- 其余交给 markdown-it ---
        if line.strip() == "" and buf and buf[-1].strip() == "":
            i += 1
            continue
        buf.append(line)
        i += 1

    flush()
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 链接改写与标题锚点
# ---------------------------------------------------------------------------

HEAD_RE = re.compile(r"<h([234])>(.*?)</h\1>", re.S)
TAG_STRIP = re.compile(r"<[^>]+>")
MD_LINK_RE = re.compile(r'<a href="([^"]*)"')


def slugify_heading(text: str) -> str:
    t = TAG_STRIP.sub("", text)
    t = html.unescape(t)
    t = re.sub(r"[\s·]+", "-", t.strip())
    t = re.sub(r"[^\w\u4e00-\u9fa5\-]", "", t)
    return t.lower() or "sec"


def rewrite(html_text: str, fslug: str) -> str:
    valid = VALID_SLUGS

    # 标题锚点
    def head(m: re.Match[str]) -> str:
        lvl, inner = m.group(1), m.group(2)
        return f'<h{lvl} id="{fslug}--{slugify_heading(inner)}">{inner}</h{lvl}>'

    html_text = HEAD_RE.sub(head, html_text)

    # 链接处理
    def link(m: re.Match[str]) -> str:
        url = m.group(1)
        if url.startswith(("http://", "https://", "mailto:", "#")):
            return m.group(0)
        if re.search(r"\.(png|jpe?g|svg|gif|webp|ico)$", url, re.I):
            return m.group(0)
        if url.startswith("/"):
            target = link_to_slug(url)
            if target in valid:
                return f'<a href="#{target}"'
        # 相对路径（示例文档里写的 docs/xxx.md 之类）在单文件里不存在，降级为不可点
        return '<a class="inner-link link-external" data-href="' + html.escape(url, quote=True) + '"'

    return MD_LINK_RE.sub(link, html_text)


# ---------------------------------------------------------------------------
# 页面骨架
# ---------------------------------------------------------------------------

CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{
  --brand:#42b883;--brand-dark:#369a6f;--brand-soft:rgba(66,184,131,.12);
  --text:#243b53;--text-2:#52667a;--text-3:#8a9aab;
  --bg:#f7f9fb;--bg-card:#fff;--border:#e3e9ef;--border-strong:#cfd8e3;
  --code-bg:#f6f8fa;--warn:#d97706;--danger:#d64545;--tip:#2b7bbf;
  --sbw:308px;
}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);
  font:15px/1.78 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  -webkit-font-smoothing:antialiased}
a{color:var(--brand-dark);text-decoration:none}
a:hover{text-decoration:underline}
code{font-family:"SF Mono",ui-monospace,Menlo,Consolas,"Liberation Mono",monospace}

/* 阅读进度 */
#progress{position:fixed;top:0;left:0;right:0;height:3px;z-index:60;background:transparent}
#progress>i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--brand),#5fd6a4)}

/* 侧栏 */
#sidebar{position:fixed;top:0;left:0;bottom:0;width:var(--sbw);overflow-y:auto;
  background:#fff;border-right:1px solid var(--border);z-index:50;padding-bottom:40px}
.brand{position:sticky;top:0;background:#fff;padding:16px 18px 12px;border-bottom:1px solid var(--border);z-index:2}
.brand h1{margin:0;font-size:16px;letter-spacing:.02em}
.brand p{margin:4px 0 10px;font-size:12px;color:var(--text-3)}
#tocfilter{width:100%;padding:7px 10px;border:1px solid var(--border-strong);border-radius:8px;
  font-size:13px;outline:none;background:#fbfcfd}
#tocfilter:focus{border-color:var(--brand);box-shadow:0 0 0 3px var(--brand-soft)}
nav{padding:10px 12px}
.nav-group{margin:6px 0 12px}
.nav-group>h2{margin:0 0 4px;padding:6px 8px;font-size:12.5px;font-weight:700;color:var(--brand-dark);
  letter-spacing:.03em;background:var(--brand-soft);border-radius:6px}
.nav-item{display:block;padding:5px 8px 5px 14px;font-size:13.5px;color:var(--text-2);
  border-left:2px solid transparent;border-radius:0 6px 6px 0}
.nav-item:hover{background:#f0f4f8;color:var(--text);text-decoration:none}
.nav-item.active{background:var(--brand-soft);color:var(--brand-dark);font-weight:600;border-left-color:var(--brand)}
.nav-item.hidden{display:none}
.nav-group.hidden{display:none}

/* 内容 */
#main{margin-left:var(--sbw);padding:32px 44px 120px;max-width:1020px}
.doc{background:var(--bg-card);border:1px solid var(--border);border-radius:14px;
  padding:30px 38px 34px;margin-bottom:26px;scroll-margin-top:20px;
  box-shadow:0 1px 2px rgba(20,40,70,.04)}
.crumb{font-size:12.5px;color:var(--text-3);margin-bottom:14px}
.crumb .sep{margin:0 6px;opacity:.6}
.src{font-size:11.5px;color:var(--text-3);margin-top:22px;padding-top:12px;
  border-top:1px dashed var(--border);font-family:monospace}

.doc h1{font-size:1.72rem;line-height:1.35;margin:0 0 22px;padding-bottom:14px;
  border-bottom:2px solid var(--brand)}
.doc h2{font-size:1.24rem;margin:38px 0 14px;padding-top:16px;border-top:1px solid var(--border)}
.doc h3{font-size:1.06rem;margin:26px 0 10px;color:#1b2b3d}
.doc h4{font-size:.98rem;margin:20px 0 8px;color:var(--text-2)}
.doc p{margin:12px 0}
.doc ul,.doc ol{margin:12px 0;padding-left:24px}
.doc li{margin:5px 0}
.doc blockquote{margin:14px 0;padding:2px 16px;border-left:3px solid var(--border-strong);
  color:var(--text-2);background:#fafcfd}
.doc hr{border:none;border-top:1px solid var(--border);margin:34px 0}
.doc strong{color:#16232f}

/* 表格 */
.doc table{border-collapse:collapse;width:100%;margin:16px 0;font-size:13.8px;display:block;overflow-x:auto}
.doc th,.doc td{border:1px solid var(--border-strong);padding:8px 12px;text-align:left;vertical-align:top}
.doc th{background:#eef3f8;font-weight:700;white-space:nowrap}
.doc tr:nth-child(even) td{background:#fafcfe}

/* 行内代码 */
.doc :not(pre)>code{background:var(--code-bg);border:1px solid var(--border);
  border-radius:5px;padding:1px 5px;font-size:.89em;color:#b5316b}

/* 代码块 */
.code-block{margin:16px 0;border:1px solid var(--border-strong);border-radius:10px;overflow:hidden;background:var(--code-bg)}
.cb-head{display:flex;align-items:center;gap:10px;padding:7px 12px;background:#eef2f7;
  border-bottom:1px solid var(--border);font-size:12px}
.cb-lang{font-weight:700;color:var(--text-2);text-transform:uppercase;letter-spacing:.04em}
.cb-file{color:var(--text-3);font-family:monospace}
.cb-copy{margin-left:auto;border:1px solid var(--border-strong);background:#fff;border-radius:6px;
  padding:3px 10px;font-size:12px;color:var(--text-2);cursor:pointer}
.cb-copy:hover{border-color:var(--brand);color:var(--brand-dark)}
.cb-copy.done{background:var(--brand);border-color:var(--brand);color:#fff}
.cb-body{margin:0;padding:14px 16px;overflow-x:auto;font-size:13px;line-height:1.62}
.cb-body code{white-space:pre;color:#1f2933}

/* 容器 */
.box{margin:18px 0;border-radius:10px;border:1px solid;overflow:hidden;background:#fff}
.box>.box-title{padding:8px 14px;font-weight:700;font-size:13.5px;border-bottom:1px solid}
.box>.box-body{padding:4px 16px 12px}
.box-body>p:first-child{margin-top:10px}
.box-body>p:last-child{margin-bottom:8px}
.box-tip{border-color:#bcdcf5;background:#f4faff}
.box-tip>.box-title{background:#e3f2fd;color:var(--tip);border-color:#bcdcf5}
.box-warn{border-color:#f5e0b8;background:#fffbf2}
.box-warn>.box-title{background:#fdf1dc;color:var(--warn);border-color:#f5e0b8}
.box-danger{border-color:#f5c6c6;background:#fff7f7}
.box-danger>.box-title{background:#fbe3e3;color:var(--danger);border-color:#f5c6c6}
.box-details{border-color:var(--border-strong);background:#fbfcfd}
.box-details>summary{padding:10px 14px;cursor:pointer;font-weight:600;font-size:13.8px;color:var(--text-2);
  list-style:none;user-select:none}
.box-details>summary::-webkit-details-marker{display:none}
.box-details>summary::before{content:"▸";display:inline-block;margin-right:8px;color:var(--brand);
  transition:transform .15s}
.box-details[open]>summary::before{transform:rotate(90deg)}
.box-details[open]>summary{border-bottom:1px solid var(--border)}
.box-details>.box-body{padding:4px 16px 12px}

/* 单元导学卡 */
.um{border:1px solid var(--border);border-radius:12px;padding:22px 26px 20px;margin:0 0 30px;
  background:linear-gradient(180deg,#f4fbf8,#fff)}
.um-head{border-bottom:1px dashed var(--border-strong);padding-bottom:14px;margin-bottom:16px}
.um-unit{display:inline-block;font-size:12px;font-weight:700;letter-spacing:.08em;color:#fff;
  background:var(--brand);border-radius:999px;padding:2px 12px;margin-bottom:10px}
.um-title{margin:0;padding:0;border:none;font-size:1.5rem;line-height:1.35}
.um-meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.um-pill{font-size:12px;color:var(--text-2);background:#eef3f8;border-radius:6px;padding:3px 10px}
.um-module{color:var(--brand-dark);background:var(--brand-soft);font-weight:600}
.um-block+.um-block{margin-top:16px}
.um-label{font-size:12px;font-weight:700;letter-spacing:.04em;color:var(--text-3);margin-bottom:8px}
.um-goals{margin:0;padding-left:20px}
.um-goals li{margin:4px 0;font-size:14px}
.um-goals li::marker{color:var(--brand)}
.um-tags{display:flex;flex-wrap:wrap;gap:8px}
.um-tag{font-size:13px;color:var(--brand-dark);background:var(--brand-soft);
  border-radius:6px;padding:3px 10px}

/* 示例卡 */
.demo-card{border:1px solid var(--border-strong);border-radius:10px;padding:14px 16px;
  margin:18px 0;background:#fbfdfc}
.demo-head{font-weight:700;font-size:14px;display:flex;align-items:center;gap:8px}
.demo-badge{font-size:11px;background:var(--brand);color:#fff;border-radius:5px;padding:2px 8px;font-weight:600}
.demo-desc{font-size:13px;color:var(--text-2);margin-top:6px}
.demo-note{font-size:12.5px;color:var(--text-3);margin:10px 0 4px}

.inner-link.link-external{color:var(--text-3);border-bottom:1px dashed var(--border-strong)}

/* 回到顶部 */
#toTop{position:fixed;right:26px;bottom:26px;width:42px;height:42px;border-radius:50%;
  border:1px solid var(--border-strong);background:#fff;color:var(--text-2);font-size:17px;
  cursor:pointer;display:none;z-index:55;box-shadow:0 2px 10px rgba(20,40,70,.12)}
#toTop:hover{border-color:var(--brand);color:var(--brand-dark)}
#toTop.show{display:block}

#menuBtn{display:none}

/* 窄屏 */
@media (max-width:1080px){
  :root{--sbw:270px}
  #main{padding:24px 22px 100px}
  .doc{padding:22px 20px 26px}
}
@media (max-width:820px){
  #sidebar{transform:translateX(-100%);transition:transform .2s;width:290px}
  body.nav-open #sidebar{transform:none}
  #main{margin-left:0;padding:56px 14px 90px}
  #menuBtn{display:block;position:fixed;top:10px;left:10px;z-index:70;width:40px;height:36px;
    border-radius:8px;border:1px solid var(--border-strong);background:#fff;cursor:pointer}
}

#boxed{position:fixed;inset:0;background:rgba(0,0,0,.25);display:none;z-index:45}
body.nav-open #boxed{display:block}
@media (min-width:821px){#boxed{display:none!important}}

/* 打印 */
@media print{
  #sidebar,#progress,#toTop,#menuBtn,#boxed{display:none!important}
  #main{margin:0;padding:0;max-width:none}
  .doc{border:none;box-shadow:none;padding:0;margin:0 0 24px;break-after:page}
  .box-details{break-inside:avoid}
  .box-details>summary{list-style:none}
  a{color:inherit}
}
"""

JS = """
(function(){
  var docs = Array.prototype.slice.call(document.querySelectorAll('.doc'));
  var links = Array.prototype.slice.call(document.querySelectorAll('.nav-item'));
  var bar = document.querySelector('#progress > i');
  var toTop = document.getElementById('toTop');

  function onScroll(){
    var st = window.scrollY || document.documentElement.scrollTop;
    var h = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.width = (h > 0 ? (st / h * 100) : 0) + '%';
    toTop.classList.toggle('show', st > 600);

    var cur = docs[0];
    for (var i = 0; i < docs.length; i++){
      if (docs[i].getBoundingClientRect().top <= 120) cur = docs[i];
      else break;
    }
    links.forEach(function(a){
      a.classList.toggle('active', a.getAttribute('data-target') === cur.id);
    });
    var act = document.querySelector('.nav-item.active');
    if (act){
      var r = act.getBoundingClientRect();
      if (r.top < 60 || r.bottom > window.innerHeight - 20){
        act.scrollIntoView({block:'center'});
      }
    }
  }

  window.addEventListener('scroll', onScroll, {passive:true});
  window.addEventListener('resize', onScroll);
  onScroll();

  // 复制代码
  document.addEventListener('click', function(e){
    var btn = e.target.closest ? e.target.closest('.cb-copy') : null;
    if (btn){
      var pre = btn.closest('.code-block').querySelector('.cb-body');
      var text = pre ? pre.innerText : '';
      var done = function(){
        var old = btn.textContent;
        btn.textContent = '已复制'; btn.classList.add('done');
        setTimeout(function(){ btn.textContent = old; btn.classList.remove('done'); }, 1400);
      };
      if (navigator.clipboard && navigator.clipboard.writeText){
        navigator.clipboard.writeText(text).then(done, function(){});
      } else {
        var ta = document.createElement('textarea');
        ta.value = text; document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); done(); } catch(err){}
        document.body.removeChild(ta);
      }
      e.preventDefault();
      return;
    }
    // 目录筛选
    var menu = e.target.closest ? e.target.closest('#menuBtn') : null;
    if (menu){ document.body.classList.toggle('nav-open'); return; }
    if (e.target.id === 'boxed'){ document.body.classList.remove('nav-open'); return; }
    // 侧栏点击后收起
    var nav = e.target.closest ? e.target.closest('.nav-item') : null;
    if (nav && window.innerWidth <= 820) document.body.classList.remove('nav-open');
  });

  // 目录搜索
  var filter = document.getElementById('tocfilter');
  if (filter){
    filter.addEventListener('input', function(){
      var q = filter.value.trim().toLowerCase();
      document.querySelectorAll('.nav-group').forEach(function(g){
        var any = false;
        g.querySelectorAll('.nav-item').forEach(function(a){
          var hit = !q || a.textContent.toLowerCase().indexOf(q) >= 0;
          a.classList.toggle('hidden', !hit);
          if (hit) any = true;
        });
        g.classList.toggle('hidden', !any);
      });
    });
  }
})();
"""


def build() -> str:
    toc = read_toc()

    global VALID_SLUGS
    files: dict[str, Path] = {}
    for p in sorted(DOCS.rglob("*.md")):
        rel = p.relative_to(ROOT).as_posix()
        files[rel] = p
    VALID_SLUGS = {slug_of(rel) for rel in files}

    link_map: dict[str, str] = {}
    for rel in files:
        s = slug_of(rel)
        link_map[s] = s
        # /unit11/01-requirements 与 /unit11/01-requirements 等价
    # 处理 /xxx/ 形式（末尾斜杠）
    for rel in files:
        s = slug_of(rel)
        link_map[s + "/"] = s

    title_of = {}
    for group, items in toc:
        for t, l in items:
            title_of[l] = t

    # --- 侧栏 ---
    nav_parts: list[str] = []
    for group, items in toc:
        if not items:
            continue
        rows = []
        for t, l in items:
            slug = link_to_slug(l)
            if slug not in VALID_SLUGS:
                continue
            rows.append(
                f'<a class="nav-item" href="#{slug}" data-target="{slug}">{esc(t)}</a>'
            )
        if rows:
            nav_parts.append(
                f'<div class="nav-group"><h2>{esc(group)}</h2>{"".join(rows)}</div>'
            )

    # --- 正文 ---
    body_parts: list[str] = []
    for rel, path in files.items():
        slug = slug_of(rel)
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception:
            continue
        lines = raw.split("\n")
        if lines and lines[0].strip() == "---":
            for j in range(1, min(len(lines), 40)):
                if lines[j].strip() == "---":
                    lines = lines[j + 1:]
                    break

        rendered = rewrite(scan_blocks(lines), slug)

        # 面包屑：从 toc 里找这个文件属于哪个分组
        crumb = ""
        for group, items in toc:
            if any(link_to_slug(l) == slug for _, l in items):
                mod = group
                crumb = f'<div class="crumb"><span>{esc(mod)}</span>'
                if slug.startswith("unit") and "-" in slug:
                    unum = slug[4:6]
                    crumb += f'<span class="sep">›</span><span>单元 {int(unum)}</span>'
                crumb += "</div>"
                break

        body_parts.append(
            f'<section class="doc" id="{slug}">{crumb}{rendered}'
            f'<div class="src">源文件：{esc(rel)}</div></section>'
        )

    total_docs = len(body_parts)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>前端工程化开发 · 48 学时完整教程</title>
<meta name="description" content="12 周 48 学时完整教程，含 12 个单元、综合项目与 10 个案例">
<style>{CSS}</style>
</head>
<body>
<div id="progress"><i></i></div>
<button id="menuBtn" type="button" aria-label="目录">☰</button>
<aside id="sidebar">
  <div class="brand">
    <h1>前端工程化开发</h1>
    <p>48 学时 · 12 个单元 · {total_docs} 篇</p>
    <input id="tocfilter" type="search" placeholder="筛选目录…" autocomplete="off">
  </div>
  <nav>{"".join(nav_parts)}</nav>
</aside>
<div id="boxed"></div>
<main id="main">{"".join(body_parts)}</main>
<button id="toTop" type="button" onclick="window.scrollTo({{top:0}})">↑</button>
<script>{JS}</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    out = Path(args.out) if args.out else ROOT.parent / "前端工程化开发-完整教程.html"
    text = build()
    out.write_text(text, encoding="utf-8")
    size_mb = out.stat().st_size / 1024 / 1024
    print(f"已生成 {out}")
    print(f"体积 {size_mb:.2f} MB")
    return 0


VALID_SLUGS: set[str] = set()

if __name__ == "__main__":
    sys.exit(main())
