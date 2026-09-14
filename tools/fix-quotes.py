#!/usr/bin/env python3
"""把直角引号「」『』换成中文引号 “”‘’。

写作规范要求中文语境用 “ ”，不用直角引号。手写时容易带上，收尾前跑一次：

    python3 tools/fix-quotes.py            # 只报告，不改
    python3 tools/fix-quotes.py --write    # 实际替换

扫描范围是 docs/ 下的 Markdown（跳过 public 目录）。"""
import argparse
import pathlib
import re
import sys

PAIRS = {
    '\u300c': '\u201c',  # 「 → “
    '\u300d': '\u201d',  # 」 → ”
    '\u300e': '\u2018',  # 『 → ‘
    '\u300f': '\u2019',  # 』 → ’
}
PATTERN = re.compile('[' + ''.join(PAIRS) + ']')
ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description='替换直角引号')
    parser.add_argument('--write', action='store_true', help='实际写入文件')
    args = parser.parse_args()

    total = 0
    for path in sorted((ROOT / 'docs').rglob('*.md')):
        if 'public' in path.parts:
            continue
        text = path.read_text(encoding='utf-8')
        hits = PATTERN.findall(text)
        if not hits:
            continue
        total += len(hits)
        rel = path.relative_to(ROOT)
        print(f'  {rel}  {len(hits)} 处')
        if args.write:
            cleaned = text
            for old, new in PAIRS.items():
                cleaned = cleaned.replace(old, new)
            path.write_text(cleaned, encoding='utf-8')

    print()
    if total == 0:
        print('没有直角引号，通过。')
        return 0
    if args.write:
        print(f'已替换 {total} 处。')
        return 0
    print(f'发现 {total} 处，加 --write 执行替换。')
    return 1


if __name__ == '__main__':
    sys.exit(main())
