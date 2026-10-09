# -*- coding: utf-8 -*-
# merge_dedup_pro.py
# Pro 版规则集：在 Full 版（18 个附加源）基础上，额外并入 10 个补充源，
# 规则量约为 Full 版的 1.7 倍。
#
# 设计说明：
#   - 复用 Full/merge_dedup.py 的合并逻辑（main() 已参数化），避免两套实现漂移
#   - 与 Full 版的唯一区别在于附加源整合产物：
#       Full : Cache/sources/      → out/integrated_extra.txt      (18 个源)
#       Pro  : Cache/sources/ + Cache/sources_pro/ → out/integrated_extra_pro.txt (28 个源)
#   - 输出 out/merged_dns_rules_pro.txt，与 Full 版并列，互不影响
#
# 运行顺序要求：必须在 fetch_sources.py 与 integrate_sources.py 之后执行
#
# 用法: py merge_dedup_pro.py

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))            # Pro/
ROOT_DIR = os.path.dirname(BASE_DIR)                             # 项目根目录
OUT_DIR = os.path.join(ROOT_DIR, "out")
OUT_FILE = os.path.join(OUT_DIR, "merged_dns_rules_pro.txt")

sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "Full"))
import merge_dedup as md                                         # noqa: E402

PRO_EXTRA_LABEL = "Integrated extra sources (28 lists)"
PRO_EXTRA_URL = ("yhosts / ad-wars / 1024_hosts / AdAway / YousList / StevenBlack / "
                 "anti-AD / EasyList family / ADgk / CJX / mvps / "
                 "i-dont-care-about-cookies / Adblock Warning Removal List / "
                 "Hblock / Spam404 / halflife / AWAvenue / AdGuard Chinese / "
                 "scamblocklist / NoCoin / Peter Lowe / Dan Pollock / neohosts")


def main():
    sources = md.build_sources(
        os.path.join(OUT_DIR, "integrated_extra_pro.txt"),
        PRO_EXTRA_LABEL, PRO_EXTRA_URL)

    md.main(
        out_file=OUT_FILE,
        sources=sources,
        title="Merged DNS blocklist - PRO (full + 10 extra sources)",
        description="! Description: 在 Full 版基础上额外并入 10 个补充源，"
                    "整行精确去重，白名单(@@)规则保留在文件末尾",
    )


if __name__ == "__main__":
    main()
