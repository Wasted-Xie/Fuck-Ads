# -*- coding: utf-8 -*-
# integrate_sources.py
# 从 sources/ 下的附加上游规则源中提取「可用的域名规则」，排除翻墙/加速/解锁类条目，
# 输出 out/integrated_extra.txt，供 merge_dedup.py 作为附加源参与最终合并。
#
# 判定规则：
#   hosts 行 (IP + 域名)：
#       - IP 是 0.0.0.0 / 127.0.0.1 / ::1 等本地地址 -> 屏蔽，转成 ||domain^
#       - IP 是其它地址                        -> 重定向(翻墙/加速/解锁)，排除并单独记录
#   裸域名行 (无 IP 前缀，如 Spam404 / hblock)   -> 屏蔽，转成 ||domain^
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
SRC_DIR = os.path.join(BASE_DIR, "Cache", "sources")
OUT_DIR = os.path.join(BASE_DIR, "out")
OUT_RULES = os.path.join(OUT_DIR, "integrated_extra.txt")
OUT_EXCLUDED = os.path.join(OUT_DIR, "excluded_redirect_entries.txt")

# 手动维护的名单目录（入库）。四个版本共用同一套解析逻辑。
LISTS_DIR = os.path.join(BASE_DIR, "Lists")
WHITELIST_FILE = os.path.join(LISTS_DIR, "whitelist.txt")
BLOCKLIST_FILE = os.path.join(LISTS_DIR, "blocklist.txt")
MIXED_FILE = os.path.join(LISTS_DIR, "mixed.txt")

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


def parse_domain(line):
    """从一行手写名单中取出纯域名（丢弃黑白属性）；无法识别时返回 None。

    支持两种写法：
        example.com          -> example.com
        @@||example.com^     -> example.com
        ||example.com^       -> example.com
    以 ! 或 # 开头（以及 [ 开头）的行视为注释，返回 None。
    带路径、通配符或 $ 修饰符的写法不支持，一律返回 None 交由调用方告警。
    """
    s = line.strip()
    if not s or s.startswith("!") or s.startswith("#") or s.startswith("["):
        return None
    if s.startswith("@@"):
        s = s[2:]
    if s.startswith("||"):
        s = s[2:]
    s = s.strip().rstrip("^").strip().lower()
    if not s or "/" in s or "$" in s or "*" in s or " " in s:
        return None
    if "." not in s or s.startswith(".") or s.endswith("."):
        return None
    return s


def parse_signed_domain(line):
    """从一行手写名单中取出 (is_allow, domain)；无法识别时返回 None。

    与 parse_domain 的区别：**保留黑白属性**，用于同一文件内混写拦截与放行。
        example.com           -> (False, 'example.com')   裸域名按拦截处理
        ||example.com^        -> (False, 'example.com')
        @@||example.com^      -> (True,  'example.com')
    以 ! 或 # 开头（以及 [ 开头）的行视为注释，返回 None。
    """
    s = line.strip()
    if not s or s.startswith("!") or s.startswith("#") or s.startswith("["):
        return None
    is_allow = False
    if s.startswith("@@"):
        is_allow = True
        s = s[2:]
    if s.startswith("||"):
        s = s[2:]
    s = s.strip().rstrip("^").strip().lower()
    if not s or "/" in s or "$" in s or "*" in s or " " in s:
        return None
    if "." not in s or s.startswith(".") or s.endswith("."):
        return None
    return (is_allow, s)


def load_manual_list(path):
    """读取一个手动维护的名单文件，返回 (域名集合, 无法解析的 (行号, 内容) 列表)。

    丢弃黑白属性，适用于「只放行」或「只拦截」的单用途文件。
    """
    domains, bad_lines = set(), []
    if not os.path.exists(path):
        return domains, bad_lines
    with open(path, "r", encoding="utf-8") as f:
        for lineno, raw_line in enumerate(f, 1):
            if not raw_line.strip() or raw_line.strip().startswith(("!", "#", "[")):
                continue
            dom = parse_domain(raw_line)
            if dom:
                domains.add(dom)
            else:
                bad_lines.append((lineno, raw_line.strip()))
    return domains, bad_lines


def load_mixed_list(path):
    """读取「黑白混写」名单，返回 (allow 集合, block 集合, 无法解析的行列表)。

    同一域名若在文件内既写放行又写拦截，放行优先（从 block 中剔除）。
    """
    allow, block, bad_lines = set(), set(), []
    if not os.path.exists(path):
        return allow, block, bad_lines
    with open(path, "r", encoding="utf-8") as f:
        for lineno, raw_line in enumerate(f, 1):
            if not raw_line.strip() or raw_line.strip().startswith(("!", "#", "[")):
                continue
            parsed = parse_signed_domain(raw_line)
            if parsed is None:
                bad_lines.append((lineno, raw_line.strip()))
                continue
            is_allow, dom = parsed
            (allow if is_allow else block).add(dom)
    # 文件内部冲突：放行优先
    block -= allow
    return allow, block, bad_lines


def load_verbatim_rules(path):
    """读取「原样透传」名单：按原始顺序保留每一行（含注释与规则）。

    与 load_manual_list / load_mixed_list 的区别：
        后两者把规则归一成纯域名（剥离 $ 修饰符、丢弃通配符），适合「只想要域名」的场景；
        本函数则**逐行原样保留**，包括 $important 等修饰符、* 通配符、@@ 前缀，
        以及 # 注释和分组说明（如「#针对转转App的放行规则，勿删」）。

    返回 (全部行列表, 规则行数, 注释行数)。
    全部行列表用于直接写入产物，保持与源文件一致的顺序与分组；
    AdGuard Home 会忽略其中的注释行，故不影响规则解析。
    """
    lines, n_rule, n_comment = [], 0, 0
    if not os.path.exists(path):
        return lines, n_rule, n_comment
    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            s = raw_line.strip()
            if not s:
                continue
            lines.append(s)
            if s.startswith(("#", "!")):
                n_comment += 1
            else:
                n_rule += 1
    return lines, n_rule, n_comment


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
    # 裸域名行（部分源为纯域名列表，如 Spam404 / Hblock 的 hmirror 版本）
    if valid_domain(body) and " " not in body:
        return ("block", [body])
    return ("skip", "other")


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="清洗附加上游源，输出可被 merge_dedup 合并的规则文件")
    ap.add_argument("--src-dirs", nargs="+", default=[SRC_DIR],
                    help="待清洗的源目录，可指定多个（默认 Cache/sources）")
    ap.add_argument("--out", default=OUT_RULES, help="输出规则文件路径")
    ap.add_argument("--out-excluded", default=OUT_EXCLUDED,
                    help="被判定为重定向而排除的条目输出路径")
    ap.add_argument("--title", default="Integrated extra sources (non-VPN only)",
                    help="输出文件头部标题")
    ap.add_argument("--only", nargs="*", default=None,
                    help="白名单式限定：只处理这些源名（不带 .txt）。"
                         "用于防止目录中残留的非本版本源被误纳入")
    args = ap.parse_args()

    src_dirs = [d if os.path.isabs(d) else os.path.join(BASE_DIR, d)
                for d in args.src_dirs]
    only = set(args.only) if args.only else None

    files = []
    for d in src_dirs:
        if not os.path.isdir(d):
            print(f"[ERROR] source dir not found: {d}", file=sys.stderr)
            sys.exit(1)
        for f in sorted(os.listdir(d)):
            if not f.endswith(".txt"):
                continue
            if only is not None and os.path.splitext(f)[0] not in only:
                print(f"[SKIP] {f}: not in --only list (stale file?)")
                continue
            files.append(os.path.join(d, f))
    if not files:
        print(f"[ERROR] no source files in {src_dirs}", file=sys.stderr)
        sys.exit(1)

    all_blocks = set()
    all_allows = set()
    excluded_lines = []
    report = []

    for path in files:
        fn = os.path.basename(path)
        name = os.path.splitext(fn)[0]
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

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("!\n")
        fh.write(f"! Title: {args.title}\n")
        fh.write("! Description: 附加上游源整合产物，已排除翻墙/加速/重定向类条目；由 merge_dedup 合并\n")
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

    with open(args.out_excluded, "w", encoding="utf-8", newline="\n") as fh:
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
    print(f"Output rules    : {os.path.relpath(args.out, BASE_DIR)}")
    print(f"Output excluded : {os.path.relpath(args.out_excluded, BASE_DIR)}")


if __name__ == "__main__":
    main()
