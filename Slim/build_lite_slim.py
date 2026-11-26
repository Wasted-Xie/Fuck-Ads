# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Wasted-Xie
#
# 本脚本采用 MIT 许可，详见仓库根目录 LICENSE 文件。
# 注意：脚本生成的 out/ 规则产物汇编自多个上游黑名单，其许可为 GPL-3.0，
#       详见 LICENSE-GPL-3.0 与 README「许可协议」一节。
# build_lite_slim.py
# 生成「极简版」规则集，面向 229MB 级内存的低配软路由。
#
# 源选择依据（最原始上游 otobtc/ADhosts 的推荐列表，逐项判定国内外）：
#   https://github.com/otobtc/ADhosts
#   —— 只保留国内规则源，剔除全部国际规则源（见下方 SOURCES 注释）
#
# 压缩策略（依次叠加）：
#   1. 无损：删除已被更短父域规则覆盖的子域（AGH 中 ||a.com^ 已覆盖 b.a.com）
#   2. 无损：剔除规则自身出现在白名单中的域名（子域级白名单不影响父域规则）
#   3. 有损：按「源权重 → 多源共识 → .cn → 层级浅」排序后裁剪到目标条数
#
# 用法:
#   py build_lite_slim.py                  # 默认上限 100000
#   py build_lite_slim.py --max 80000
#   py build_lite_slim.py --with-security  # 额外纳入 URLHaus 安全源（国际源，默认不含）

import argparse
import collections
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))            # Slim/
ROOT_DIR = os.path.dirname(BASE_DIR)                             # 项目根目录
RAW_DIR = os.path.join(ROOT_DIR, "Cache", "raw")
SRC_DIR = os.path.join(ROOT_DIR, "Cache", "sources")
OUT_DIR = os.path.join(ROOT_DIR, "out")
FULL_FILE = os.path.join(OUT_DIR, "merged_dns_rules.txt")
DEFAULT_OUT = os.path.join(OUT_DIR, "merged_dns_rules_slim.txt")

sys.path.insert(0, ROOT_DIR)
import integrate_sources as integ                                # noqa: E402
from integrate_sources import (                                   # noqa: E402
    BLOCKLIST_FILE, APPEND_FILE, load_manual_list, load_verbatim_rules,
    rule_domain, whitelist_rule,
)

# 国内规则源：(源名, 路径, 权重)
#   权重越高，越优先保留其规则
SOURCES = (
    ("adblockdnslite", os.path.join(RAW_DIR, "adblockdnslite.txt"), 5),   # 217 Lite，仅国内域名
    ("anti-ad", os.path.join(SRC_DIR, "anti-ad.txt"), 5),                 # 国内优质综合源
    ("yhosts", os.path.join(SRC_DIR, "yhosts.txt"), 4),                   # 国内站点广告
    ("adgk", os.path.join(SRC_DIR, "adgk.txt"), 3),                       # 国内去广告
    ("easylistchina", os.path.join(SRC_DIR, "easylistchina.txt"), 3),     # EasyList 中文版
    ("ad-wars", os.path.join(SRC_DIR, "ad-wars.txt"), 3),                 # 大圣净化，国内视频
    ("goodbyeads_dns", os.path.join(RAW_DIR, "goodbyeads_dns.txt"), 3),   # 国内项目
    ("cjx-annoyance", os.path.join(SRC_DIR, "cjx-annoyance.txt"), 2),     # 中文向补充
    ("xinggsf-rule", os.path.join(SRC_DIR, "xinggsf-rule.txt"), 2),       # 乘风规则
    ("xinggsf-mv", os.path.join(SRC_DIR, "xinggsf-mv.txt"), 2),           # 乘风视频规则
    ("1024_hosts", os.path.join(SRC_DIR, "1024_hosts.txt"), 1),           # 中文成人/赌博站点
)
# 剔除的国际规则源（记录在此，便于审计；不参与构建）：
#   AdAway / Mvps(美欧) / YousList(韩国) / StevenBlack(国外) /
#   EasyList(英文) / EasyList Privacy ×2(隐私追踪) /
#   I don't care about cookies / Adblock Warning Removal List
# 其它已排除的源：
#   googlehosts(翻墙加速) / hblock(国内网络不可达) / halflife(已失效) /
#   Koolproxy 与 Adbyby(代理端规则格式，非 DNS 规则)

# 安全类国际源（默认不纳入，需 --with-security）
SECURITY_SOURCES = (
    ("filter_11", os.path.join(RAW_DIR, "filter_11.txt"), 2),             # URLHaus 恶意网站
)

# 注 1：本脚本不再对任何域名做硬编码放行。
# 需要放行某个域名时，写进 Lists/whitelist.txt 即可——它参与全部四个版本的构建，
# 且输出为 @@||d^$important，优先级高于任何拦截规则。
#
# 注 2：曾有一个 MUST_KEEP 保底清单（tanx.com / jiathis.com / ad.m.iqiyi.com /
# ad.jia.360.cn），用于豁免父域收敛与 --max 裁剪。该清单已移除：
#   - 这 4 个域名都由上游源正常提供，无需硬编码兜底
#   - ad.jia.360.cn 虽会被 ||360.cn^ 收敛掉，但拦截效果不受影响（父域已覆盖）
# 若将来需要确保某条规则不被收敛/裁剪，写进 Lists/blocklist.txt——它在收敛之后注入，
# 且给最高价值分，效果等价。


def load_source(path):
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


def load_full_allows():
    """读取 Full 产物中的白名单域名。

    注意：Full 产物里的白名单带 $important（@@||d^$important），
    不能用 endswith("^") 判断，否则会被全部漏掉。
    """
    allows = []
    if not os.path.exists(FULL_FILE):
        return allows
    with open(FULL_FILE, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line.startswith("@@") or line.startswith("!"):
                continue
            d = rule_domain(line)
            if d:
                allows.append(d)
    return allows


def drop_parent_covered(domains):
    """删除已被更短父域规则覆盖的域名（AGH 中父域规则已覆盖其全部子域）。

    例：集合中存在 a.com 时，b.a.com 会被删除——a.com 的规则已覆盖它，
    拦截能力不受影响。
    """
    s = set(domains)
    drop = set()
    for d in s:
        parts = d.split(".")
        for i in range(1, len(parts) - 1):
            if ".".join(parts[i:]) in s:
                drop.add(d)
                break
    return s - drop


def main():
    ap = argparse.ArgumentParser(description="Build the slim DNS rule set (China sources only)")
    ap.add_argument("--max", type=int, default=0,
                    help="规则条数上限；0（默认）= 不裁剪，仅做无损去重")
    ap.add_argument("--out", default=DEFAULT_OUT, help="输出文件路径")
    ap.add_argument("--with-security", action="store_true",
                    help="额外纳入 URLHaus 安全源（国际源，默认不纳入）")
    args = ap.parse_args()

    sources = list(SOURCES) + (list(SECURITY_SOURCES) if args.with_security else [])

    per_source = []
    value = collections.Counter()          # 源权重累加
    consensus = collections.Counter()      # 被多少个源收录
    all_domains = set()

    for name, path, weight in sources:
        blocks, _ = load_source(path)
        per_source.append((name, weight, len(blocks)))
        for d in blocks:
            all_domains.add(d)
            value[d] += weight
            consensus[d] += 1

    print(f"sources used                       : {len(sources)} (China only)")
    print(f"candidate domains (raw union)      : {len(all_domains)}")

    # ---- 1. 无损：父域覆盖收敛 ----
    stage1 = drop_parent_covered(all_domains)
    print(f"after parent-covered removal       : {len(stage1)}  (-{len(all_domains)-len(stage1)})")

    # ---- 2. 无损：白名单冲突清理 ----
    # 仅剔除「规则自身就在白名单中」的域名。若白名单豁免的是子域
    # （如 @@||5471782.fls.doubleclick.net^），父域规则 ||doubleclick.net^ 仍应保留：
    # AGH 中白名单优先级更高，子域例外会自动生效。
    allow_set = set(load_full_allows())
    stage2 = {d for d in stage1 if d not in allow_set}
    print(f"after whitelist conflict removal   : {len(stage2)}  (-{len(stage1)-len(stage2)})")

    # ---- 3. 手动维护的拦截名单（Lists/blocklist.txt）----
    # 放在白名单冲突清理之后注入，确保手写条目不会被白名单剔除；
    # 同时给最高价值分，使其在 --max 裁剪时也不会被挤出。
    # 注 1：手写白名单无需在此处理 —— 它已写入 Full 产物，上面的 allow_set 已包含。
    # 注 2：Lists/Append.txt 走「原样透传」，不在此处解析为域名，见下方写文件部分。
    manual_blocks, bl_bad = load_manual_list(BLOCKLIST_FILE)
    for lineno, text in bl_bad:
        print(f"[WARN] Lists/blocklist.txt:{lineno} 无法解析，已忽略: {text}",
              file=sys.stderr)
    manual_blocks -= allow_set              # 兜底：不与 Full 白名单冲突
    manual_added = sorted(d for d in manual_blocks if d not in stage2)
    for d in manual_added:
        stage2.add(d)
        value[d] = max(value[d], 100)
        consensus[d] = max(consensus[d], 99)
    print(f"manual blocklist injected          : {len(manual_blocks)} domains"
          f"  (+{len(manual_added)} new)")

    # Append.txt 原文透传（全部行，含注释与带修饰符的规则）
    append_vlines, append_nrules, append_ncomments = load_verbatim_rules(APPEND_FILE)

    # ---- 4. 有损：按价值排序（--max>0 时才裁剪）----
    def sort_key(d):
        cn_bonus = 1 if d.endswith(".cn") else 0
        return (-value[d], -consensus[d], -cn_bonus, d.count("."), len(d), d)

    ordered = sorted(stage2, key=sort_key)
    if args.max and len(ordered) > args.max:
        selected = ordered[:args.max]
        print(f"after value-based truncation       : {len(selected)}  (-{len(ordered)-len(selected)})")
    else:
        selected = ordered
        print(f"no truncation (kept all)           : {len(selected)}")

    # 裁剪后可能出现新的父域冗余，再收敛一次
    final = drop_parent_covered(selected)
    if len(final) < len(selected):
        print(f"after final parent collapse        : {len(final)}  (-{len(selected)-len(final)})")

    sorted_blocks = sorted(final)
    sorted_allows = sorted(allow_set)

    out_path = args.out if os.path.isabs(args.out) else os.path.join(BASE_DIR, args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    header = [
        "!",
        "! Title: Merged DNS blocklist - SLIM (China sources only, low-memory)",
        "! Description: 面向 229MB 级内存软路由的极简规则集；仅使用国内规则源，",
        "!              已做父域无损收敛 + 白名单冲突消除 + 价值排序裁剪；",
        "!              与全量/lite 版共用同一份白名单",
        f"! Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"! Block rules: {len(sorted_blocks)}",
        f"! Whitelist rules: {len(sorted_allows)}",
        f"! Max limit: {args.max if args.max else 'none (lossless dedup only)'}",
        "! Sources (China only):",
    ]
    header += [f"!   - {name} [w={weight}] block {nb}" for name, weight, nb in per_source]
    header += [
        "! Excluded international sources:",
        "!   AdAway, Mvps, YousList, StevenBlack, EasyList, EasyPrivacy(x2),",
        "!   I-dont-care-about-cookies, Adblock-Warning-Removal-List",
        "!",
    ]

    body = ["||" + d + "^" for d in sorted_blocks]
    if sorted_allows:
        # 白名单带 $important：Append.txt 里存在 ||d^$important 形态的拦截规则，
        # 普通 @@||d^ 优先级不足以覆盖它们（AdGuard 优先级：
        # $important 例外 > $important 拦截 > 普通例外 > 普通拦截）。
        body += [whitelist_rule(d) for d in sorted_allows]

    # Append.txt 原样透传（含注释分组、$ 修饰符与 * 通配符）
    append_section = []
    if append_vlines:
        append_section = ["", "! ==== Lists/Append.txt (verbatim) ===="]
        append_section += append_vlines

    new_text = "\n".join(header + body + append_section) + "\n"

    # 与 Full/merge_dedup.py 保持一致：除生成时间戳外内容未变时不重写文件，
    # 避免定时任务产生无意义的提交。
    def content_key(text):
        return [ln for ln in text.splitlines()
                if not ln.startswith("! Generated:")]

    changed = True
    if os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            changed = content_key(f.read()) != content_key(new_text)
    if changed:
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(new_text)
        out_status = "written (content changed)"
    else:
        out_status = "unchanged - file kept as-is"

    print()
    print("==== slim result ====")
    print(f"block rules   : {len(sorted_blocks)}")
    print(f"whitelist     : {len(sorted_allows)}")
    cn = sum(1 for d in sorted_blocks if d.endswith(".cn"))
    print(f"  .cn domains : {cn}")
    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"file size     : {size_mb:.2f} MB")
    print(f"output        : {os.path.relpath(out_path, ROOT_DIR)}  [{out_status}]")


if __name__ == "__main__":
    main()
