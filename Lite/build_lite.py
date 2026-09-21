# -*- coding: utf-8 -*-
# build_lite.py
# 生成 lite 版规则：面向极低配置软路由的精简列表，优先保留国内域名拦截。
#
# 设计约束：
#   - 全量产物 out/merged_dns_rules.txt 由 merge_dedup.py 生成，本脚本**只读取、不修改**，
#     也不影响其任何输入，两套列表完全并行
#   - 与全量不冲突：lite 屏蔽集会剔除全量白名单中的域名，白名单直接沿用全量，
#     因此不会出现「lite 拦截 / 全量放行」的矛盾
#   - lite 专用上游使用 217 的 Lite 版（仅国内域名），与全量所用的完整版互不影响
#
# 运行顺序要求：必须在 merge_dedup.py 之后执行（需要全量产物作白名单基准）
#
# 用法:
#   py build_lite.py                  # 输出全部国内向源
#   py build_lite.py --max 120000     # 超限时按优先级裁剪
#   py build_lite.py --no-security    # 不纳入 URLHaus 安全源

import argparse
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))            # Lite/
ROOT_DIR = os.path.dirname(BASE_DIR)                             # 项目根目录
RAW_DIR = os.path.join(ROOT_DIR, "Cache", "raw")
SRC_DIR = os.path.join(ROOT_DIR, "Cache", "sources")
OUT_DIR = os.path.join(ROOT_DIR, "out")
FULL_FILE = os.path.join(OUT_DIR, "merged_dns_rules.txt")
OUT_FILE = os.path.join(OUT_DIR, "merged_dns_rules_lite.txt")

sys.path.insert(0, ROOT_DIR)
import integrate_sources as integ                                # noqa: E402

# 国内向源：(标识, 路径, 说明, 优先级) —— 优先级数字越小越先保留
CN_SOURCES = (
    ("adblockdnslite", os.path.join(RAW_DIR, "adblockdnslite.txt"), "217 Lite（仅国内域名）", 1),
    ("anti-ad", os.path.join(SRC_DIR, "anti-ad.txt"), "anti-AD（国内优质）", 2),
    ("adgk", os.path.join(SRC_DIR, "adgk.txt"), "ADgk（国内）", 2),
    ("easylistchina", os.path.join(SRC_DIR, "easylistchina.txt"), "EasyList China", 2),
    ("yhosts", os.path.join(SRC_DIR, "yhosts.txt"), "yhosts（国内站点）", 2),
    ("ad-wars", os.path.join(SRC_DIR, "ad-wars.txt"), "大圣净化（国内视频）", 2),
    ("cjx-annoyance", os.path.join(SRC_DIR, "cjx-annoyance.txt"), "CJX's Annoyance", 3),
    ("xinggsf-rule", os.path.join(SRC_DIR, "xinggsf-rule.txt"), "乘风规则", 3),
    ("xinggsf-mv", os.path.join(SRC_DIR, "xinggsf-mv.txt"), "乘风视频规则", 3),
    ("goodbyeads_dns", os.path.join(RAW_DIR, "goodbyeads_dns.txt"), "GOODBYEADS（国内项目）", 3),
    ("1024_hosts", os.path.join(SRC_DIR, "1024_hosts.txt"), "1024_hosts（成人/赌博站点）", 4),
)
SECURITY_SOURCES = (
    ("filter_11", os.path.join(RAW_DIR, "filter_11.txt"), "URLHaus（恶意网站/钓鱼）", 5),
)


def load_source(path):
    """清洗单个源，返回 (block 域名集合, allow 域名集合)"""
    blocks, whites = set(), set()
    if not os.path.exists(path):
        return blocks, whites
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    for line in text.splitlines():
        kind, payload = integ.parse_line(line)
        if kind == "block":
            for d in payload:
                if integ.valid_domain(d):
                    blocks.add(d)
        elif kind == "allow":
            if integ.valid_domain(payload):
                whites.add(payload)
    return blocks, whites


def load_full_output():
    """读取全量产物，返回 (block 域名集合, allow 域名列表)"""
    blocks, allows = set(), []
    if not os.path.exists(FULL_FILE):
        return blocks, allows
    with open(FULL_FILE, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("@@||") and line.endswith("^"):
                allows.append(line[4:-1])
            elif line.startswith("||") and line.endswith("^"):
                blocks.add(line[2:-1])
    return blocks, allows


def main():
    ap = argparse.ArgumentParser(description="Build the lite DNS rule set")
    ap.add_argument("--max", type=int, default=0,
                    help="规则数上限，超出时按优先级裁剪（0 = 不裁剪）")
    ap.add_argument("--no-security", action="store_true",
                    help="不纳入 URLHaus 安全源")
    args = ap.parse_args()

    sources = list(CN_SOURCES) + ([] if args.no_security else list(SECURITY_SOURCES))

    origin_prio = {}
    per_source = []
    for name, path, desc, prio in sources:
        blocks, whites = load_source(path)
        per_source.append((name, desc, prio, len(blocks), len(whites)))
        for d in blocks:
            cur = origin_prio.get(d)
            if cur is None or prio < cur:
                origin_prio[d] = prio

    full_blocks, full_allows = load_full_output()
    if not full_allows:
        print("[WARN] out/merged_dns_rules.txt not found or empty - "
              "run merge_dedup.py first for whitelist consistency", file=sys.stderr)

    # ---- 冲突消除：全量白名单中的域名不得出现在 lite 屏蔽集中 ----
    allow_set = set(full_allows)
    dropped_by_whitelist = {d for d in origin_prio if d in allow_set}
    candidates = {d: p for d, p in origin_prio.items() if d not in allow_set}

    # ---- 规模控制 ----
    truncated = 0
    if args.max and len(candidates) > args.max:
        ordered = sorted(candidates.items(),
                         key=lambda kv: (kv[1],
                                         0 if kv[0].endswith(".cn") else 1,
                                         len(kv[0]), kv[0]))
        candidates = dict(ordered[:args.max])
        truncated = len(origin_prio) - len(dropped_by_whitelist) - len(candidates)

    sorted_blocks = sorted(candidates)
    sorted_allows = sorted(allow_set)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("!\n")
        fh.write("! Title: Merged DNS blocklist - LITE (China-focused)\n")
        fh.write("! Description: 面向极低配置软路由的精简规则，优先保留国内域名拦截；\n")
        fh.write("!              已排除翻墙类内容，白名单与全量版 merged_dns_rules.txt 保持一致\n")
        fh.write(f"! Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        fh.write(f"! Block rules: {len(sorted_blocks)}\n")
        fh.write(f"! Whitelist rules: {len(sorted_allows)}\n")
        fh.write("! Sources (China-focused only):\n")
        for name, desc, prio, nb, nw in per_source:
            fh.write(f"!   - {name}: {desc} (block {nb} / white {nw}, priority {prio})\n")
        fh.write("!\n")
        fh.write("\n".join("||" + d + "^" for d in sorted_blocks))
        fh.write("\n")
        if sorted_allows:
            fh.write("\n".join("@@" + "||" + d + "^" for d in sorted_allows))
            fh.write("\n")

    print("==== lite: per-source ====")
    for name, desc, prio, nb, nw in per_source:
        print(f"  P{prio} {name:<18} block={nb:>7}  white={nw:>3}")
    print("==== lite: result ====")
    print(f"merged unique blocks           : {len(sorted_blocks)}")
    print(f"whitelist (inherited from full) : {len(sorted_allows)}")
    print(f"dropped by full whitelist       : {len(dropped_by_whitelist)}")
    if truncated:
        print(f"truncated by --max {args.max:<9}: {truncated}")
    cn = sum(1 for d in sorted_blocks if d.endswith(".cn"))
    print(f"  of which .cn domains          : {cn}")
    if full_blocks:
        print(f"full list size (unchanged)      : {len(full_blocks)}")
        print(f"lite / full                     : {len(sorted_blocks)*100//max(1,len(full_blocks))}%")
    print(f"output                          : {os.path.relpath(OUT_FILE, ROOT_DIR)}")


if __name__ == "__main__":
    main()
