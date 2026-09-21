# Changelog

本项目所有值得注意的变更都会记录在此文件。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

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
