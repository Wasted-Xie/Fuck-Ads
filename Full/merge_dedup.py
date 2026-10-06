# -*- coding: utf-8 -*-
# merge_dedup.py
# Merge three DNS blocklist sources under raw/ and deduplicate at line level,
# producing one AdGuard-syntax list.
# - Reads raw/ only; source files are never modified
# - Skips empty lines, "!" comments and "[...]" header lines
# - Block rules (||...^) and whitelist rules (@@||...^) are deduplicated
#   separately; whitelist rules are kept at the end of the output file
# Usage: py merge_dedup.py   (on Windows use the py launcher if "python"
#        points to the Microsoft Store stub)

import sys
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))            # Full/
ROOT_DIR = os.path.dirname(BASE_DIR)                             # 项目根目录
RAW_DIR = os.path.join(ROOT_DIR, "Cache", "raw")
OUT_DIR = os.path.join(ROOT_DIR, "out")
OUT_FILE = os.path.join(OUT_DIR, "merged_dns_rules.txt")

# Source definitions
SOURCES = [
    {"label": "URLHaus (AdGuard Hostlists #11)", "file": "filter_11.txt",
     "url": "https://adguardteam.github.io/HostlistsRegistry/assets/filter_11.txt"},
    {"label": "GOODBYEADS dns", "file": "goodbyeads_dns.txt",
     "url": "https://github.com/8680/GOODBYEADS (mirror ghfast.top)"},
    {"label": "AdBlock DNS (217heidai)", "file": "adblockdns.txt",
     "url": "https://github.com/217heidai/adblockfilters"},
    {"label": "Integrated extra sources (28 lists)", "file": "integrated_extra.txt",
     "path": os.path.join(OUT_DIR, "integrated_extra.txt"),
     "url": "yhosts / ad-wars / 1024_hosts / AdAway / YousList / StevenBlack / anti-AD / "
            "EasyList family / ADgk / CJX / mvps / Hblock / Spam404 / halflife / "
            "AWAvenue / AdGuard Chinese / scamblocklist / NoCoin / Peter Lowe / "
            "Dan Pollock / neohosts / i-dont-care-about-cookies / etc.",
     "optional": True},
]

def is_block_rule(line):
    return line.startswith("||")


def is_white_rule(line):
    return line.startswith("@@")


def load_rules(path):
    """Read one source file, return (block_set, white_set, total_rule_lines).

    所有上游源一律按原样拦截，不做任何域名豁免。
    （历史上曾对附加源启用 360 品牌保护，该机制已按用户要求彻底移除。）
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    blocks, whites = set(), set()
    total = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:                      # empty line
            continue
        if line.startswith("!") or line.startswith("["):  # comment / header
            continue
        total += 1
        if is_white_rule(line):
            whites.add(line)
            continue
        blocks.add(line)
    return blocks, whites, total


def main():
    per_source = []
    all_blocks, all_whites = set(), set()

    for src in SOURCES:
        path = src.get("path") or os.path.join(RAW_DIR, src["file"])
        if not os.path.exists(path):
            if src.get("optional"):
                print(f"[WARN] optional source missing, skipped: {src['file']}")
                continue
            print(f"[ERROR] missing source file: {path}", file=sys.stderr)
            sys.exit(1)
        blocks, whites, total = load_rules(path)
        per_source.append({**src, "total": total,
                           "blocks": len(blocks), "whites": len(whites)})
        all_blocks |= blocks
        all_whites |= whites

    sorted_blocks = sorted(all_blocks)
    sorted_whites = sorted(all_whites)

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    header = [
        "!",
        "! Title: Merged DNS blocklist (line-level dedup)",
        f"! Description: {len(per_source)} 个源按整行精确去重合并，白名单(@@)规则保留在文件末尾",
        f"! Generated: {stamp}",
        f"! Block rules: {len(sorted_blocks)}",
        f"! Whitelist rules: {len(sorted_whites)}",
        "!",
    ]
    header += [f"! Source {i + 1}: {s['label']}  <-  {s['url']}"
               for i, s in enumerate(per_source)]
    header.append("!")

    body = sorted_blocks + sorted_whites
    new_text = "\n".join(header + body + [""])

    # Rewrite only when something besides the generated timestamp changed,
    # so a scheduled run with identical rules creates no git commit.
    def content_key(text):
        return [ln for ln in text.splitlines()
                if not ln.startswith("! Generated:")]

    changed = True
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE, "r", encoding="utf-8") as f:
            old_text = f.read()
        changed = content_key(old_text) != content_key(new_text)
    if changed:
        with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_text)
        out_status = "written (content changed)"
    else:
        out_status = "unchanged - file kept as-is"

    # ---- Console report (ASCII only, safe under any codepage) ----
    print("==== Per-source input stats ====")
    sum_total = 0
    for s in per_source:
        sum_total += s["total"]
        print(f"{s['label']:<34} rules={s['total']:>7}  "
              f"(block {s['blocks']} / white {s['whites']})")
    print("==== Merge dedup result ====")
    print(f"Total input rule lines       : {sum_total}")
    print(f"Block rules after dedup      : {len(sorted_blocks)}")
    print(f"Whitelist rules after dedup  : {len(sorted_whites)}")
    print(f"Total after dedup            : {len(sorted_blocks) + len(sorted_whites)}")
    print(f"Duplicate lines removed      : {sum_total - len(sorted_blocks) - len(sorted_whites)}")
    print(f"Output file                  : {os.path.relpath(OUT_FILE, ROOT_DIR)}  [{out_status}]")


if __name__ == "__main__":
    main()
