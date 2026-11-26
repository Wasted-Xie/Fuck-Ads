# Merged DNS Blocklist（合并 DNS 拦截列表）

将 **31 个上游**黑名单/去广告列表（3 主源 + 28 附加源）自动拉取 → 格式清洗 → 整行精确去重 → 合并为 AdGuard 语法列表，供 [AdGuard Home](https://github.com/AdguardTeam/AdGuardHome) 订阅使用。

每次运行产出**四套并列的列表**，按设备性能任选其一（同时订阅也不冲突）：

| 版本 | 产物 | 规则量 | 上游源 | 适用场景 |
|---|---|---|---|---|
| **Full** | `merged_dns_rules.txt` | 约 36 万 | 21 个（3 主源 + 18 附加源） | 性能充足设备，拦截与占用的平衡点 |
| **Pro** | `merged_dns_rules_pro.txt` | 约 56 万 | 31 个（3 主源 + 28 附加源） | 追求最大拦截覆盖，接受更高内存 |
| **Lite** | `merged_dns_rules_lite.txt` | 约 15 万 | 国内向 12 个 | 中等配置，优先国内域名 |
| **Slim** | `merged_dns_rules_slim.txt` | 约 14 万 | 仅国内向 11 个 | **229MB 级内存低配软路由** |

> 订阅地址见 [订阅](#订阅) 一节。

> **Full 与 Pro 的区别**：Pro 额外并入 10 个补充源（Hblock、Spam404、halflife、AWAvenue、AdGuard Chinese、scamblocklist、NoCoin、Peter Lowe、Dan Pollock、neohosts），规则量约 1.7 倍。这些源偏重**反诈/恶意域名**，若只需拦截广告，Full 已足够。

## 特性

- **多格式清洗**：识别 hosts（`0.0.0.0 域名`）、adblock（`||域名^`）与裸域名格式，统一转为 AdGuard 语法
- **整行精确去重**：只删完全相同的规则，不改写保留规则的写法
- **父域无损收敛**：`||a.com^` 已覆盖 `b.a.com`，删除被覆盖的子域规则**不损失拦截能力**
- **完整保留白名单**：上游 `@@` 规则置于文件末尾，避免误拦正常服务
- **剔除 DNS 层无法表达的内容**：带路径规则、`$domain=` / `$app=` 限定规则、元素隐藏（`##`）、正则
- **排除翻墙/加速条目**：指向非本地 IP 的 hosts 重定向一律不纳入
- **自定义名单**：`Lists/` 下三个手写文件参与全部版本构建
- **无硬编码放行**：代码中不对任何域名做特殊处理，需放行时写进 `Lists/whitelist.txt` 即可
- **四版本产物**：覆盖从最大拦截到 229MB 低配设备
- **各版互不冲突**：共用同一份白名单，且都剔除白名单已有域名
- **全自动更新**：Actions 定时拉取重建，仅在有变化时提交

## 目录结构

```
.
├── fetch_sources.py          # 公共：下载 31 个上游 + Lite 专用源 → Cache/
├── integrate_sources.py      # 公共：附加源清洗（多格式 → ||域名^）
├── extract_agh_rules.py      # 本地工具：从 AGH 配置提取自定义规则（不入库）
│
├── Full/merge_dedup.py       # → out/merged_dns_rules.txt
├── Pro/merge_dedup_pro.py    # → out/merged_dns_rules_pro.txt（复用 Full 合并逻辑）
├── Lite/build_lite.py        # → out/merged_dns_rules_lite.txt
├── Slim/build_lite_slim.py   # → out/merged_dns_rules_slim.txt
│
├── Cache/                    # 上游源缓存（自动拉取，不入库）
│   ├── raw/                  #   主源 + Lite 专用源
│   ├── sources/              #   18 个附加源（Full 用）
│   └── sources_pro/          #   10 个 Pro 专用源
├── Lists/                    # 手动名单（入库，参与全部四版）
│   ├── whitelist.txt         #   只放行（裸域名即可，参与清洗）
│   ├── blocklist.txt         #   只拦截（裸域名即可，参与清洗）
│   └── Append.txt            #   扩展区：原样追加到产物末尾，不参与清洗
├── out/                      # 最终产物（入库，供订阅）
├── docs/
│   ├── rules-and-license.md  # 数据处理规则、优先级、许可说明
│   └── analysis.md           # Lite/Slim 参数与实测数据
├── .github/workflows/update.yml
└── .gitignore
```

> 脚本**只读取** `Cache/` 与 `out/`，彼此不干扰。顺序依赖：
> `integrate_sources.py`（Full 与 Pro 各一次）→ `Full/` → `Pro/` → `Lite/`、`Slim/`（后两者以 Full 产物为白名单基准）。

## 使用方法

更新已完全托管在 GitHub Actions，本地无需运行任何脚本。

### 云端自动更新（默认）

1. `update.yml` 已随仓库提供，**无需配置脚本**
2. **首次部署需确认一次**：`Settings → Actions → General → Workflow permissions` 选 **Read and write**，否则工作流无权推回产物
3. 想立即验证：`Actions` → **Update merged DNS rules** → **Run workflow**

每次执行：拉取全部上游 → 清洗（Full/Pro 各一次）→ 合并（Full）→ 合并（Pro）→ 构建 Lite → 构建 Slim → 仅在有变化时提交四套产物。

> GitHub 定时触发为每 30 分钟（UTC 0/30 分），高峰期可能延迟数分钟至数十分钟。

### 本地手动运行（应急）

前置：[Python 3](https://www.python.org/downloads/)（勾选 **py launcher**）。

```bat
py fetch_sources.py             :: 下载全部上游 → Cache/
py integrate_sources.py         :: 清洗 Full 附加源（18 个）
py integrate_sources.py --src-dirs Cache/sources Cache/sources_pro ^
    --out out/integrated_extra_pro.txt ^
    --out-excluded out/excluded_redirect_entries_pro.txt ^
    --title "Integrated extra sources for PRO (non-VPN only)"   :: 清洗 Pro 附加源（28 个）
py Full\merge_dedup.py          :: 生成 Full（须在 integrate 之后）
py Pro\merge_dedup_pro.py       :: 生成 Pro
py Lite\build_lite.py           :: 生成 Lite（需 Full 产物作白名单基准）
py Slim\build_lite_slim.py      :: 生成 Slim（同上）
```

产物输出到 `out/`，文件名与云端一致。

## 订阅

在 AdGuard Home → 过滤器 → DNS 拦截清单中添加。**四个版本选其一即可**（同时订阅多个版本会导致规则重复）。

**使用建议**：

1. 性能充足 → 选 **Full**；追求最大拦截覆盖 → 选 **Pro**；低配设备 → 选 **Lite**（中等）或 **Slim**（229MB 级）
2. 国内网络优先点 **加速链接 1**（gh-proxy.com，1 分钟缓存，最稳）；它失效时依次试加速链接 2 / 3
3. 四个版本语法相同（均为 AdGuard 通用语法：`||域名^`、`@@` 放行、`*` 通配符、`$important`），**AdGuard Home、AdGuard 浏览器插件、AdGuard for Windows/Mac/Android 均可使用**

| 版本 | 规则量 | 原始链接 | 加速链接 1 | 加速链接 2 | 加速链接 3 | 适配说明 |
|---|---|---|---|---|---|---|
| **Full** | 约 36 万 | [原始](https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt) | [gh-proxy](https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt) | [jsDelivr](https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules.txt) | [fastly](https://fastly.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules.txt) | AdGuard Home、AdGuard 全系 |
| **Pro** | 约 56 万 | [原始](https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_pro.txt) | [gh-proxy](https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_pro.txt) | [jsDelivr](https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_pro.txt) | [fastly](https://fastly.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_pro.txt) | AdGuard Home、AdGuard 全系 |
| **Lite** | 约 15 万 | [原始](https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt) | [gh-proxy](https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt) | [jsDelivr](https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_lite.txt) | [fastly](https://fastly.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_lite.txt) | AdGuard Home、AdGuard 全系 |
| **Slim** | 约 14 万 | [原始](https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt) | [gh-proxy](https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt) | [jsDelivr](https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_slim.txt) | [fastly](https://fastly.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_slim.txt) | AdGuard Home、AdGuard 全系 |

### 各渠道说明

| 渠道 | 缓存时长 | 说明 |
|---|---|---|
| 原始链接 | 5 分钟 | `raw.githubusercontent.com` 直连，国内常超时，耗时波动可达 31 倍 |
| **加速链接 1**（gh-proxy.com） | 60 秒 | **首选**。国内可直连，TTFB 最稳（波动仅 1.4 倍） |
| 加速链接 2（jsDelivr cdn） | 最长 12 小时 | 备用。偶有 TTFB 尖峰 |
| 加速链接 3（jsDelivr fastly） | 最长 12 小时 | 备用。`cdn` 节点异常时换这个 |

> **建议同时订阅两条**（如 Full 的加速链接 1 + 加速链接 2）互为兜底。AGH 允许添加多个过滤器，同一版本重复规则不会冲突。

### jsDelivr 缓存异常时

把 `cdn.jsdelivr.net` 换成 `fastly.jsdelivr.net` 或 `gcore.jsdelivr.net` 再试；也可主动清缓存（浏览器打开，返回 `"status": "finished"` 即成功）：

[清 Full](https://purge.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules.txt) · [清 Pro](https://purge.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_pro.txt) · [清 Lite](https://purge.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_lite.txt) · [清 Slim](https://purge.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_slim.txt)

> 该清除已写入 Actions：产物有变化时自动 purge 四个地址。

**确认拿到最新版**：看文件头部 `! Block rules:` 与 `! Generated:`，与仓库 [out/](out/) 不一致即命中旧缓存。

## AGH 订阅稳定性建议

AGH 对过滤器源有超时判定：**某次拉取超时或连接被重置，就会标记该订阅「连接不稳定」**。因此对 AGH 而言「每次几秒内响应」比「平均速度快」更重要——偶发 20 秒尖峰比稳定的 2 秒更容易触发告警。

**为何 jsDelivr 偶尔不稳定**：用 4 个国内公共 DNS 解析其各节点，**全部返回境外 IP**（Cloudflare / Fastly），无任何国内节点。每次拉取都要跨境，于是出现「多数几百毫秒、偶尔 20 秒」的尖峰。

**推荐**：gh-proxy.com 首选（TTFB 波动仅 1.4 倍），jsDelivr 备用，两条同时订阅互为兜底。

**已被标记不稳定时**：删掉该过滤器重新添加（重置失败计数）→ 换成 gh-proxy.com 地址。

> 完整实测数据（各渠道 TTFB、成功率、11 个已失效加速站清单）见 [docs/analysis.md](docs/analysis.md)。

## 自定义名单（手动维护）

`Lists/` 下三个手写文件，处理方式完全不同：

| 文件 | 作用 | 写法 |
|---|---|---|
| `whitelist.txt` | **放行**（参与清洗） | 裸域名，如 `example.com` |
| `blocklist.txt` | **拦截**（参与清洗） | 裸域名，如 `example.com` |
| `Append.txt` | **原样追加**到产物末尾（不参与清洗） | 完整 AdGuard 语法 |

**放行一个域名**：写进 `Lists/whitelist.txt`，一行一个。产物会输出为 `@@||example.com^$important`——最高优先级，能压过任何拦截规则（含 `Append.txt` 里的 `||d^$important`）。

**拦截一个域名**：写进 `Lists/blocklist.txt`。

**Append.txt 是"扩展区"，不是名单**：内容逐行原样追加，脚本不解析、不清洗、不做冲突检查。写什么，产物末尾就是什么，是否有效完全由 AGH 判定。因此它支持 `$important`、`*` 通配符、注释分组等全部语法。

> ⚠️ `Append.txt` 里写裸域名**不会**被自动转成 `||域名^`，请写完整语法。

> 优先级细节（构建时 vs 运行时、冲突判定速查表、Lite/Slim 的白名单继承）见
> [docs/rules-and-license.md](docs/rules-and-license.md#优先级顺序)。

### 产物头部记录

```text
! Manual whitelist: Lists/whitelist.txt  (11 domains)
! Manual blocklist: Lists/blocklist.txt  (0 domains)
! Manual append   : Lists/Append.txt  (1164 rules / 153 comments, passed through verbatim)
```

> 三个文件默认只有注释、无规则，初始状态对产物**零影响**。推送后 Actions 下次运行自动纳入。

## 数据处理与许可

| 想了解 | 见 |
|---|---|
| 31 个上游源的清单与许可证 | [docs/rules-and-license.md](docs/rules-and-license.md#一数据处理规则) |
| 清洗规则明细（哪些规则被丢弃） | [docs/rules-and-license.md](docs/rules-and-license.md#清洗规则明细) |
| **黑白名单 / Append / 上游源的优先级** | [docs/rules-and-license.md](docs/rules-and-license.md#优先级顺序) |
| 代码与产物的许可差异、你的义务 | [docs/rules-and-license.md](docs/rules-and-license.md#二许可说明) |
| Lite / Slim 的详细参数与实测数据 | [docs/analysis.md](docs/analysis.md) |

简要说明：

- **代码**（脚本、工作流、文档）为 **MIT** — [LICENSE](LICENSE)
- **产物**（`out/` 四份列表）为 **GPL-3.0** — [LICENSE-GPL-3.0](LICENSE-GPL-3.0)
  - 原因：产物是上游黑名单的汇编，版权继承自输入源，而上游多为 GPL-3.0
  - 仅订阅使用无需任何操作；再分发产物需遵守 GPL-3.0

## 免责声明

- 所有规则来自第三方公开列表，本项目仅做机械合并、格式转换与去重，**不对上游内容作正确性担保**
- 误拦正常服务时，请在 `Lists/whitelist.txt` 中添加对应域名
- 使用本列表产生的任何后果由使用者自行承担

