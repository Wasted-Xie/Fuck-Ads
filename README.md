# Merged DNS Blocklist（合并 DNS 拦截列表）

将 **21 个上游**黑名单/去广告列表（3 个主源 + 18 个附加源）**自动拉取 → 格式清洗 → 整行精确去重 → 合并**
为 AdGuard 语法列表，可供 [AdGuard Home](https://github.com/AdguardTeam/AdGuardHome) 作为 DNS 拦截清单订阅使用。

每次运行产出**三套并列的列表**，可按设备性能任选其一订阅（同时订阅也不冲突）：

| 版本 | 产物文件 | 规则量 | 适用场景 |
|---|---|---|---|
| **全量版** | `out/merged_dns_rules.txt` | 约 31 万条 | 性能充足的设备（软路由 / NAS / 小主机） |
| **Lite 版** | `out/merged_dns_rules_lite.txt` | 约 14.7 万条 | 中等配置设备，优先保留国内域名拦截 |
| **Slim 版** | `out/merged_dns_rules_slim.txt` | 约 12.9 万条 | **229MB 级内存的低配软路由**，仅用国内规则源 + 父域无损收敛 |

## 特性

- **多格式清洗**：自动识别 hosts 格式（`0.0.0.0 域名`）与 adblock 格式（`||域名^`），统一转换为 AdGuard 语法
- **整行精确去重**：只删除完全相同的规则，不改写保留规则的写法
- **父域无损收敛**：`||a.com^` 已覆盖 `b.a.com`，因此删除所有被父域规则覆盖的子域规则，**不损失任何拦截能力**
- **完整保留白名单**：上游的 `@@` 白名单规则置于合并文件末尾，避免正常服务被误拦
- **剔除 DNS 层无法表达的内容**：带路径规则、`$domain=` / `$app=` 站点限定规则、元素隐藏规则（`##`）、正则规则
- **排除翻墙/加速类条目**：指向非本地 IP 的 hosts 重定向条目一律不纳入
- **保护域名**：附加源中 360 系列的拦截被过滤（原有上游列表不受影响，一概照拦）
- **三版本产物**：覆盖从高性能设备到 229MB 低配软路由的全部场景
- **各版互不冲突**：三套列表共用同一份白名单，且都会剔除白名单中已有的域名，不会出现「A 版拦截 / B 版放行」的矛盾
- 合并文件头部自动写入生成时间、来源与统计信息，便于审计
- **两种更新方式**：GitHub Actions 云端每 30 分钟自动更新（推荐），或本地 Windows 一键脚本

## 目录结构

代码按版本分目录存放，公共部分（下载、清洗）留在根目录：

```
.
├── fetch_sources.py          # 公共：下载 21 个上游 + Lite 专用上游 → Cache/
├── integrate_sources.py      # 公共：附加源清洗（多格式解析 → 统一为 ||域名^）
├── update_lists.bat          # 本地一键脚本：下载 → 清洗 → 三版构建 → 提交推送
├── update_lists_no_window.bat# 同上，但以隐藏窗口方式启动（无控制台闪现）
│
├── Full/                     # 全量版：21 个源全覆盖
│   └── merge_dedup.py        #   → out/merged_dns_rules.txt
├── Lite/                     # Lite 版：国内向源，优先国内域名
│   └── build_lite.py         #   → out/merged_dns_rules_lite.txt
├── Slim/                     # Slim 版：仅国内源 + 父域无损收敛
│   └── build_lite_slim.py    #   → out/merged_dns_rules_slim.txt
│
├── Cache/                    # 上游源文件缓存（脚本自动拉取，不入库）
│   ├── raw/                  #   主源 + Lite 专用上游
│   └── sources/              #   18 个附加源
├── out/                      # 最终产物（入库，供订阅）
│   ├── integrated_extra.txt          # 中间产物（不入库）
│   ├── excluded_redirect_entries.txt # 中间产物（不入库）
│   ├── merged_dns_rules.txt          # 全量版
│   ├── merged_dns_rules_lite.txt     # Lite 版
│   └── merged_dns_rules_slim.txt     # Slim 版
├── .github/workflows/
│   └── update.yml            # GitHub Actions 定时工作流（每 30 分钟）
└── .gitignore                # 忽略 Cache/、中间产物、__pycache__、test/
```

> 三个版本目录中的脚本**只读取** `Cache/` 的源文件与 `out/` 中的全量产物，彼此不干扰；
> 各版本脚本可独立运行，但存在顺序依赖：`integrate_sources.py` → `Full/` → `Lite/` 与 `Slim/`。

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
   py Full\merge_dedup.py
   py Lite\build_lite.py           :: 必须在 Full\merge_dedup.py 之后运行
   py Slim\build_lite_slim.py      :: 同上，需要全量产物作为白名单基准
   ```
4. 如需本机定时运行（示例：每小时）：
   ```bat
   schtasks /Create /TN FuckAdsUpdate /TR "C:\path\to\update_lists.bat" /SC HOURLY /MO 1 /F
   ```

### 订阅

在 AdGuard Home → 过滤器 → DNS 拦截清单中订阅（三选一，或同时订阅均无冲突）：

| 版本 | 规则量 | 订阅地址 |
|---|---|---|
| 全量版 | 约 31 万 | `https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt` |
| Lite 版 | 约 14.7 万 | `https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt` |
| **Slim 版**（229MB 级设备） | 约 12.9 万 | `https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt` |

列表随上游自动更新（每 30 分钟检查一次）。

## 订阅加速镜像（GitHub 直连慢/超时时选用）

AdGuard Home 是**由您的设备去拉取规则**，国内网络直连 `raw.githubusercontent.com` 常常很慢甚至超时。
此时可将下表任意一条地址粘贴到「DNS 拦截清单」使用（按推荐程度排序，**按设备性能选择对应那一列**）：

| 方式 | 全量版（约 31 万条） | Lite 版（约 14.7 万条） | Slim 版（约 12.9 万条） |
|---|---|---|---|
| **jsDelivr CDN**（推荐：免费全球 CDN，自动跟随 main 分支，缓存约数分钟） | https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules.txt | https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_lite.txt | https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_slim.txt |
| **gh-proxy.com** 代理 | https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt | https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt | https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt |
| **ghfast.top** 代理 | https://ghfast.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt | https://ghfast.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt | https://ghfast.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt |
| **gh.ddlc.top** 代理 | https://gh.ddlc.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt | https://gh.ddlc.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt | https://gh.ddlc.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt |
| 直连 raw.githubusercontent.com | https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt | https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt | https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt |

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

Slim 版：

```text
https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_slim.txt
https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt
https://ghfast.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt
https://gh.ddlc.top/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt
https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt
```

注意事项：

- jsDelivr 免费加速**公开仓库**且单文件需 ≤20 MB（全量约 7 MB、Lite 约 3.2 MB、Slim 约 2.8 MB，均满足）；列表更新后其缓存有数分钟到数小时的延迟，拉取到的可能不是最新版本，稍候再试即可。
- 第三方代理站可能限速或失效，失效就换下一条；ghfast.top 等加速站域名偶尔变动，最新地址见其主页发布站。
- 加速站属于第三方服务，仅作下载加速，不影响列表内容本身。

## 关于国内网络环境的实测结论

### 结论

**国内广告域名生态极度碎片化，已经到了"去重几乎无处可去"的程度。**

这不是情绪化判断，而是本项目在合并 11 个国内规则源（`adblockdnslite`、`anti-ad`、`yhosts`、`adgk`、`easylistchina`、`ad-wars`、`goodbyeads_dns`、`cjx-annoyance`、`xinggsf-rule`、`xinggsf-mv`、`1024_hosts`）时得到的实测结果。

### 理由与数据

**证据一：11 个独立维护的规则源，去重后只剩 12.9 万条**

| 处理阶段 | 规则数 | 说明 |
|---|---|---|
| 11 个源并集 | 143,806 | 多个源分别独立维护 |
| 父域无损收敛后 | **128,883** | 仅减少 14,923 条（**10.4%**） |

**11 个源、上百人年的维护积累，交叉重叠只带来了 10% 的冗余。** 如果国内广告域名集中在少数几个平台手里，各源之间的重叠率会高得多。对比国际源（StevenBlack、EasyList、AdAway、Mvps 等 4 源）：并集 126,907 条，父域收敛后 90,796 条，**减少 28.5%**——是国内向源的 **2.7 倍**。

**证据二：12.9 万条规则散落在 10.8 万个独立注册域上**

| 指标 | 数值 |
|---|---|
| 独立注册域（eTLD+1） | **108,035 个** |
| 平均每个注册域承载的规则 | **1.19 条** |
| 只含 1 条规则的注册域 | **100,272 个（占 92.8%）** |

**93% 的注册域只被一条规则覆盖。** 这意味着绝大多数广告域名是一域一广告、互不相关的一次性站点，而不是"一个平台下挂几百个子域"的集中式结构。这种形态**无法通过归并父域来压缩**——因为它们本来就没有共同的父域。

**证据三：域名呈现明显的批量注册特征**

| 现象 | 数据 |
|---|---|
| 疑似随机/批量注册域名 | 12,275 条（**8.5%**） |
| 廉价批量后缀占比 | `.site` 4,231、`.online` 4,011、`.cfd` 3,662、`.space` 3,660、`.cyou` 3,309、`.qpon` 2,760、`.website` 2,773 |
| 顶级域集中度 | `.com` 占 53%，其余高度分散在数十个廉价新顶级域中 |

正常经营的网站不会使用 `.cfd`、`.cyou`、`.qpon` 这类后缀。这些域名的存在说明：**国内广告投放方采用"批量注册廉价域名 + 快速废弃"的消耗战策略**，用大量一次性域名绕过黑名单。

### 这些数据说明了什么

1. **拦截方处于绝对劣势**：防守方需要为每一个新域名添加规则，攻击方只需花几块钱注册一个新域名。10.8 万个注册域、93% 单条规则，意味着这条流水线从未停止。
2. **传统去重手段已接近极限**：父域归并只能挤出 10%。继续压缩的唯一途径是"删规则"，而每删一条都可能漏掉一个真实广告域。
3. **国内网络环境的广告治理成本极高**：广告域名不是集中在几个可被一次性封禁的大平台，而是像霉菌一样散布在数十万个廉价域名上。这既是监管缺位的表现，也是流量变现链条极度碎片化的结果。

> 上述数据全部由本仓库脚本在本地实测得出，可用 `py Slim\build_lite_slim.py` 复现。

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
py Lite\build_lite.py                    :: 默认：全部国内向源（约 14.7 万条）
py Lite\build_lite.py --max 120000       :: 限到 12 万条，超限时按「优先级 → .cn 优先 → 域名长度」裁剪
py Lite\build_lite.py --no-security      :: 不纳入 URLHaus 安全源（-3,727 条）
```

## Slim 版说明（面向 229MB 级内存设备）

### 定位

在 Lite 版基础上进一步压缩到 **约 12.9 万条（2.75 MB）**，适用于内存 256MB 上下的低配软路由。

### 与 Lite 版的差异

| 项 | Lite 版 | Slim 版 |
|---|---|---|
| 规则数 | 148,726 | **128,874** |
| 上游源 | 国内向 11 源 + URLHaus | **仅国内向 11 源**（不含 URLHaus） |
| 压缩手段 | 仅整行去重 | 整行去重 + **父域无损收敛**（-14,923） |
| 品牌保护 | 无 | **360 只拦广告子域、简书整域放行** |
| 保底清单 | 无 | **4 条强制保留** |

**父域收敛**是 Slim 版独有的无损优化：AGH 中 `||a.com^` 已覆盖 `b.a.com`，因此所有被父域规则覆盖的子域规则都被删除，**不损失任何拦截能力**，却省下 14,923 条。

### 品牌保护（按维护者要求）

| 域名 | 策略 |
|---|---|
| `360.cn` / `360.com` / `360safe.com` / `360shouji.com` / `360os.com` / `360totalsecurity.com` / `360tpcdn.com` / `qhimg.com` / `qhmsg.com` / `qhres.com` / `so.com` / `360kan.com` | **只拦广告子域**（`ad.*`、`fenxi.*`、`lianmeng.*`、`union.*`、`s.*`、`tf.*`、`stat.*`、`inst.*`、`gamebox.*`、`wan.*` 等），主域与下载/更新/产品等功能域名一律放行 |
| `jianshu.com` | **整域放行**（上游误判） |

> 注意：名字里含 "360" 的**第三方**域名（`camera360.com`、`life360.com`、`leads360.com`、`360doc.com`、`insta360.com`、`360buy.com` 等）不属保护范围，照常拦截。

### 保底清单

以下 4 个国内广告域在无损收敛后可能被挤出，因此**强制保留**（`MUST_KEEP`）：

| 域名 | 说明 |
|---|---|
| `tanx.com` | 阿里妈妈广告交易平台（原易传媒 Tanx） |
| `jiathis.com` | 加网分享按钮 |
| `ad.m.iqiyi.com` | 爱奇艺移动端广告 |
| `ad.jia.360.cn` | 360 广告投放域（仅此子域，不影响 360 主站） |

### 手动调整

```bat
py Slim\build_lite_slim.py                  :: 默认：无损去重，不裁剪（约 12.9 万条）
py Slim\build_lite_slim.py --max 80000      :: 内存紧张时裁到 8 万条（保底清单强制保留）
py Slim\build_lite_slim.py --with-security  :: 额外纳入 URLHaus 安全源（默认不纳入）
```

### 内存占用说明

AdGuard Home 的规则内存开销约为 **1–2 KB/条**（随版本与配置浮动），因此：

| 规则数 | 估算内存 |
|---|---|
| 12.9 万（默认） | 126–252 MB |
| 8 万（`--max 80000`） | 78–156 MB |
| 5 万（`--max 50000`） | 49–98 MB |

> **该数值为估算，不是实测值**——准确占用需在目标设备上运行 AdGuard Home 后查看其内存统计。若 229MB 设备运行默认版吃力，请用 `--max` 下调。

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
