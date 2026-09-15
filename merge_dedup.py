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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw")
OUT_DIR = os.path.join(BASE_DIR, "out")
OUT_FILE = os.path.join(OUT_DIR, "merged_dns_rules.txt")

# Source definitions
SOURCES = [
    {"label": "URLHaus (AdGuard Hostlists #11)", "file": "filter_11.txt",
     "url": "https://adguardteam.github.io/HostlistsRegistry/assets/filter_11.txt"},
    {"label": "GOODBYEADS dns", "file": "goodbyeads_dns.txt",
     "url": "https://github.com/8680/GOODBYEADS (mirror ghfast.top)"},
    {"label": "AdBlock DNS (217heidai)", "file": "adblockdns.txt",
     "url": "https://github.com/217heidai/adblockfilters"},
    {"label": "Integrated extra sources (18 lists)", "file": "integrated_extra.txt",
     "path": os.path.join(OUT_DIR, "integrated_extra.txt"),
     "url": "yhosts / ad-wars / 1024_hosts / AdAway / YousList / StevenBlack / anti-AD / "
            "EasyList family / ADgk / CJX / mvps / etc.",
     "optional": True},
]

# 永不拦截的保护域名（含其全部子域）：用户明确要求放行 360 系列
PROTECTED_DOMAINS = (
    "360.cn", "360.com", "360safe.com", "360shouji.com", "360os.com",
    "360totalsecurity.com", "qhimg.com", "qhmsg.com", "qhres.com",
)


def is_protected(domain):
    """判断域名是否属于受保护域名（自身或其子域）"""
    d = (domain or "").lower().strip()
    if d.startswith("*."):
        d = d[2:]
    for p in PROTECTED_DOMAINS:
        if d == p or d.endswith("." + p):
            return True
    return False


def is_block_rule(line):
    return line.startswith("||")


def is_white_rule(line):
    return line.startswith("@@")


def load_rules(path, apply_protection=False):
    """Read one source file, return (block_set, white_set, total_rule_lines, protected_count).

    apply_protection: 仅对附加上游源启用保护域名过滤；
                      原有上游列表按原样一概拦截，不做任何豁免。
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    blocks, whites = set(), set()
    total = 0
    protected = 0
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
        if is_block_rule(line):
            dom = line[2:].rstrip("^")
        else:
            # 容错：非标准行（如 hosts 形式）取末段作为域名判断
            dom = line.split()[-1] if " " in line else line
        if apply_protection and is_protected(dom):
            protected += 1                # 保护域名：附加源中永不拦截
            continue
        blocks.add(line)
    return blocks, whites, total, protected


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
        blocks, whites, total, protected = load_rules(
            path, apply_protection=bool(src.get("optional")))
        per_source.append({**src, "total": total,
                           "blocks": len(blocks), "whites": len(whites),
                           "protected": protected})
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
    sum_protected = 0
    for s in per_source:
        sum_total += s["total"]
        sum_protected += s["protected"]
        extra = f"  protected={s['protected']}" if s["protected"] else ""
        print(f"{s['label']:<34} rules={s['total']:>7}  "
              f"(block {s['blocks']} / white {s['whites']}){extra}")
    print("==== Merge dedup result ====")
    print(f"Total input rule lines       : {sum_total}")
    print(f"Block rules after dedup      : {len(sorted_blocks)}")
    print(f"Whitelist rules after dedup  : {len(sorted_whites)}")
    print(f"Total after dedup            : {len(sorted_blocks) + len(sorted_whites)}")
    print(f"Duplicate lines removed      : {sum_total - len(sorted_blocks) - len(sorted_whites)}")
    print(f"Protected domains skipped    : {sum_protected}  (extra sources only)")
    print(f"Output file                  : {os.path.relpath(OUT_FILE, BASE_DIR)}  [{out_status}]")


if __name__ == "__main__":
    main()
