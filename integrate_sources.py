# -*- coding: utf-8 -*-
# integrate_sources.py
# 从 sources/ 下的附加上游规则源中提取「可用的域名规则」，排除翻墙/加速/解锁类条目，
# 输出 out/integrated_extra.txt，供 merge_dedup.py 作为附加源参与最终合并。
#
# 判定规则：
#   hosts 行 (IP + 域名)：
#       - IP 是 0.0.0.0 / 127.0.0.1 / ::1 等本地地址 -> 屏蔽，转成 ||domain^
#       - IP 是其它地址                        -> 重定向(翻墙/加速/解锁)，排除并单独记录
#   adblock 网络规则 ||domain^ / |http://domain^ -> 保留（仅接受纯域名，带路径的一律丢弃）
#   adblock 白名单  @@||domain^                  -> 保留（带修饰符的场景限定豁免一律丢弃）
#   含 $domain= / $app= 修饰符的规则             -> 丢弃（限定型，抽成整域会严重放大范围）
#   元素隐藏规则 (##, #@#, #?#, #$#, #%#)        -> 跳过（DNS 层无效）
#   正则规则 /regex/                             -> 跳过（DNS 层无法表达）
#   注释行 (! 或 #)                              -> 跳过
#
# 用法: py integrate_sources.py

import os
import re
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "sources")
OUT_DIR = os.path.join(BASE_DIR, "out")
OUT_RULES = os.path.join(OUT_DIR, "integrated_extra.txt")
OUT_EXCLUDED = os.path.join(OUT_DIR, "excluded_redirect_entries.txt")

# 整体排除的源（本身就是翻墙/加速专用，不含去广告内容）
EXCLUDE_SOURCES = {"googlehosts"}

LOCAL_IPS = {
    "0.0.0.0", "127.0.0.1", "::1", "::", "0:0:0:0:0:0:0:0",
    "255.255.255.255", "0.0.0.0.0",
}
SYSTEM_NAMES = {
    "localhost", "localhost.localdomain", "local", "broadcasthost",
    "ip6-localhost", "ip6-loopback", "ip6-allnodes", "ip6-allrouters",
    "ip6-localnet", "ip6-mcastprefix",
}
COSMETIC_MARKS = ("##", "#@#", "#?#", "#$#", "#%#", "#@$#", "#@?#")
DOMAIN_RE = re.compile(r"^[a-zA-Z0-9*][a-zA-Z0-9._*\-]*$")
HOSTS_RE = re.compile(r"^([0-9a-fA-F:.]{2,})\s+(\S+)")
ADB_DOMAIN_RE = re.compile(r"^\|\|([a-zA-Z0-9._*\-]+)\^?(?=$|\$)")
ADB_URL_RE = re.compile(r"^\|https?://([a-zA-Z0-9._*\-]+)\^?(?=$|\$)")
IP_LIKE_RE = re.compile(r"^[0-9.]+$")
# 形如 *.js / *.png 的「文件扩展名式」规则不是域名，必须拒绝
BAD_LAST_LABELS = {
    "js", "css", "png", "jpg", "jpeg", "gif", "swf", "mp4", "mp3", "webp",
    "svg", "ico", "json", "xml", "html", "htm", "php", "asp", "aspx", "txt",
    "woff", "woff2", "ttf", "eot", "apk", "exe", "dll", "zip", "rar", "gz",
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "csv", "wasm", "map",
    "m3u8", "ts", "flv", "avi", "mkv", "torrent", "bin", "dat", "log",
}


def valid_domain(d):
    """域名有效性检查"""
    if not d or len(d) > 255:
        return False
    if "." not in d:
        return False
    if d in SYSTEM_NAMES:
        return False
    if IP_LIKE_RE.match(d):
        return False
    if not DOMAIN_RE.match(d):
        return False
    if d.startswith(".") or d.endswith(".") or ".." in d:
        return False
    if d.startswith("*."):
        rest = d[2:]
        # 拒绝 *.com / *.net 这类过宽通配
        if "." not in rest:
            return False
    # 拒绝 *.js / *.png 这类扩展名式规则
    if d.rsplit(".", 1)[-1].lower() in BAD_LAST_LABELS:
        return False
    return True


def extract_adblock_domain(rule):
    """从 adblock 网络规则中提取纯域名，失败返回 None"""
    body = rule
    if "$" in body:
        head, mods = body.split("$", 1)
        # $domain= / $app= 是「仅特定站点/应用生效」的限定修饰符，
        # 抽成整域拦截会严重放大范围（例：||baidu.com^$domain=pos.baidu.com），必须丢弃
        if re.search(r"(^|,)\s*(domain|app)=", mods):
            return None
        body = head
    m = ADB_DOMAIN_RE.match(body)
    if m:
        return m.group(1)
    m = ADB_URL_RE.match(body)
    if m:
        return m.group(1)
    return None


def parse_line(line):
    """返回 (kind, payload)；kind ∈ block/allow/redirect/skip"""
    s = line.strip()
    if not s:
        return ("skip", "blank")
    if s.startswith("!") or s.startswith("#"):
        return ("skip", "comment")
    # 元素隐藏 / 脚本注入类规则
    for mark in COSMETIC_MARKS:
        if mark in s:
            return ("skip", "cosmetic")
    # adblock 白名单
    if s.startswith("@@"):
        body = s[2:]
        # 带修饰符的白名单是「场景限定豁免」（$generichide / $popup / $domain= 等），
        # DNS 层无法表达该限定；转成无条件豁免会放行本该拦截的广告域，故直接丢弃
        if "$" in body:
            return ("skip", "other")
        dom = extract_adblock_domain(body)
        return ("allow", dom) if dom else ("skip", "other")
    # adblock 黑名单
    if s.startswith("||"):
        dom = extract_adblock_domain(s)
        return ("block", [dom]) if dom else ("skip", "other")
    # 单竖线规则 |http://domain...
    if s.startswith("|"):
        dom = extract_adblock_domain(s)
        return ("block", [dom]) if dom else ("skip", "other")
    # 正则规则
    if s.startswith("/") and s.endswith("/"):
        return ("skip", "regex")
    # hosts 行（去掉行内注释）
    body = s.split("#", 1)[0].strip()
    if not body:
        return ("skip", "comment")
    m = HOSTS_RE.match(body)
    if m:
        ip, dom = m.group(1), m.group(2)
        rest = body[len(m.group(0)):].split()
        domains = [dom] + [x for x in rest if x]
        local = ip in LOCAL_IPS
        out = []
        for d in domains:
            if valid_domain(d):
                out.append(d)
        if not out:
            return ("skip", "other")
        if local:
            return ("block", out)
        return ("redirect", (ip, out))
    return ("skip", "other")


def main():
    if not os.path.isdir(SRC_DIR):
        print(f"[ERROR] source dir not found: {SRC_DIR}")
        sys.exit(1)

    files = sorted(f for f in os.listdir(SRC_DIR) if f.endswith(".txt"))
    if not files:
        print(f"[ERROR] no source files in {SRC_DIR}")
        sys.exit(1)

    all_blocks = set()
    all_allows = set()
    excluded_lines = []
    report = []

    for fn in files:
        name = os.path.splitext(fn)[0]
        path = os.path.join(SRC_DIR, fn)
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()

        stat = {"lines": len(lines), "block": 0, "allow": 0, "redirect": 0,
                "skip_cosmetic": 0, "skip_regex": 0, "skip_comment": 0,
                "skip_other": 0}

        if name in EXCLUDE_SOURCES:
            report.append((name, stat, True))
            continue

        for line in lines:
            kind, payload = parse_line(line)
            if kind == "block":
                for d in payload:
                    if valid_domain(d):
                        all_blocks.add(d)
                        stat["block"] += 1
                    else:
                        stat["skip_other"] += 1
            elif kind == "allow":
                if valid_domain(payload):
                    all_allows.add(payload)
                    stat["allow"] += 1
                else:
                    stat["skip_other"] += 1
            elif kind == "redirect":
                ip, doms = payload
                stat["redirect"] += len(doms)
                for d in doms:
                    excluded_lines.append(f"{ip}\t{d}\t[{name}]")
            else:
                key = "skip_" + payload
                if key in stat:
                    stat[key] += 1
                else:
                    stat["skip_other"] += 1

        report.append((name, stat, False))

    # 白名单与黑名单冲突时，以白名单为准（从黑名单中移除）
    conflict = all_blocks & all_allows
    if conflict:
        all_blocks -= conflict

    sorted_blocks = sorted(all_blocks)
    sorted_allows = sorted(all_allows)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_RULES, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("!\n")
        fh.write("! Title: Integrated extra sources (non-VPN only)\n")
        fh.write("! Description: 附加上游源整合产物，已排除翻墙/加速/重定向类条目；由 merge_dedup.py 合并\n")
        fh.write(f"! Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        fh.write(f"! Block rules: {len(sorted_blocks)}\n")
        fh.write(f"! Whitelist rules: {len(sorted_allows)}\n")
        fh.write("! Source files:\n")
        for name, _, excluded in report:
            tag = " (EXCLUDED: anti-censorship source)" if excluded else ""
            fh.write(f"!   - {name}{tag}\n")
        fh.write("!\n")
        fh.write("\n".join("||" + d + "^" for d in sorted_blocks))
        fh.write("\n")
        if sorted_allows:
            fh.write("\n".join("@@" + "||" + d + "^" for d in sorted_allows))
            fh.write("\n")

    with open(OUT_EXCLUDED, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# 判定为重定向(翻墙/加速/解锁)而排除的条目，格式: IP<TAB>域名<TAB>[来源]\n")
        fh.write("\n".join(excluded_lines))
        fh.write("\n")

    # ---- 控制台报告（ASCII，避免代码页乱码）----
    print(f"{'source':<20} {'lines':>8} {'block':>8} {'allow':>6} {'REDIRECT':>9} "
          f"{'cosmetic':>9} {'regex':>6} {'comment':>8} {'other':>7}")
    print("-" * 92)
    tot = {"lines": 0, "block": 0, "allow": 0, "redirect": 0,
           "skip_cosmetic": 0, "skip_regex": 0, "skip_comment": 0, "skip_other": 0}
    for name, stat, excluded in report:
        if excluded:
            print(f"{name:<20} {'(source excluded entirely - anti-censorship)':>60}")
            continue
        print(f"{name:<20} {stat['lines']:>8} {stat['block']:>8} {stat['allow']:>6} "
              f"{stat['redirect']:>9} {stat['skip_cosmetic']:>9} {stat['skip_regex']:>6} "
              f"{stat['skip_comment']:>8} {stat['skip_other']:>7}")
        for k in tot:
            tot[k] += stat[k]
    print("-" * 92)
    print(f"{'TOTAL':<20} {tot['lines']:>8} {tot['block']:>8} {tot['allow']:>6} "
          f"{tot['redirect']:>9} {tot['skip_cosmetic']:>9} {tot['skip_regex']:>6} "
          f"{tot['skip_comment']:>8} {tot['skip_other']:>7}")
    print()
    print(f"Unique block domains (after merge/dedup) : {len(sorted_blocks)}")
    print(f"Unique whitelist domains                 : {len(sorted_allows)}")
    print(f"Blocklist/whitelist conflicts resolved   : {len(conflict)}")
    print(f"Redirect (anti-censorship) lines excluded: {len(excluded_lines)}")
    print(f"Output rules    : {os.path.relpath(OUT_RULES, BASE_DIR)}")
    print(f"Output excluded : {os.path.relpath(OUT_EXCLUDED, BASE_DIR)}")


if __name__ == "__main__":
    main()
