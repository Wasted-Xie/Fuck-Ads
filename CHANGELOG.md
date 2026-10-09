# Changelog

本项目所有值得注意的变更都会记录在此文件。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [2.3.0] - 2026-10-09

**规则集拆分为四版本**：原先的「全量版」被拆为 **Full 版（约 32 万条）** 与 **Pro 版（约 53 万条）**，Lite / Slim 保持不变。

### 变更

#### 版本拆分

| 版本 | 产物 | 规则量 | 上游源 |
|---|---|---|---|
| **Full 版** | `out/merged_dns_rules.txt` | 约 32 万 | 21 个（3 主源 + 18 附加源） |
| **Pro 版** | `out/merged_dns_rules_pro.txt` | 约 53 万 | 31 个（3 主源 + 28 附加源） |
| Lite 版 | `out/merged_dns_rules_lite.txt` | 约 14.6 万 | 国内向 12 个 |
| Slim 版 | `out/merged_dns_rules_slim.txt` | 约 12.9 万 | 仅国内向 11 个 |

- **Full 版**回到 v2.0.0 时代的源构成（18 个附加源），规则量约 32 万条
- **Pro 版**保留 v2.1.0 引入的 10 个补充源（Hblock / Spam404 / halflife / AWAvenue / AdGuard Chinese / scamblocklist / NoCoin / Peter Lowe / Dan Pollock / neohosts），规则量约 53 万条
- `out/merged_dns_rules.txt` **文件名与订阅地址不变**，仍是 32 万条的 Full 版，既有订阅者不受影响

#### 目录与脚本

- 新增 `Pro/merge_dedup_pro.py`：复用 `Full/merge_dedup.py` 的合并逻辑（`main()` 已参数化为接受 `out_file` / `sources` / `title`），仅替换输入与输出，避免两套实现漂移
- `fetch_sources.py`：新增 `PRO_EXTRA_SOURCES`（10 个），下载到 `Cache/sources_pro/`，与 Full 用的 `Cache/sources/` 隔离
- `integrate_sources.py`：新增 `--src-dirs` / `--out` / `--out-excluded` / `--title` / `--only` 参数，支持一次清洗多个目录并输出到不同文件
- `fetch_sources.py` 新增 `prune_stale()`：删除源目录中不属于本版本的残留文件

### 修复

- **源目录残留污染**：`actions/cache` 会恢复上次运行的 `Cache/sources/`，其中残留的 Pro 源会导致 Full 版规则量错误膨胀到 53 万。`prune_stale()` 在每次拉取前清理非本版本文件，已实测验证（放入假残留文件 → 被自动删除）

### 说明

- Lite / Slim 仍以 **Full 版**产物作为白名单基准（Pro 版白名单多 1 条 `tracker.namitiyu.com`，不影响两者）
- 四个版本共用同一份手写名单（`Lists/whitelist.txt` 与 `Lists/blocklist.txt`）
- Actions 工作流新增 Pro 构建与 Pro 产物的 jsDelivr purge；`actions/cache` 路径加入 `Cache/sources_pro`
- 四份产物均通过幂等性验证

---

## [2.2.0] - 2026-10-07

**新增自定义名单**：支持手动维护白名单与拦截名单，参与全部三个版本的构建。

### 新增

#### `Lists/` 目录与两个手动维护的名单

| 文件 | 作用 |
|---|---|
| `Lists/whitelist.txt` | 放行被上游误拦的域名 |
| `Lists/blocklist.txt` | 拦截上游未覆盖的域名 |

- **格式**：两种写法都支持——裸域名（`example.com`）或 AdGuard 语法（`@@||example.com^` / `||example.com^`），大小写不敏感，`!` 与 `#` 开头为注释
- **范围**：三个版本全部生效。Full 直接读取；Lite / Slim 通过继承全量白名单自动获得白名单，拦截名单则单独注入
- **冲突处理**：
  - 两个手写文件互相冲突 → **白名单优先**，并打印警告
  - 手写白名单与上游黑名单冲突 → 自动移除上游黑名单条目（含子域），避免同一域名既拦又放
  - 手写拦截名单与全量白名单冲突 → 该条被忽略（兜底）
- **优先级**：手写拦截名单在 Lite / Slim 中获得最高优先级，即使使用 `--max` 裁剪也不会被挤出
- **格式校验**：无法解析的行（通配符、路径、`$` 修饰符、无点号等）会被忽略并在 stderr 打印行号与内容，不影响构建

#### 公共解析函数

`integrate_sources.py` 新增 `parse_domain()` 与 `load_manual_list()`，供三个版本共用，避免重复实现。

### 说明

- 两个名单文件默认只含注释、无任何规则，因此**初始状态下对产物零影响**（实测：空名单时产物与改动前完全一致，532,868 / 145,737 / 128,339，白名单 278）
- 产物头部新增两行记录手写名单的生效条数，便于审计：
  ```text
  ! Manual whitelist: Lists/whitelist.txt  (0 domains)
  ! Manual blocklist: Lists/blocklist.txt  (0 domains)
  ```
- 已通过边界测试：非法格式告警但不中断；空名单、幂等性、三版本一致性均验证通过

---

## [2.1.0] - 2026-10-06

**上游源扩充**：从 [BlueSkyXN/AdGuardHomeRules](https://github.com/BlueSkyXN/AdGuardHomeRules) 引用的规则源中补充引入 10 个本项目原先未使用的源（附加源 18 → 28 个），全量版规则量由约 31 万条增至约 53 万条。同时**彻底移除 360 品牌保护**。

### 新增

#### 补充引入 10 个上游源

经逐源核查（许可证、停更状态、可达性、与现有源的重叠度）后补充引入：

| 源 | 许可证 | 净新增 | 说明 |
|---|---|---|---|
| **Hblock** | MIT | 214,498 | 体量最大的新增源；官方站点在部分网络不可达，改用官方镜像项目 [hmirror](https://github.com/hectorm/hmirror) 的同源数据 |
| **Spam404** | — | 8,036 | 诈骗/盗版/外挂站点，纯域名格式 |
| **neohosts** | NOASSERTION | 290 | 国内综合（上游已停更） |
| **AdGuard Chinese filter** | GPL-3.0 | 169 | AdGuard 官方中文过滤器，替换原先 2021 年的陈旧快照 |
| **halflife** | — | 163 | 原 `o0HalfLife0o/list` 已注销，改用同源镜像 [sbwml/halflife-list](https://github.com/sbwml/halflife-list) |
| **Scam Blocklist** | MIT | 51 | 诈骗域名 |
| **Peter Lowe's List** | — | 13 | 老牌广告服务器列表 |
| **Dan Pollock's List** | — | 6 | 综合拦截（0.0.0.0 版） |
| **NoCoin Filter List** | MIT | 5 | 浏览器挖矿域名 |
| **AWAvenue Ads Rule** | GPL-3.0 | 1 | 国内去广告 |

#### 支持裸域名格式

`integrate_sources.py` 原先仅识别 `0.0.0.0 域名` / `||域名^` 两种形式，会静默丢弃纯域名列表（Spam404、Hblock 均为该格式，合计 46.9 万行）。现已支持无 IP 前缀的裸域名行。

### 变更

#### 彻底移除 360 品牌保护

早期版本对 360 系列做「只拦广告子域、主域与功能域放行」的特殊处理。按维护者要求**彻底移除该机制**（不只是失效，相关代码一并删除），360 系列规则与其他域名一视同仁：

- `Full/merge_dedup.py`：删除 `PROTECTED_DOMAINS` 常量、`is_protected()` 函数，以及 `load_rules()` 的 `apply_protection` 参数（该参数此前仅用于对附加源做 360 过滤）
- `Slim/build_lite_slim.py`：删除 `BRAND_360`、`AD_LABELS_360` 常量与 `is_360_ad_subdomain()` 函数，`drop_protected()` 简化为 `drop_allowed()`，仅负责简书整域放行

**未引入功能回归**：实测清理前后 Slim 产物 SHA256 完全一致、规则差异 0 条。

**附带修正**：此前 Slim 会删除 `||360.cn^` 裸域规则（为放行 360 主站），导致其下 85 条广告子域必须逐条列出。移除保护后裸域规则得以保留，这些子域由父域规则统一覆盖，**拦截范围不变而规则数减少**。

**保留项**：`jianshu.com` 整域放行不变。

### 规则量变化

| 版本 | 变更前 | 变更后 | 文件大小 |
|---|---|---|---|
| 全量版 | 309,157 | **532,868** | 12.05 MB |
| Lite 版 | 148,727 | **145,737** | 3.15 MB |
| Slim 版 | 130,710 | **128,339** | 2.74 MB |

> Lite / Slim 版基本持平：两者只取国内向源，新引入的源中仅 AdGuard Chinese filter、neohosts 属国内向。全量版增长主要来自 Hblock 与 Spam404。

### 修复

- `integrate_sources.py`：新增裸域名行解析（见上），此前 Spam404 与 Hblock 的规则会被全部丢弃
- `Lite/build_lite.py`、`Slim/build_lite_slim.py`：补上「内容未变不重写」保护（原先只有全量版有）。此前这两份产物每次构建都会因时间戳变化而被重写，在定时任务中会产生无意义的提交
- `Full/merge_dedup.py`：修正附加源标签中过期的源数量描述

### Slim 版表示优化

移除 360 保护后，`||360.cn^` 裸域规则得以保留，其下 85 条广告子域改由父域规则覆盖。实测 Slim 对 360 的拦截范围与 Lite **完全等价**（Lite 的 116 条 360 规则中，27 条直接命中、89 条被父域覆盖、0 条遗漏），而规则条数由表示方式决定减少。

### 说明

- 白名单三版本保持一致（各 278 条）
- 新引入源均通过策略检查：无简书冲突，无 360 保护相关回归
- Hblock 内容以钓鱼/诈骗/仿冒站点为主（如仿冒 Netflix、Leboncoin 的域名），引入后规则集定位由「纯广告拦截」扩展为「广告 + 反诈拦截」
- 上游 `anti-ad` 自带 2 条 360 相关白名单（`@@||profile*.se.360.cn^`、`@@||s.mvconf.f.360.cn^`）。此为**上游规则内容**，本项目按「机械合并、不干预内容」原则原样保留，未做过滤

---

## [2.0.0] - 2026-09-21

**多版本规则集大更新**：从「单一全量列表」演进为「三套并列规则集 + 按版本分目录 + 统一缓存」，并完成 GitHub Actions 全自动化。

### 新增

#### Lite 版规则集（`out/merged_dns_rules_lite.txt`）

面向**中等配置设备**的国内优先精简列表，约 **14.9 万条**（全量的约 48%）。

- 上游改用 217heidai 的 **AdBlock DNS Lite**（仅针对国内域名拦截，约 5,173 条）替代全量版
- 只用国内向源，剔除全部国际源（EasyList、EasyPrivacy×2、StevenBlack、Mvps、AdAway、YousList、Cookie 提示、反 AdBlock 提示）
- 按优先级分层：`adblockdnslite` / `anti-ad` / `adgk` / `easylistchina` / `yhosts` / `ad-wars` → `cjx-annoyance` / `xinggsf` / `goodbyeads` → `1024_hosts` → `filter_11`
- 支持 `--max` 按优先级裁剪、`--no-security` 剔除 URLHaus 安全源

#### Slim 版规则集（`out/merged_dns_rules_slim.txt`）

面向 **229MB 级内存低配软路由**的极简列表，约 **13 万条**。

- **父域无损收敛**：`||a.com^` 已覆盖 `b.a.com`，删除所有被父域规则覆盖的子域规则，不损失拦截能力却省下约 1.5 万条
- **品牌域名保护**：360 系列（`360.cn`、`360.com`、`360safe.com`、`360shouji.com`、`360os.com`、`360totalsecurity.com`、`360tpcdn.com`、`qhimg.com`、`qhmsg.com`、`qhres.com`、`so.com`、`360kan.com`）**只拦广告子域**，主域与下载/更新/产品等功能域名放行；`jianshu.com` 整域放行（上游误判）
- **保底清单**（`MUST_KEEP`）：`tanx.com`、`jiathis.com`、`ad.m.iqiyi.com`、`ad.jia.360.cn` 强制保留，不受收敛或裁剪影响
- 默认**不含** URLHaus 安全源（可用 `--with-security` 纳入），源代码中保留了该可选源
- 白名单与全量版完全一致，杜绝「某版拦截 / 另版放行」的矛盾

#### 国内网络环境实测结论（写入 README）

以实测数据论证国内广告域名生态的碎片化程度：

| 证据 | 数据 |
|---|---|
| 去重空间 | 11 个国内源并集 143,806 → 父域收敛后 128,883（**仅减 10.4%**）；同期国际 4 源减少 **28.5%** |
| 碎片化程度 | 12.9 万条规则散落在 **108,035 个**独立注册域，**92.8% 的注册域只有 1 条规则** |
| 批量注册特征 | 疑似随机域名 12,275 条（8.5%）；`.cfd` / `.cyou` / `.qpon` / `.space` 等廉价后缀数千条 |

结论：拦截方处于绝对劣势（防守需逐域加规则，攻击方几块钱注册新域），传统去重手段已接近极限，广告治理成本极高。

#### GitHub Actions 云端自动化

- 新增 `.github/workflows/update.yml`：**每 30 分钟**（UTC 的 0 分与 30 分）自动运行，支持手动触发
- 流程：下载 21 个上游 → 清洗 → 全量合并 → Lite 构建 → Slim 构建 → **仅在有变化时**提交推送
- 使用 `actions/cache` 保留上游缓存，源拉取失败时沿用旧缓存，保证规则集稳定
- Actions 版本：`checkout@v7`、`setup-python@v7`、`cache@v6`（Node 24）

#### 公共下载脚本 `fetch_sources.py`

- 统一负责下载 21 个上游 + Lite 专用上游，本地与云端共用
- 直连优先，失败依次尝试 5 个镜像站
- 下载失败、响应为空、或新内容异常小（< 缓存的一半）时**保留缓存副本**，避免规则集抖动

### 变更

#### 目录结构重组

代码按版本分目录存放，公共部分留在根目录：

```
├── fetch_sources.py          # 公共：下载 → Cache/
├── integrate_sources.py      # 公共：附加源清洗
├── CHANGELOG.md              # 版本变更记录
├── Full/merge_dedup.py       # 全量版
├── Lite/build_lite.py        # Lite 版
├── Slim/build_lite_slim.py   # Slim 版
├── Cache/raw/ + Cache/sources/   # 上游源文件缓存（不入库）
├── out/                      # 三份产物（文件名未变）
└── .github/workflows/update.yml
```

- 上游缓存从 `raw/` + `sources/` 迁移至 `Cache/` 统一管理
- 三个版本的脚本可独立运行，依赖顺序：`integrate_sources.py` → `Full/` → `Lite/` 与 `Slim/`

#### 三个产物文件名保持不变

`out/merged_dns_rules.txt`、`out/merged_dns_rules_lite.txt`、`out/merged_dns_rules_slim.txt`
—— 已分发的订阅地址不受影响。

### 修复

- **父域收敛与白名单冲突的逻辑缺陷**：原实现会把「白名单豁免某个子域」误判为「父域规则与白名单冲突」而删除父域规则（例如 `@@||5471782.fls.doubleclick.net^` 导致 `||doubleclick.net^` 被删）。现改为仅当规则**自身**在白名单中时才剔除
- **品牌保护与父域收敛的执行顺序**：必须先剔除 `||360.cn^` 这类整域规则，再做父域收敛，否则其下广告子域会被当作"已被父域覆盖"而一并删除

### 移除

- `update_lists.bat`（本地一键脚本）—— 更新流程已完全托管至 GitHub Actions，本地不再需要该脚本；如需本地生成，按 README「方式二」依次运行五个 Python 脚本即可
- `update_lists_no_window.bat`（旧版隐藏窗口启动器，内容为早期流程快照）
- `merge_dedup.js`（早期 JS 实现，已被 `Full/merge_dedup.py` 取代）
- `run_hidden.vbs`（定时任务包装器）
- 本地 `raw/` 与 `sources/` 目录（已并入 `Cache/`）
- 过期的实验缓存与分析副本

---

## [1.1.0] - 2026-09-16

### 变更

- GitHub Actions 触发频率由每小时改为**每 30 分钟**
- Actions 升级至 Node 24 版本（`checkout@v7`、`setup-python@v7`、`cache@v6`），消除 Node 20 弃用警告
- README 补充订阅加速镜像表（jsDelivr / gh-proxy.com / ghfast.top / gh.ddlc.top / 直连）

### 新增

- 多镜像回退链：GitHub 源在直连失败后依次尝试 5 个镜像站
- 缓存保护：源拉取失败时沿用本地缓存，避免规则集抖动与无意义提交

---

## [1.0.0] - 2026-09-09

### 新增

- 初始版本：合并 3 个上游（URLHaus / GOODBYEADS / AdBlock DNS）为单一 AdGuard 语法列表
- `merge_dedup.py`：整行精确去重，保留上游 `@@` 白名单
- `update_lists.bat`：本地一键脚本（下载 → 合并 → 提交推送）
- 「规则无变化时不提交」：仅比较实质内容，忽略生成时间戳
- README：目录结构、使用方法、上游源与许可、数据处理规则

---

## 版本说明

| 版本 | 含义 |
|---|---|
| 主版本 +1 | 产物结构或订阅方式发生**不兼容变化** |
| 次版本 +1 | 新增规则集、上游源或功能，向后兼容 |
| 修订号 +1 | 修复缺陷、调整参数、文档更新 |

> 每日的规则自动更新（`Update merged DNS rules`）不单独记录，仅记录代码、流程与规则集结构的变更。
