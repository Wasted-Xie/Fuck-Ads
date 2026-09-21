# -*- coding: utf-8 -*-
# fetch_sources.py
# 下载全部上游源：3 个主源 -> raw/，18 个附加源 -> sources/
#
# 行为约定（与 merge/build 脚本的缓存保护逻辑一致）：
#   - 直连优先（GitHub Actions 环境直连 GitHub 畅通），失败后依次尝试镜像
#   - 下载失败、响应为空、或新内容异常小（< 缓存的一半）时，保留已有缓存文件，
#     使规则集保持稳定、不产生无意义的提交
#   - 主源失败（且无缓存）为致命错误；附加源失败仅告警并继续
#
# 用法: python3 fetch_sources.py

import os
import sys
import time
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "Cache", "raw")
EXTRA_DIR = os.path.join(BASE_DIR, "Cache", "sources")

UA = "Mozilla/5.0 (compatible; fuck-ads-updater/1.0)"
TIMEOUT = 45
RETRIES = 2
MIRROR_TEMPLATES = (
    "https://gh-proxy.com/{url}",
    "https://gh.ddlc.top/{url}",
    "https://gh.con.sh/{url}",
    "https://ghproxy.cn/{url}",
    "https://ghfast.top/{url}",
)

# 主源：任一失败（且无缓存）即视为致命错误
PRIMARY_SOURCES = (
    ("filter_11.txt", (
        "https://adguardteam.github.io/HostlistsRegistry/assets/filter_11.txt",
    )),
    ("goodbyeads_dns.txt", (
        "https://raw.githubusercontent.com/8680/GOODBYEADS/master/data/rules/dns.txt",
        "https://ghfast.top/raw.githubusercontent.com/8680/GOODBYEADS/master/data/rules/dns.txt",
    )),
    ("adblockdns.txt", (
        "https://raw.githubusercontent.com/217heidai/adblockfilters/main/rules/adblockdns.txt",
    )),
)

# 附加源：失败仅告警；GitHub 源自动附加镜像回退
EXTRA_SOURCES = (
    ("yhosts.txt", "https://raw.githubusercontent.com/VeleSila/yhosts/master/hosts"),
    ("ad-wars.txt", "https://raw.githubusercontent.com/jdlingyu/ad-wars/master/hosts"),
    ("1024_hosts.txt", "https://raw.githubusercontent.com/Goooler/1024_hosts/master/hosts"),
    ("adaway.txt", "https://raw.githubusercontent.com/AdAway/adaway.github.io/master/hosts.txt"),
    ("youslist.txt", "https://raw.githubusercontent.com/yous/YousList/master/hosts.txt"),
    ("stevenblack.txt", "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"),
    ("xinggsf-rule.txt", "https://raw.githubusercontent.com/xinggsf/Adblock-Plus-Rule/master/rule.txt"),
    ("xinggsf-mv.txt", "https://raw.githubusercontent.com/xinggsf/Adblock-Plus-Rule/master/mv.txt"),
    ("adgk.txt", "https://raw.githubusercontent.com/banbendalao/ADgk/master/ADgk.txt"),
    ("cjx-annoyance.txt", "https://raw.githubusercontent.com/cjx82630/cjxlist/master/cjx-annoyance.txt"),
    ("anti-ad.txt", "https://raw.githubusercontent.com/privacy-protection-tools/anti-AD/master/anti-ad-adguard.txt"),
    ("mvps.txt", "https://winhelp2002.mvps.org/hosts.txt"),
    ("abp-easyprivacy.txt", "https://easylist-downloads.adblockplus.org/easyprivacy.txt"),
    ("easylist.txt", "https://easylist.to/easylist/easylist.txt"),
    ("easylist-privacy.txt", "https://easylist.to/easylist/easyprivacy.txt"),
    ("easylistchina.txt", "https://easylist-downloads.adblockplus.org/easylistchina.txt"),
    ("idontcarecookies.txt", "https://www.i-dont-care-about-cookies.eu/abp/"),
    ("antiadblock.txt", "https://easylist-downloads.adblockplus.org/antiadblockfilters.txt"),
)

# lite 版专用上游（217 Lite，仅国内域名）。
# 仅供 build_lite.py 使用，全量流程（merge_dedup.py）不读取它。
LITE_SOURCES = (
    ("adblockdnslite.txt",
     "https://raw.githubusercontent.com/217heidai/adblockfilters/main/rules/adblockdnslite.txt"),
)


def with_mirrors(url):
    """为 GitHub raw 地址补充镜像候选（直连优先）"""
    candidates = [url]
    if "raw.githubusercontent.com" in url:
        candidates += [tpl.format(url=url) for tpl in MIRROR_TEMPLATES]
    return candidates


def http_get(url):
    """返回响应字节；失败返回 None"""
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                if resp.status != 200:
                    raise urllib.error.HTTPError(url, resp.status, "bad status", resp.headers, None)
                return resp.read()
        except Exception:                              # noqa: BLE001 - 网络异常种类多，统一处理
            if attempt + 1 < RETRIES:
                time.sleep(2)
    return None


def fetch_one(name, urls, dest_dir, critical):
    """下载单个源；返回 'updated' / 'cached' / 'missing'"""
    dest = os.path.join(dest_dir, name)
    last_error = None

    for url in urls:
        data = http_get(url)
        if not data:
            continue

        size = len(data)
        if os.path.exists(dest):
            old_size = os.path.getsize(dest)
            if size < old_size // 2:
                print(f"[WARN] {name}: new copy {size} bytes vs cached {old_size} bytes - keeping cached copy")
                return "cached"

        tmp = dest + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, dest)
        print(f"[OK]   {name}: {size} bytes")
        return "updated"

    if os.path.exists(dest):
        print(f"[WARN] {name}: download failed - keeping cached copy")
        return "cached"
    if critical:
        print(f"[ERROR] {name}: download failed and no cache available", file=sys.stderr)
    else:
        print(f"[WARN] {name}: download failed and no cache - source omitted")
    return "missing"


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(EXTRA_DIR, exist_ok=True)

    stats = {"updated": 0, "cached": 0, "missing": 0}
    critical_missing = []

    print("==== primary sources (raw/) ====")
    for name, urls in PRIMARY_SOURCES:
        candidates = []
        for url in urls:
            candidates.extend(with_mirrors(url))
        result = fetch_one(name, candidates, RAW_DIR, critical=True)
        stats[result] += 1
        if result == "missing":
            critical_missing.append(name)

    print("==== extra sources (sources/) ====")
    for name, url in EXTRA_SOURCES:
        result = fetch_one(name, with_mirrors(url), EXTRA_DIR, critical=False)
        stats[result] += 1

    print("==== lite sources (raw/) ====")
    for name, url in LITE_SOURCES:
        result = fetch_one(name, with_mirrors(url), RAW_DIR, critical=False)
        stats[result] += 1

    print("==== fetch summary ====")
    print(f"updated : {stats['updated']}")
    print(f"cached  : {stats['cached']}")
    print(f"missing : {stats['missing']}")

    if critical_missing:
        print(f"[ERROR] critical sources unavailable: {', '.join(critical_missing)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
