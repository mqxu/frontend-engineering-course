#!/usr/bin/env python3
"""按写作规范清理行业黑话用词。

保留自然技术含义的用法（如「文本对齐方式」「逐行对齐」），
只替换黑话腔的表达。
"""
from pathlib import Path

ROOT = Path("/Users/moqi/Desktop/前端工程化开发/output/course-site/docs")

# 精确替换表（长串在前，避免误伤）
RULES: list[tuple[str, str]] = [
    ("登录鉴权闭环", "登录与鉴权"),
    ("登录鉴权完整链路", "登录鉴权完整链路"),
    ("闭环", "完整链路"),

    ("这一节讲怎么落地", "这一节讲具体怎么做"),
    ("让规范能落地的关键", "让规范真正生效的关键"),

    ("第一件要对齐的事：统一响应结构", "第一件要定下来的事：统一响应结构"),
    ("第二件要对齐的事：字段名与类型", "第二件要定下来的事：字段名与类型"),
    ("第三件要对齐的事：跨域", "第三件要定下来的事：跨域"),
    ("三件事必须先对齐", "三件事必须先定下来"),
    ("统一响应结构已对齐", "统一响应结构已确认"),
    ("分页字段名已对齐", "分页字段名已确认"),
    ("接口约定对齐了", "接口约定定下来了"),
    ("这份对齐的结论", "这份确认下来的结论"),
    ("第一次对齐", "第一次核对"),
    ("字段对齐的结果", "字段核对的结果"),
    ("联调流程、字段对齐、跨域", "联调流程、字段核对、跨域"),
    ("字段不对齐怎么处理", "字段名对不上怎么处理"),
    ("字段名没对齐", "字段名对不上"),
    ("前端校验规则和后端接口约定要对齐", "前端校验规则要和后端接口约定一致"),
    ("两边天然对齐", "两边天然一致"),
    ("一开始就对齐基线最省事", "一开始就用基线版本最省事"),
    ("把这两处逐个对齐", "把这两处逐个核对"),
    ("路径前缀要对齐，别乱加", "路径前缀要对上，别乱加"),
    ("换业务载体后做完整闭环", "换业务载体后做一遍完整流程"),
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
        for old, rep in RULES:
            if old == rep:
                continue
            n = new.count(old)
            if n:
                new = new.replace(old, rep)
                hits += n
        if hits:
            f.write_text(new, encoding="utf-8")
            print(f"{hits:>4}  {f.relative_to(ROOT)}")
            total += hits
    print("共替换", total, "处")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
