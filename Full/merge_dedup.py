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

# 复用公共模块中的手写名单解析逻辑（Lite / Slim 同样使用它）
sys.path.insert(0, ROOT_DIR)
from integrate_sources import (                                   # noqa: E402
    WHITELIST_FILE, BLOCKLIST_FILE, MIXED_FILE,
    parse_domain, load_manual_list, load_mixed_list,
)

# Source definitions
# 「附加源整合产物」这个条目由 build_sources() 按版本注入，因为 Full 与 Pro
# 使用不同的整合文件（integrated_extra.txt / integrated_extra_pro.txt）。
def build_sources(extra_path, extra_label, extra_url):
    return [
        {"label": "URLHaus (AdGuard Hostlists #11)", "file": "filter_11.txt",
         "url": "https://adguardteam.github.io/HostlistsRegistry/assets/filter_11.txt"},
        {"label": "GOODBYEADS dns", "file": "goodbyeads_dns.txt",
         "url": "https://github.com/8680/GOODBYEADS (mirror ghfast.top)"},
        {"label": "AdBlock DNS (217heidai)", "file": "adblockdns.txt",
         "url": "https://github.com/217heidai/adblockfilters"},
        {"label": extra_label, "file": os.path.basename(extra_path),
         "path": extra_path, "url": extra_url, "optional": True},
    ]


FULL_EXTRA_LABEL = "Integrated extra sources (18 lists)"
FULL_EXTRA_URL = ("yhosts / ad-wars / 1024_hosts / AdAway / YousList / StevenBlack / "
                  "anti-AD / EasyList family / ADgk / CJX / mvps / "
                  "i-dont-care-about-cookies / Adblock Warning Removal List")

SOURCES = build_sources(os.path.join(OUT_DIR, "integrated_extra.txt"),
                        FULL_EXTRA_LABEL, FULL_EXTRA_URL)

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


def main(out_file=None, sources=None, title=None, description=None):
    out_file = out_file or OUT_FILE
    sources = sources if sources is not None else SOURCES
    title = title or "Merged DNS blocklist (line-level dedup)"
    per_source = []
    all_blocks, all_whites = set(), set()

    # ---- 手动维护的名单（优先级高于上游）----
    # 优先级：whitelist.txt > mixed.txt 的 @@ 放行 > blocklist.txt
    #         > mixed.txt 的拦截 > 上游源
    manual_whitelist, wl_bad = load_manual_list(WHITELIST_FILE)
    manual_blocklist, bl_bad = load_manual_list(BLOCKLIST_FILE)
    mixed_allow, mixed_block, mx_bad = load_mixed_list(MIXED_FILE)

    for path, bad in ((WHITELIST_FILE, wl_bad),
                      (BLOCKLIST_FILE, bl_bad),
                      (MIXED_FILE, mx_bad)):
        for lineno, text in bad:
            print(f"[WARN] {os.path.relpath(path, ROOT_DIR)}:{lineno} "
                  f"无法解析，已忽略: {text}", file=sys.stderr)

    # 手写名单之间冲突时一律以「放行」为准
    manual_conflict = manual_whitelist & manual_blocklist
    if manual_conflict:
        for d in sorted(manual_conflict):
            print(f"[WARN] 域名同时出现在 whitelist 与 blocklist，按白名单处理: {d}",
                  file=sys.stderr)
        manual_blocklist -= manual_conflict

    # mixed.txt 的放行条目与 whitelist.txt 同级；其拦截条目则在 blocklist 之后
    mixed_conflict = (mixed_allow & manual_blocklist) | (mixed_block & manual_whitelist)
    if mixed_conflict:
        for d in sorted(mixed_conflict):
            print(f"[WARN] 域名在 mixed.txt 与单用途名单中冲突，按放行处理: {d}",
                  file=sys.stderr)
    manual_blocklist -= mixed_allow
    mixed_block -= manual_whitelist
    mixed_block -= mixed_allow

    # 合并后的总白名单 / 总拦截（手写部分）
    manual_whitelist_all = manual_whitelist | mixed_allow
    manual_blocklist_all = manual_blocklist | mixed_block

    for src in sources:
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

    # ---- 把手写拦截名单并入黑名单 ----
    for d in manual_blocklist_all:
        all_blocks.add("||" + d + "^")

    # ---- 手写白名单：加入白名单，并从黑名单中移除同名条目 ----
    for d in manual_whitelist_all:
        all_whites.add("@@||" + d + "^")

    # 上游黑名单中与手写白名单冲突的条目一律移除（含其子域，避免父域规则继续拦截）
    manual_wl_removed = 0
    for rule in list(all_blocks):
        dom = rule[2:-1] if rule.startswith("||") and rule.endswith("^") else None
        if dom and (dom in manual_whitelist_all
                    or any(dom.endswith("." + w) for w in manual_whitelist_all)):
            all_blocks.discard(rule)
            manual_wl_removed += 1

    sorted_blocks = sorted(all_blocks)
    sorted_whites = sorted(all_whites)

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    header = [
        "!",
        f"! Title: {title}",
        description or (f"! Description: {len(per_source)} 个源按整行精确去重合并，"
                        f"白名单(@@)规则保留在文件末尾"),
        f"! Generated: {stamp}",
        f"! Block rules: {len(sorted_blocks)}",
        f"! Whitelist rules: {len(sorted_whites)}",
        "!",
    ]
    header += [f"! Source {i + 1}: {s['label']}  <-  {s['url']}"
               for i, s in enumerate(per_source)]
    header += [
        f"! Manual whitelist: Lists/whitelist.txt  ({len(manual_whitelist)} domains)",
        f"! Manual blocklist: Lists/blocklist.txt  ({len(manual_blocklist)} domains)",
        f"! Manual mixed    : Lists/mixed.txt  "
        f"(allow {len(mixed_allow)} / block {len(mixed_block)})",
    ]
    header.append("!")

    body = sorted_blocks + sorted_whites
    new_text = "\n".join(header + body + [""])

    # Rewrite only when something besides the generated timestamp changed,
    # so a scheduled run with identical rules creates no git commit.
    def content_key(text):
        return [ln for ln in text.splitlines()
                if not ln.startswith("! Generated:")]

    changed = True
    if os.path.exists(out_file):
        with open(out_file, "r", encoding="utf-8") as f:
            old_text = f.read()
        changed = content_key(old_text) != content_key(new_text)
    if changed:
        with open(out_file, "w", encoding="utf-8", newline="\n") as f:
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
    print(f"Manual whitelist domains     : {len(manual_whitelist)}  (Lists/whitelist.txt)")
    print(f"Manual blocklist domains     : {len(manual_blocklist)}  (Lists/blocklist.txt)")
    print(f"Manual mixed allow/block     : {len(mixed_allow)} / {len(mixed_block)}  (Lists/mixed.txt)")
    if manual_conflict:
        print(f"  whitelist/blocklist clashes: {len(manual_conflict)}  (whitelist wins)")
    if mixed_conflict:
        print(f"  mixed-vs-single clashes    : {len(mixed_conflict)}  (allow wins)")
    print(f"Upstream blocks removed by manual whitelist: {manual_wl_removed}")
    print(f"Total input rule lines       : {sum_total}")
    print(f"Block rules after dedup      : {len(sorted_blocks)}")
    print(f"Whitelist rules after dedup  : {len(sorted_whites)}")
    print(f"Total after dedup            : {len(sorted_blocks) + len(sorted_whites)}")
    print(f"Duplicate lines removed      : {sum_total - len(sorted_blocks) - len(sorted_whites)}")
    print(f"Output file                  : {os.path.relpath(out_file, ROOT_DIR)}  [{out_status}]")


if __name__ == "__main__":
    main()
