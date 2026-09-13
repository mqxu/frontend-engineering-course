#!/usr/bin/env python3
"""统一成功业务码口径为 0。

教程单元（unit10、unit11、appendix）里写的是 `code === 200`，
项目规格（project/api.md 及三个参考实现）用的是 `code === 0`。
以项目规格为准，统一成 0。

只替换明确带 `code` 前缀的表达式，避免误伤 HTTP 200。
"""
from pathlib import Path

ROOT = Path("/Users/moqi/Desktop/前端工程化开发/output/course-site/docs")

PAIRS: list[tuple[str, str]] = [
    ("res.data.code === 200", "res.data.code === 0"),
    ("res.code === 200", "res.code === 0"),
    ("res.code !== 200", "res.code !== 0"),
    ("body.code !== 200", "body.code !== 0"),
    ("code === 200)", "code === 0)"),
    ("code !== 200)", "code !== 0)"),
]


def main() -> int:
    total = 0
    for f in sorted(ROOT.rglob("*.md")):
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        new = text
        hits = 0
        for old, rep in PAIRS:
            n = new.count(old)
            if n:
                new = new.replace(old, rep)
                hits += n
        if hits:
            f.write_text(new, encoding="utf-8")
            print(f"{hits:>3}  {f.relative_to(ROOT)}")
            total += hits
    print("共替换", total, "处")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
