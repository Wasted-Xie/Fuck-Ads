# Merged DNS Blocklist（合并 DNS 拦截列表）

将 **21 个上游**黑名单/去广告列表（3 个主源 + 18 个附加源）**自动拉取 → 格式清洗 → 整行精确去重 → 合并**
为 AdGuard 语法列表，可供 [AdGuard Home](https://github.com/AdguardTeam/AdGuardHome) 作为 DNS 拦截清单订阅使用。

每次运行产出**两套并列的列表**，可按设备性能任选其一订阅（同时订阅也不冲突）：

| 版本 | 产物文件 | 规则量 | 适用场景 |
|---|---|---|---|
| **全量版** | `out/merged_dns_rules.txt` | 约 31 万条 | 性能充足的设备（软路由 / NAS / 小主机） |
| **Lite 版** | `out/merged_dns_rules_lite.txt` | 约 14.7 万条 | **极低配置软路由**，优先保留国内域名拦截 |

## 特性

- **多格式清洗**：自动识别 hosts 格式（`0.0.0.0 域名`）与 adblock 格式（`||域名^`），统一转换为 AdGuard 语法
- **整行精确去重**：只删除完全相同的规则，不改写保留规则的写法
- **完整保留白名单**：上游的 `@@` 白名单规则置于合并文件末尾，避免正常服务被误拦
- **剔除 DNS 层无法表达的内容**：带路径规则、`$domain=` / `$app=` 站点限定规则、元素隐藏规则（`##`）、正则规则
- **排除翻墙/加速类条目**：指向非本地 IP 的 hosts 重定向条目一律不纳入
- **保护域名**：附加源中 360 系列的拦截被过滤（原有上游列表不受影响，一概照拦）
- **双版本产物**：全量版覆盖广；Lite 版面向极低配置软路由，只取国内向上游并优先国内域名，体量约为全量的 47%
- **两版互不冲突**：Lite 版会剔除全量白名单中的域名，并沿用同一份白名单，不会出现「Lite 拦截 / 全量放行」的矛盾
- 合并文件头部自动写入生成时间、来源与统计信息，便于审计
- **两种更新方式**：GitHub Actions 云端每 30 分钟自动更新（推荐），或本地 Windows 一键脚本

## 目录结构

```
.
├── fetch_sources.py      # 源下载：21 个上游 + Lite 专用上游 → raw/ 与 sources/
├── integrate_sources.py  # 附加源清洗：多格式解析 → 统一为 ||域名^（Python 3）
├── merge_dedup.py        # 全量合并去重：主源 + 附加源 → merged_dns_rules.txt
├── build_lite.py         # Lite 版构建：国内向源 → merged_dns_rules_lite.txt（Python 3）
├── update_lists.bat      # 本地一键脚本：下载 → 清洗 → 合并 → 构建 Lite → 提交推送（Windows）
├── .github/workflows/
│   └── update.yml        # GitHub Actions 定时工作流（每 30 分钟）
├── .gitignore            # 忽略 raw/ 与 sources/（上游源文件不入库）
├── raw/                  # 主源 + Lite 专用上游（脚本自动拉取，临时产物）
├── sources/              # 18 个附加源（脚本自动拉取，临时产物）
└── out/
    ├── integrated_extra.txt        # 附加源清洗后的中间产物
    ├── merged_dns_rules.txt        # 全量产物，供 AdGuard Home 订阅
    └── merged_dns_rules_lite.txt   # Lite 产物（国内优先，低配设备用）
```

## 使用方法

两种更新方式**任选其一**（不要同时启用，否则两边会互相推送冲突）。

### 方式一：GitHub Actions 云端自动更新（推荐）

不需要本地机器开机，云端每 30 分钟自动执行：

1. `.github/workflows/update.yml` 已随仓库提供，**无需再配置任何脚本**；
2. **首次部署需确认一次仓库设置**：`Settings → Actions → General → Workflow permissions` 选择 **Read and write**，否则工作流没有权限把产物推回仓库；
3. 想立刻验证：打开 `Actions` 标签页 → 选择 **Update merged DNS rules** → **Run workflow**。

工作流每次执行：拉取 21 个源 + Lite 专用上游 → 格式清洗 → 合并去重（全量）→ 构建 Lite 版 → **仅在有变化时**提交推送（两套产物一起提交）。

> 说明：GitHub 的定时触发为每 30 分钟（UTC 的 0 分与 30 分），高峰期可能有数分钟到数十分钟延迟；规则无变化时不产生提交。

### 方式二：本地 Windows 运行（可选/应急）

前置依赖：Windows 10 1803+（自带 curl）、[Python 3](https://www.python.org/downloads/)（安装时勾选 **py launcher**）、git。

1. 用文本编辑器打开 `update_lists.bat`，确认顶部目标仓库地址：
   ```bat
   set "REMOTE_URL=https://github.com/Wasted-Xie/Fuck-Ads.git"
   ```
2. 首次使用前配置 git 身份（否则提交会失败）：
   ```bat
   git config --global user.name  "你的名字"
   git config --global user.email "you@example.com"
   ```
3. 双击运行 `update_lists.bat`，脚本依次执行：
   1. **定位路径** —— `cd` 到脚本所在目录；
   2. **下载 3 个主源** 到 `raw/`（多镜像链自动回退，失败会中止）；
   3. **下载 18 个附加源** 到 `sources/` 与 **Lite 专用上游** 到 `raw/`（GitHub 源经镜像链轮换，非 GitHub 源直连；个别失败只告警并沿用本地缓存）；
   4. **清洗 + 合并（全量）** —— `integrate_sources.py` 统一格式，`merge_dedup.py` 去重合并；
   5. **构建 Lite 版** —— `build_lite.py` 以全量白名单为基准生成 `merged_dns_rules_lite.txt`；
   6. **提交推送** —— 初始化本地 git 仓库（如尚未初始化），提交两套产物与脚本，推送到 `origin/main`（仅在有变化时）。

   也可手动分步执行：
   ```bat
   py fetch_sources.py
   py integrate_sources.py
   py merge_dedup.py
   py build_lite.py            :: 必须在 merge_dedup.py 之后运行
   ```
4. 如需本机定时运行（示例：每小时）：
   ```bat
   schtasks /Create /TN FuckAdsUpdate /TR "C:\path\to\update_lists.bat" /SC HOURLY /MO 1 /F
   ```

### 订阅

在 AdGuard Home → 过滤器 → DNS 拦截清单中订阅（二选一，或同时订阅均无冲突）：

| 版本 | 订阅地址 |
|---|---|
| 全量版 | `https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt` |
| **Lite 版**（低配设备） | `https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt` |

列表随上游自动更新。

## 订阅加速镜像（GitHub 直连慢/超时时选用）

AdGuard Home 是**由您的设备去拉取规则**，国内网络直连 `raw.githubusercontent.com` 常常很慢甚至超时。
此时可将下表任意一条地址粘贴到「DNS 拦截清单」使用（按推荐程度排序，**按设备性能选择全量版或 Lite 版那一列**）：

| 方式 | 全量版地址（约 31 万条） | Lite 版地址（约 14.7 万条） |
|---|---|---|
| **jsDelivr CDN**（推荐：免费全球 CDN，自动跟随 main 分支，缓存约数分钟） | https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules.txt | https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_lite.txt |
| **gh-proxy.com** 代理 | https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt | https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt |
| **ghfast.top** 代理 | https://ghfast.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt | https://ghfast.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt |
| **gh.ddlc.top** 代理 | https://gh.ddlc.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt | https://gh.ddlc.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt |
| 直连 raw.githubusercontent.com | https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt | https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt |

一次性复制全部地址：

全量版：

```text
https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules.txt
https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt
https://ghfast.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt
https://gh.ddlc.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt
https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt
```

Lite 版：

```text
https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_lite.txt
https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt
https://ghfast.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt
https://gh.ddlc.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt
https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt
```

注意事项：

- jsDelivr 免费加速**公开仓库**且单文件需 ≤20 MB（全量约 7 MB、Lite 约 3 MB，均满足）；列表更新后其缓存有数分钟到数小时的延迟，拉取到的可能不是最新版本，稍候再试即可。
- 第三方代理站可能限速或失效，失效就换下一条；ghfast.top 等加速站域名偶尔变动，最新地址见其主页发布站。
- 加速站属于第三方服务，仅作下载加速，不影响列表内容本身。

## Lite 版说明（面向极低配置软路由）

### 定位

Lite 版把规则量压到全量的约 **47%**（约 14.7 万条，3.2 MB），在保证国内广告拦截效果的前提下，降低 AdGuard Home 的内存占用与匹配开销。

### 与全量版的关系

| 项 | 说明 |
|---|---|
| 产出方式 | `build_lite.py` 独立生成，**不修改全量版的任何产出逻辑** |
| 白名单 | **直接沿用全量白名单**（274 条） |
| 冲突处理 | Lite 屏蔽集会**剔除全量白名单中的域名**，杜绝两版结论相反 |
| 订阅关系 | 两版可单独订阅，也可同时订阅（同时订阅时 Lite 是子集，无副作用） |

### 组成来源（按优先级）

| 优先级 | 源 | 说明 |
|---|---|---|
| P1 | **adblockdnslite**（217 Lite） | 官方 Lite 版，仅针对国内域名拦截 |
| P2 | anti-AD、ADgk、EasyList China、yhosts、大圣净化 | 国内向主力源 |
| P3 | CJX's Annoyance、乘风规则、GOODBYEADS | 国内补充 |
| P4 | 1024_hosts | 成人/赌博站点 |
| P5 | URLHaus（filter_11） | 恶意网站/钓鱼（安全类，可用 `--no-security` 去掉） |

> 注意：全量版中的国际源（EasyList、EasyPrivacy、StevenBlack、Mvps、AdAway、YousList 等）**不参与 Lite 版**，这是体量下降的主要来源。

### 手动调整

```bat
py build_lite.py                    :: 默认：全部国内向源（约 14.7 万条）
py build_lite.py --max 120000       :: 限到 12 万条，超限时按「优先级 → .cn 优先 → 域名长度」裁剪
py build_lite.py --no-security      :: 不纳入 URLHaus 安全源（-3,727 条）
```

## 数据处理规则

### 主源（3 个，未经格式改写）

主源由 `merge_dedup.py` 直接读取，**整行精确去重，不做任何格式改写或豁免**：

| 源 | 仓库 / 主页 | 许可证 | 内容 |
|---|---|---|---|
| URLHaus（AdGuard Hostlists Registry #11） | https://github.com/AdguardTeam/HostlistsRegistry | 仓库 **GPL-3.0**；数据源头 URLhaus（abuse.ch）无标准开源许可，官方仅提供 Fair Use 原则 + Terms of Service（见下注） | 恶意网站 / 钓鱼 / 木马域名 |
| GOODBYEADS dns | https://github.com/8680/GOODBYEADS | **MIT** | 去广告域名 |
| AdBlock DNS（217heidai/adblockfilters） | https://github.com/217heidai/adblockfilters | **GPL-3.0** | 去广告合并域名（含 `@@` 白名单） |

> 注：URLhaus 数据 ([API 文档](https://urlhaus.abuse.ch/api/) 原文)：“available free of charge under the fair use principles”，商业/营利用途可能需要 abuse.ch 商业 API 订阅；再分发请遵守其 [Terms of Service](https://urlhaus.abuse.ch/faq/#tos)。个人非商业用途并注明来源风险较低。

### Lite 专用上游（1 个，仅供 Lite 版）

| 源 | 地址 | 说明 |
|---|---|---|
| AdBlock DNS **Lite**（217heidai/adblockfilters） | https://github.com/217heidai/adblockfilters | 与全量主源同一项目，但内容为**仅国内域名拦截**的精简版（约 5,173 条），由 `build_lite.py` 使用；全量流程不读取它 |

### 附加源（18 个，经格式清洗）

附加源由 `integrate_sources.py` 清洗后再合并：

| 源 | 地址 | 内容 |
|---|---|---|
| yhosts | https://github.com/VeleSila/yhosts | 国内站点广告（hosts） |
| 大圣净化 ad-wars | https://github.com/jdlingyu/ad-wars | 国内视频网站广告（hosts） |
| 1024_hosts | https://github.com/Goooler/1024_hosts | 成人/赌博类站点（hosts） |
| AdAway | https://github.com/AdAway/adaway.github.io | 移动端广告（hosts） |
| YousList | https://github.com/yous/YousList | 韩文站点广告（hosts） |
| StevenBlack | https://github.com/StevenBlack/hosts | 综合去广告（hosts） |
| Mvps | https://winhelp2002.mvps.org/hosts.txt | 欧美站点广告（hosts） |
| anti-AD | https://github.com/privacy-protection-tools/anti-AD | 国内去广告（AdGuard 格式） |
| EasyList | https://easylist.to/easylist/easylist.txt | 国际广告 |
| EasyPrivacy | https://easylist.to/easylist/easyprivacy.txt | 隐私追踪 |
| EasyPrivacy（ABP 分发） | https://easylist-downloads.adblockplus.org/easyprivacy.txt | 隐私追踪 |
| EasyList China | https://easylist-downloads.adblockplus.org/easylistchina.txt | 中文广告 |
| 乘风视频规则 | https://github.com/xinggsf/Adblock-Plus-Rule | 国内视频站广告 |
| ADgk | https://github.com/banbendalao/ADgk | 国内去广告 |
| CJX's Annoyance List | https://github.com/cjx82630/cjxlist | 自我推广 |
| Adblock Warning Removal List | https://easylist-downloads.adblockplus.org/antiadblockfilters.txt | 反 Adblock 提示 |
| I don't care about cookies | https://www.i-dont-care-about-cookies.eu/abp/ | Cookie 提示（DNS 层基本无有效规则） |

**附加源清单来源**：[otobtc/ADhosts](https://github.com/otobtc/ADhosts) (https://github.com/otobtc/ADhosts) —— 本项目的附加源即从该仓库的推荐列表中筛选非翻墙类源，再统一做格式清洗。

> 附加源各自适用其仓库声明的许可，使用与再分发前请查阅对应仓库。

### 清洗规则明细

| 输入形式 | 处理 |
|---|---|
| hosts 行 `0.0.0.0 域名` / `127.0.0.1 域名` / `::1 域名` | 视为屏蔽，转为 `\|\|域名^` |
| hosts 行 `其它IP 域名` | 视为重定向（翻墙/加速/解锁），**排除**并单独记录到 `out/excluded_redirect_entries.txt` |
| `\|\|域名^` / `\|http://域名^` | 保留（仅接受纯域名形式） |
| `\|\|域名^/路径`（带路径） | **丢弃**（DNS 层无法表达路径，抽成整域会造成误拦） |
| `\|\|域名^$domain=x` / `$app=x`（站点/应用限定） | **丢弃**（转成整域会严重放大范围） |
| `@@\|\|域名^`（无修饰符白名单） | 保留为白名单 |
| `@@\|\|域名^$generichide` 等带修饰符白名单 | **丢弃**（场景限定豁免，转成无条件豁免会放行本该拦截的广告域） |
| 元素隐藏规则（含 `##`、`#@#`、`#?#`、`#$#`、`#%#`） | **丢弃**（DNS 层无效） |
| 正则规则 `/regex/`、扩展名式规则（如 `\|\|*.js`）、IP 形式规则 | **丢弃** |
| 保护域名（附加源中的 `360.cn` / `360.com` / `360safe.com` 等及其子域） | **过滤不拦**；主源不受此限制 |

> 被整体排除的翻墙/加速专用源：`googlehosts`（内容全为 IP 重定向）。
> 另外 `hblock`（站点在国内网络不可达）、`halflife`（已失效）以及 Koolproxy / Adbyby（代理端专用格式，非 DNS 规则）未纳入。

## 免责声明

- 拦截列表可能包含**误报**，启用后请关注日常访问，必要时在 AdGuard Home 中添加例外。
- 本项目仅做机械合并、格式转换与去重，不对上游规则内容作正确性担保。

## License

本项目（脚本与文档）采用 **GNU General Public License v3.0（GPL-3.0）**，详见仓库根目录 [LICENSE](LICENSE) 文件。

> 注意：**合并产物（域名数据）的再分发仍受上游各自许可约束**（见上表），发布时请保留来源与许可声明。
