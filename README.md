# Merged DNS Blocklist（合并 DNS 拦截列表）

将三个 AdGuard Home DNS 黑名单上游**自动拉取 → 整行精确去重 → 合并**为单一 AdGuard 语法列表，
可供 [AdGuard Home](https://github.com/AdguardTeam/AdGuardHome) 作为 DNS 拦截清单订阅使用。

## 特性

- 三个上游源合并，**整行精确去重**（不做语义改写，不改动任何规则写法）
- 完整保留上游的 `@@` 白名单规则（置于合并文件末尾，避免白名单域名被误拦）
- 合并文件头部自动写入生成时间、来源与统计信息，便于审计
- 一键脚本：拉取 → 合并 → 提交并推送到 GitHub 仓库

## 目录结构

```
.
├── merge_dedup.py        # 合并去重脚本（Python 3）
├── update_lists.bat      # 一键更新脚本：下载 → 合并 → git 提交推送
├── .gitignore            # 忽略 raw/（上游源文件不入库）
├── raw/                  # 三个上游源文件（脚本自动拉取，临时产物）
└── out/
    └── merged_dns_rules.txt   # 合并产物，供 AdGuard Home 订阅
```

## 使用方法

前置依赖：Windows 10 1803+（自带 curl）、[Python 3](https://www.python.org/downloads/)（安装时勾选 **py launcher**）、git。

1. 用文本编辑器打开 `update_lists.bat`，在顶部配置区填入目标 GitHub 仓库地址：
   ```bat
   set "REMOTE_URL=https://github.com/你的用户名/你的仓库.git"
   ```
2. 首次使用前配置 git 身份（否则提交会失败）：
   ```bat
   git config --global user.name  "你的名字"
   git config --global user.email "you@example.com"
   ```
3. 双击运行 `update_lists.bat`。脚本会依次：
   1. 定位到脚本所在目录；
   2. 用 curl 拉取三个上游源到 `raw/`（第三个源直连失败时自动回退 ghfast.top 镜像）；
   3. 运行 `merge_dedup.py` 合并去重，输出 `out/merged_dns_rules.txt`；
   4. 初始化本地 git 仓库（如尚未初始化），提交合并产物与脚本，推送到 `origin/main`。

   也可跳过推送仅手动合并：`py merge_dedup.py`。

4. 在 AdGuard Home → 过滤器 → DNS 拦截清单中订阅本仓库合并产物的 raw 链接：`https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt`。之后每次运行 `update_lists.bat` 即可更新。
[订阅链接](https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt)

## 订阅加速镜像（GitHub 直连慢/超时时选用）

AdGuard Home 是**由您的设备去拉取规则**，国内网络直连 `raw.githubusercontent.com` 常常很慢甚至超时。
此时可将下表任意一条地址粘贴到「DNS 拦截清单」使用（按推荐程度排序）：

| 方式 | 地址 |
|---|---|
| **jsDelivr CDN**（推荐：免费全球 CDN，自动跟随 main 分支，缓存约数分钟） | https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules.txt |
| **gh-proxy.com** 代理 | https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt |
| **ghfast.top** 代理 | https://ghfast.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt |
| **gh.ddlc.top** 代理 | https://gh.ddlc.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt |
| 直连 raw.githubusercontent.com | https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt |

一次性复制全部地址：

```text
https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules.txt
https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt
https://ghfast.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt
https://gh.ddlc.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt
https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt
```

注意事项：

- jsDelivr 免费加速**公开仓库**且单文件需 ≤20 MB（本文件约 5.8 MB，满足）；列表更新后其缓存有数分钟到数小时的延迟，拉取到的可能不是最新版本，稍候再试即可。
- 第三方代理站可能限速或失效，失效就换下一条；ghfast.top 等加速站域名偶尔变动，最新地址见其主页发布站。
- 加速站属于第三方服务，仅作下载加速，不影响列表内容本身。

## 上游规则源与许可

合并产物由以下三个上游编译而来。各列表文件**本身不含许可声明**，下列许可证来自各上游仓库的 LICENSE 文件：

| 源 | 仓库 / 主页 | 许可证 | 内容 |
|---|---|---|---|
| URLHaus（AdGuard Hostlists Registry #11） | https://github.com/AdguardTeam/HostlistsRegistry | 仓库 **GPL-3.0**；数据源头 URLhaus（abuse.ch）无标准开源许可，官方仅提供 Fair Use 原则 + Terms of Service（见下注） | 恶意网站 / 钓鱼 / 木马域名 |
| GOODBYEADS dns | https://github.com/8680/GOODBYEADS | **MIT** | 去广告域名 |
| AdBlock DNS（217heidai/adblockfilters） | https://github.com/217heidai/adblockfilters | **GPL-3.0** | 去广告合并域名（含 193 条 @@ 白名单） |

> 注：URLhaus 数据（[API 文档](https://urlhaus.abuse.ch/api/)原文）：“available free of charge under the fair use principles”，商业/营利用途可能需要 abuse.ch 商业 API 订阅；再分发请遵守其 [Terms of Service](https://urlhaus.abuse.ch/faq/#tos)。个人非商业用途并注明来源风险较低。

## 免责声明

- 拦截列表可能包含**误报**（尤其恶意域名列表），启用后请关注日常访问，必要时在 AdGuard Home 中添加例外。
- 本项目仅做机械合并与去重，不对上游规则内容作正确性担保。

## License

本项目（脚本与文档）采用 **GNU General Public License v3.0（GPL-3.0）**，详见仓库根目录 [LICENSE](LICENSE) 文件（与远程仓库已设定的许可一致）。

> 注意：**合并产物（域名数据）的再分发仍受上游各自许可约束**（见上表），发布时请保留来源与许可声明。
