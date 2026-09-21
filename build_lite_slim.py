# -*- coding: utf-8 -*-
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw")
SRC_DIR = os.path.join(BASE_DIR, "sources")
OUT_DIR = os.path.join(BASE_DIR, "out")
FULL_FILE = os.path.join(OUT_DIR, "merged_dns_rules.txt")
DEFAULT_OUT = os.path.join(OUT_DIR, "merged_dns_rules_slim.txt")

sys.path.insert(0, BASE_DIR)
import integrate_sources as integ                                # noqa: E402

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

# 保底清单：无论去重收敛或裁剪如何，这些域名**必须**出现在最终产物中。
# 来源：slim 版校验时发现未被任何保留规则覆盖的国内广告域。
MUST_KEEP = (
    "tanx.com",          # 阿里妈妈广告交易平台（原易传媒 Tanx）
    "jiathis.com",       # 加网分享按钮（国内站点广泛使用）
    "ad.m.iqiyi.com",    # 爱奇艺移动端广告
    "ad.jia.360.cn",     # 360 广告投放域（仅拦此广告子域，不影响 360 主站）
)

# ---- 品牌域名保护（按用户要求）----
# 360 系列：**只拦广告子域**，主域与功能性域名（下载/更新/产品站）一律放行。
# 注意：这里必须列出奇虎 360 的自有域名；名字里含 "360" 的第三方站点
#      （camera360 / life360 / leads360 / 360doc / insta360 / 360buy 等）不在此列，照常拦截。
BRAND_360 = (
    "360.cn", "360.com", "360safe.com", "360shouji.com", "360os.com",
    "360totalsecurity.com", "qhimg.com", "qhmsg.com", "qhres.com",
    "360tpcdn.com", "so.com", "360kan.com",
)
# 360 域名中「广告/统计/推广」性质的标签：命中则**保留拦截**
AD_LABELS_360 = {
    "ad", "ads", "adapi", "adapter", "agd", "agd2", "iad", "cpull", "fenxi",
    "lianmeng", "union", "tf", "s", "sd", "se", "stat", "stats", "s1",
    "track", "tracking", "click", "dmp", "commercial", "tg", "shake", "leak",
    "look", "p", "pub", "huid", "show", "sdk", "sdkrec", "papi", "tr", "f",
    # 以下为校验时补录（360 的安装统计 / 游戏 / 网游推广域）
    "inst", "gamebox", "wan", "games", "m", "msg",
}
# 整域放行（含其子域）：简书被上游误判，按用户要求放行主站
ALLOW_DOMAINS = ("jianshu.com",)


def is_360_ad_subdomain(domain):
    """360 域名中，是否属于应保留拦截的广告/统计子域。

    - 主域与 www 子域 -> False（放行）
    - 含广告/统计标签的子域 -> True（保留拦截）
    - 其它子域（下载/更新/产品站）-> False（放行）
    """
    for b in BRAND_360:
        if domain == b or domain == "www." + b:
            return False
        if domain.endswith("." + b):
            prefix = domain[:-(len(b) + 1)]
            return bool(set(prefix.split(".")) & AD_LABELS_360)
    return False


def is_allowed_domain(domain):
    """是否属于「整域放行」的域名（自身或其子域）"""
    for a in ALLOW_DOMAINS:
        if domain == a or domain.endswith("." + a):
            return True
    return False


def drop_protected(domains):
    """移除品牌保护范围内的整域规则与功能性域名规则，返回 (保留集, 移除数)"""
    kept, removed = set(), 0
    for d in domains:
        under_360 = any(d == b or d.endswith("." + b) for b in BRAND_360)
        if under_360:
            if is_360_ad_subdomain(d):
                kept.add(d)          # 广告子域：保留拦截
            else:
                removed += 1         # 主域/功能域：放行
        elif is_allowed_domain(d):
            removed += 1             # 简书等：整域放行
        else:
            kept.add(d)
    return kept, removed


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
    allows = []
    if not os.path.exists(FULL_FILE):
        return allows
    with open(FULL_FILE, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("@@||") and line.endswith("^"):
                allows.append(line[4:-1])
    return allows


def drop_parent_covered(domains, keep=()):
    """删除已被更短父域规则覆盖的域名（AGH 中父域规则已覆盖其全部子域）。

    keep 中的域名永不删除（保底清单）。
    """
    keep = set(keep)
    s = set(domains)
    drop = set()
    for d in s:
        if d in keep:
            continue
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

    # ---- 0. 品牌保护（必须最先执行）----
    # 若不先剔除 ||360.cn^ / ||jianshu.com^ 这类整域规则，后续的父域收敛会把
    # 其下所有广告子域当作「已被父域覆盖」而删掉，导致广告子域也一并放行。
    all_domains, removed = drop_protected(all_domains)
    print(f"brand protection applied           : {len(all_domains)}  (-{removed})")

    # ---- 1. 无损：父域覆盖收敛（保底清单豁免）----
    stage1 = drop_parent_covered(all_domains, keep=MUST_KEEP)
    print(f"after parent-covered removal       : {len(stage1)}  (-{len(all_domains)-len(stage1)})")

    # ---- 2. 无损：白名单冲突清理 ----
    # 仅剔除「规则自身就在白名单中」的域名。若白名单豁免的是子域
    # （如 @@||5471782.fls.doubleclick.net^），父域规则 ||doubleclick.net^ 仍应保留：
    # AGH 中白名单优先级更高，子域例外会自动生效。
    allow_set = set(load_full_allows())
    stage2 = {d for d in stage1 if d not in allow_set}
    print(f"after whitelist conflict removal   : {len(stage2)}  (-{len(stage1)-len(stage2)})")

    # ---- 3. 保底清单：不在池中的直接补入 ----
    missing_keep = [d for d in MUST_KEEP if d not in stage2]
    for d in missing_keep:
        stage2.add(d)
        value[d] = max(value[d], 100)      # 给最高价值分，确保排序时位于最前
        consensus[d] = max(consensus[d], 99)
    if missing_keep:
        print(f"must-keep injected                 : +{len(missing_keep)}  {missing_keep}")
    else:
        print("must-keep injected                 : (all already present)")

    # ---- 4. 有损：按价值排序（--max>0 时才裁剪）----
    def sort_key(d):
        cn_bonus = 1 if d.endswith(".cn") else 0
        return (-value[d], -consensus[d], -cn_bonus, d.count("."), len(d), d)

    ordered = sorted(stage2, key=sort_key)
    if args.max and len(ordered) > args.max:
        selected = ordered[:args.max]
        # 保底清单强制保留（即使被挤出配额）
        keepset = set(MUST_KEEP)
        selected = list(dict.fromkeys(list(selected) + [d for d in MUST_KEEP if d in ordered]))
        print(f"after value-based truncation       : {len(selected)}  (-{len(ordered)-len(selected)})")
    else:
        selected = ordered
        print(f"no truncation (kept all)           : {len(selected)}")

    # 裁剪后可能出现新的父域冗余，再收敛一次（保底清单豁免）
    final = drop_parent_covered(selected, keep=MUST_KEEP)
    if len(final) < len(selected):
        print(f"after final parent collapse        : {len(final)}  (-{len(selected)-len(final)})")

    # 最终确保保底清单存在
    for d in MUST_KEEP:
        final.add(d)

    sorted_blocks = sorted(final)
    sorted_allows = sorted(allow_set)

    out_path = args.out if os.path.isabs(args.out) else os.path.join(BASE_DIR, args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("!\n")
        fh.write("! Title: Merged DNS blocklist - SLIM (China sources only, low-memory)\n")
        fh.write("! Description: 面向 229MB 级内存软路由的极简规则集；仅使用国内规则源，\n")
        fh.write("!              已做父域无损收敛 + 白名单冲突消除 + 价值排序裁剪；\n")
        fh.write("!              与全量/lite 版共用同一份白名单\n")
        fh.write(f"! Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        fh.write(f"! Block rules: {len(sorted_blocks)}\n")
        fh.write(f"! Whitelist rules: {len(sorted_allows)}\n")
        fh.write(f"! Max limit: {args.max if args.max else 'none (lossless dedup only)'}\n")
        fh.write("! Must-keep (never dropped): " + ", ".join(MUST_KEEP) + "\n")
        fh.write("! Sources (China only):\n")
        for name, weight, nb in per_source:
            fh.write(f"!   - {name} [w={weight}] block {nb}\n")
        fh.write("! Excluded international sources:\n")
        fh.write("!   AdAway, Mvps, YousList, StevenBlack, EasyList, EasyPrivacy(x2),\n")
        fh.write("!   I-dont-care-about-cookies, Adblock-Warning-Removal-List\n")
        fh.write("!\n")
        fh.write("\n".join("||" + d + "^" for d in sorted_blocks))
        fh.write("\n")
        if sorted_allows:
            fh.write("\n".join("@@" + "||" + d + "^" for d in sorted_allows))
            fh.write("\n")

    print()
    print("==== slim result ====")
    print(f"block rules   : {len(sorted_blocks)}")
    print(f"whitelist     : {len(sorted_allows)}")
    cn = sum(1 for d in sorted_blocks if d.endswith(".cn"))
    print(f"  .cn domains : {cn}")
    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"file size     : {size_mb:.2f} MB")
    print(f"output        : {os.path.relpath(out_path, BASE_DIR)}")


if __name__ == "__main__":
    main()
