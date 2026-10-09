# Merged DNS Blocklist（合并 DNS 拦截列表）

将 **31 个上游**黑名单/去广告列表（3 个主源 + 28 个附加源）**自动拉取 → 格式清洗 → 整行精确去重 → 合并**
为 AdGuard 语法列表，可供 [AdGuard Home](https://github.com/AdguardTeam/AdGuardHome) 作为 DNS 拦截清单订阅使用。

每次运行产出**四套并列的列表**，可按设备性能与拦截强度任选其一订阅（同时订阅也不冲突）：

| 版本 | 产物文件 | 规则量 | 上游源 | 适用场景 |
|---|---|---|---|---|
| **Full 版** | `out/merged_dns_rules.txt` | 约 32 万条 | 21 个（3 主源 + 18 附加源） | 性能充足的设备，拦截面与资源占用的平衡点 |
| **Pro 版** | `out/merged_dns_rules_pro.txt` | 约 53 万条 | 31 个（3 主源 + 28 附加源） | 追求最大拦截覆盖，接受更高内存占用 |
| **Lite 版** | `out/merged_dns_rules_lite.txt` | 约 14.6 万条 | 国内向 12 个 | 中等配置设备，优先保留国内域名拦截 |
| **Slim 版** | `out/merged_dns_rules_slim.txt` | 约 12.9 万条 | 仅国内向 11 个 | **229MB 级内存的低配软路由**，父域无损收敛 |

> **Full 与 Pro 的区别**：Pro 在 Full 基础上额外并入 10 个补充源（Hblock、Spam404、halflife、AWAvenue、AdGuard Chinese、scamblocklist、NoCoin、Peter Lowe、Dan Pollock、neohosts），规则量约 1.7 倍。这些源偏重**反诈/恶意域名**且含大量廉价 TLD，若只需拦截广告，Full 版已足够。

## 特性

- **多格式清洗**：自动识别 hosts 格式（`0.0.0.0 域名`）、adblock 格式（`||域名^`）与裸域名格式，统一转换为 AdGuard 语法
- **整行精确去重**：只删除完全相同的规则，不改写保留规则的写法
- **父域无损收敛**：`||a.com^` 已覆盖 `b.a.com`，因此删除所有被父域规则覆盖的子域规则，**不损失任何拦截能力**
- **完整保留白名单**：上游的 `@@` 白名单规则置于合并文件末尾，避免正常服务被误拦
- **剔除 DNS 层无法表达的内容**：带路径规则、`$domain=` / `$app=` 站点限定规则、元素隐藏规则（`##`）、正则规则
- **排除翻墙/加速类条目**：指向非本地 IP 的 hosts 重定向条目一律不纳入
- **自定义名单**：`Lists/` 下三个手写文件（白名单 / 拦截名单 / 黑白混写）可手动增补，参与全部版本构建（见下文）
- **四版本产物**：覆盖从最大拦截到 229MB 低配软路由的全部场景
- **各版互不冲突**：四套列表共用同一份白名单，且都会剔除白名单中已有的域名，不会出现「A 版拦截 / B 版放行」的矛盾
- 合并文件头部自动写入生成时间、来源与统计信息，便于审计
- **全自动更新**：GitHub Actions 云端定时拉取上游并重建四套列表，仅在有变化时提交

## 目录结构

代码按版本分目录存放，公共部分（下载、清洗）留在根目录：

```
.
├── fetch_sources.py          # 公共：下载 31 个上游 + Lite 专用上游 → Cache/
├── integrate_sources.py      # 公共：附加源清洗（多格式解析 → 统一为 ||域名^）
├── CHANGELOG.md              # 版本变更记录
│
├── Full/                     # Full 版：21 个源（3 主源 + 18 附加源）
│   └── merge_dedup.py        #   → out/merged_dns_rules.txt
├── Pro/                      # Pro 版：31 个源（在 Full 基础上 +10 补充源）
│   └── merge_dedup_pro.py    #   → out/merged_dns_rules_pro.txt（复用 merge_dedup 的合并逻辑）
├── Lite/                     # Lite 版：国内向源，优先国内域名
│   └── build_lite.py         #   → out/merged_dns_rules_lite.txt
├── Slim/                     # Slim 版：仅国内源 + 父域无损收敛
│   └── build_lite_slim.py    #   → out/merged_dns_rules_slim.txt
│
├── Cache/                    # 上游源文件缓存（脚本自动拉取，不入库）
│   ├── raw/                  #   主源 + Lite 专用上游
│   ├── sources/              #   18 个附加源（Full 使用）
│   └── sources_pro/          #   10 个 Pro 专用补充源
├── Lists/                    # 手动维护的名单（入库，参与全部四个版本）
│   ├── whitelist.txt         #   自定义白名单（只放行）
│   ├── blocklist.txt         #   自定义拦截名单（只拦截）
│   └── mixed.txt             #   黑白混写（@@ 前缀表示放行）
├── out/                      # 最终产物（入库，供订阅）
│   ├── integrated_extra.txt              # 中间产物（不入库）
│   ├── integrated_extra_pro.txt          # 中间产物（不入库）
│   ├── excluded_redirect_entries*.txt    # 中间产物（不入库）
│   ├── merged_dns_rules.txt              # Full 版
│   ├── merged_dns_rules_pro.txt          # Pro 版
│   ├── merged_dns_rules_lite.txt         # Lite 版
│   └── merged_dns_rules_slim.txt         # Slim 版
├── .github/workflows/
│   └── update.yml            # GitHub Actions 定时工作流（每 30 分钟）
└── .gitignore                # 忽略 Cache/、中间产物、__pycache__、test/、temp/
```

> 四个版本目录中的脚本**只读取** `Cache/` 的源文件与 `out/` 中的产物，彼此不干扰；
> 各版本脚本可独立运行，但存在顺序依赖：
> `integrate_sources.py`（Full 与 Pro 各跑一次）→ `Full/` → `Pro/` → `Lite/` 与 `Slim/`（后两者以 Full 产物为白名单基准）。

## 使用方法

更新流程已完全托管在 GitHub Actions 上，本地无需运行任何脚本。

### 方式一：GitHub Actions 云端自动更新（默认方式）

不需要本地机器开机，云端每 30 分钟自动执行：

1. `.github/workflows/update.yml` 已随仓库提供，**无需再配置任何脚本**；
2. **首次部署需确认一次仓库设置**：`Settings → Actions → General → Workflow permissions` 选择 **Read and write**，否则工作流没有权限把产物推回仓库；
3. 想立刻验证：打开 `Actions` 标签页 → 选择 **Update merged DNS rules** → **Run workflow**。

工作流每次执行：拉取 31 个源 + Lite 专用上游 → 格式清洗（Full 与 Pro 各一次）→ 合并去重（Full）→ 合并去重（Pro）→ 构建 Lite 版 → 构建 Slim 版 → **仅在有变化时**提交推送（四套产物一起提交）。

> 说明：GitHub 的定时触发为每 30 分钟（UTC 的 0 分与 30 分），高峰期可能有数分钟到数十分钟延迟；规则无变化时不产生提交。

### 方式二：本地手动运行（可选/应急）

日常更新由云端 Actions 全自动完成，**本地无需运行任何脚本**。
仅在需要本地排查、或临时离线生成规则时，按顺序手动执行：

前置依赖：[Python 3](https://www.python.org/downloads/)（安装时勾选 **py launcher**）。

```bat
py fetch_sources.py             :: 下载全部上游 → Cache/
py integrate_sources.py         :: 清洗 Full 版附加源（18 个）
py integrate_sources.py --src-dirs Cache/sources Cache/sources_pro ^
    --out out/integrated_extra_pro.txt ^
    --out-excluded out/excluded_redirect_entries_pro.txt ^
    --title "Integrated extra sources for PRO (non-VPN only)"   :: 清洗 Pro 版附加源（28 个）
py Full\merge_dedup.py          :: 生成 Full 版（必须在 integrate 之后）
py Pro\merge_dedup_pro.py       :: 生成 Pro 版（复用 Full 的合并逻辑）
py Lite\build_lite.py           :: 生成 Lite 版（需要 Full 产物作白名单基准）
py Slim\build_lite_slim.py      :: 生成 Slim 版（同上）
```

产物输出到 `out/`，文件名与云端一致；若需要提交推送，自行执行 `git add` / `commit` / `push` 即可。

### 订阅

在 AdGuard Home → 过滤器 → DNS 拦截清单中订阅（任选，或同时订阅均无冲突）：

| 版本 | 规则量 | 订阅地址 |
|---|---|---|
| **Full 版** | 约 32 万 | `https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt` |
| **Pro 版** | 约 53 万 | `https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_pro.txt` |
| Lite 版 | 约 14.6 万 | `https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt` |
| **Slim 版**（229MB 级设备） | 约 12.9 万 | `https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt` |

列表随上游自动更新（云端定时检查，通常每 4–6 小时一次）。

## 订阅加速镜像（GitHub 直连慢/超时时选用）

AdGuard Home 是**由您的设备去拉取规则**，国内网络直连 `raw.githubusercontent.com` 常常很慢甚至超时。
此时可将下表任意一条地址粘贴到「DNS 拦截清单」使用（按推荐程度排序，**按设备性能选择对应那一列**）：

> **建议同时添加 gh-proxy.com 与 jsDelivr 两条**（AGH 支持多个过滤器，重复规则无害）。两者互为兜底，任一条抖动时另一条仍能拉到。选择依据见下方 [AGH 订阅稳定性建议](#agh-订阅稳定性建议) 一节。

| 方式 | 缓存时长 | Full 版（约 32 万条） | Pro 版（约 53 万条） |
|---|---|---|---|
| **gh-proxy.com**（首选：TTFB 最稳，波动仅 1.4 倍，缓存最短） | 60 秒 | https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt | https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_pro.txt |
| **jsDelivr CDN**（备用：偶有 TTFB 尖峰，见下节） | **最长 12 小时** | https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules.txt | https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_pro.txt |
| 直连 raw.githubusercontent.com（**不推荐**：耗时波动可达 31 倍，偶发全部失败） | 5 分钟 | https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt | https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_pro.txt |

### Lite 版（约 14.6 万条）

| 方式 | Lite 版地址 |
|---|---|
| **gh-proxy.com** | https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt |
| **jsDelivr CDN** | https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_lite.txt |
| 直连 raw | https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt |

### Slim 版（约 12.9 万条）

| 方式 | Slim 版地址 |
|---|---|
| **gh-proxy.com** | https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt |
| **jsDelivr CDN** | https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_slim.txt |
| 直连 raw | https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt |

一次性复制全部地址：

Full 版：

```text
https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt
https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules.txt
https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt
```

Pro 版：

```text
https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_pro.txt
https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_pro.txt
https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_pro.txt
```

Lite 版：

```text
https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt
https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_lite.txt
https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt
```

Slim 版：

```text
https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt
https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_slim.txt
https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt
```

注意事项：

- **缓存时长直接决定「订阅多久才更新」**，实测数据（2026-10-06）：

  | 渠道 | `Cache-Control` | 实际含义 |
  |---|---|---|
  | gh-proxy.com | `max-age=60` | 1 分钟，几乎实时 |
  | raw.githubusercontent.com | `max-age=300` | 5 分钟 |
  | jsDelivr | `s-maxage=43200` | **12 小时**，最慢 |

- **jsDelivr 缓存问题**：其 CDN 边缘节点会缓存最长 12 小时，且各节点（`cdn` / `fastly` / `gcore` / `testingcf`）缓存互相独立——可能某个节点已是新版而另一个仍是旧版。若发现拉取到的规则数明显偏少，按以下任一方式处理：
  1. 换用上表首行的 **gh-proxy.com**（1 分钟缓存，最可靠）；
  2. 换用其它 jsDelivr 节点，例如把 `cdn.jsdelivr.net` 换成 `fastly.jsdelivr.net` 或 `gcore.jsdelivr.net`；
  3. 主动清除 jsDelivr 缓存（浏览器打开即可，返回 `"status": "finished"` 表示成功）：
     - Full 版 https://purge.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules.txt
     - Pro 版 https://purge.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_pro.txt
     - Lite 版 https://purge.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_lite.txt
     - Slim 版 https://purge.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_slim.txt

  > 该清除操作已写入 Actions 工作流：每次产物有变化时会自动 purge 上述四个地址。
- **如何确认自己拿到的是最新版**：打开订阅地址看文件头部，比对 `! Block rules:` 与 `! Generated:` 两个字段。若与仓库 [out/](out/) 目录中的文件不一致，说明命中了旧缓存。
- jsDelivr 免费加速**公开仓库**且单文件需 ≤20 MB（Pro 约 12 MB、Full 约 7.2 MB、Lite 约 3.2 MB、Slim 约 2.8 MB，均满足）。
- 第三方代理站可能限速或失效，失效就换下一条。
- 加速站属于第三方服务，仅作下载加速，不影响列表内容本身。

## AGH 订阅稳定性建议

> 本节数据由本仓库在 **2026-10-09** 于中国大陆家庭宽带环境下实测得出（多轮直连，未经代理）。

AdGuard Home 对过滤器源有自己的超时判定：**某次拉取超时或连接被重置，就会把该订阅标记为「连接不稳定」**，并在后续拉取中降低优先级甚至暂停。因此对 AGH 而言，**「每次都能在几秒内响应」比「平均速度快」更重要**——偶发的 20 秒尖峰比稳定的 2 秒更容易触发告警。

### 各渠道实际表现

> 下列两组数据来自**不同时段的两次独立测试**，raw 直连的表现差异很大（一次全失败、一次全成功）——这本身就是它不可靠的证据：能通但不可预期。

**测试一：TTFB（首字节时间）稳定性**，同一文件连续 5 轮：

| 渠道 | 各轮 TTFB（秒） | 平均 | 峰值/均值 | 评价 |
|---|---|---|---|---|
| **gh-proxy.com** | `0.52 0.32 0.31 0.29 0.41` | **0.37s** | **1.4x** | ✅ 最稳 |
| jsDelivr `cdn` | `0.27 1.18 0.61 0.43 0.31` | 0.56s | 2.1x | ⚠️ 尚可 |
| jsDelivr `fastly` | `1.64 0.25 20.51 0.52` + 1 次失败 | 5.73s | **3.6x** | ❌ 易触发超时 |
| raw 直连 | 5 轮全部失败 | — | — | ❌ 不可靠 |

**测试二：成功率**（3 轮，均校验返回内容是否为真规则文件）：

| 渠道 | 成功率 | 平均耗时 |
|---|---|---|
| gh-proxy.com | 100% | 0.39s |
| jsDelivr `cdn` | 100% | 0.90s |
| jsDelivr `fastly` | 100% | 2.12s |
| jsDelivr `gcore` | 33% | 2.09s |
| ghfast.top | 33% | 0.79s |
| raw 直连 | 100%（耗时波动 **0.34–10.69s**，达 31 倍） | 4.03s |

**综合判断**：raw 直连两次测试结果相反，且耗时波动达 31 倍，不能作为 AGH 的稳定订阅源；gh-proxy.com 是唯一两项测试都稳定的渠道。

### 为什么 jsDelivr 偶尔会被判为「连接不稳定」

用 4 个国内公共 DNS（223.5.5.5 / 119.29.29.29 / 180.76.76.76 / 114.114.114.114）解析 jsDelivr 各节点，**全部返回境外 IP**：

| 域名 | 解析结果 | 归属 |
|---|---|---|
| `cdn.jsdelivr.net` | `104.17.207.5` / `151.101.1.229` | Cloudflare / Fastly（境外） |
| `fastly.jsdelivr.net` | `151.101.65.229` 等 | Fastly（境外） |
| `gcore.jsdelivr.net` | `104.17.207.5` | Cloudflare（境外） |

**没有任何国内节点 IP**。每次拉取都要跨境，于是出现「多数时候几百毫秒、偶尔 20 秒」的尖峰，这正是 AGH 判定不稳定的直接原因。

此外 jsDelivr 的边缘节点缓存最长 12 小时（见上节），且各节点缓存互相独立——同一时刻不同节点可能返回不同版本，这也容易被误认为「连接有问题」。

### 推荐配置

**优先使用 gh-proxy.com**，它的 TTFB 波动最小（1.4x），不会触发 AGH 的超时判定：

```text
https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt
```

**建议同时订阅两条**（AGH 允许添加多个过滤器，重复规则无害），任一条故障时另一条兜底：

```text
首选  https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt
备用  https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_slim.txt
```

> 把上面两条里的 `merged_dns_rules_slim.txt` 换成 `merged_dns_rules.txt`（Full）、`merged_dns_rules_pro.txt`（Pro）或 `merged_dns_rules_lite.txt`（Lite）即可用于其它版本。

### 若已被 AGH 标记为不稳定

1. 在「过滤器 → DNS 拦截清单」中把该条**删掉重新添加**，AGH 会重置其失败计数；
2. 换成 gh-proxy.com 地址；
3. 若是内容问题（规则数偏少）而非连接问题，参考上节的 jsDelivr 缓存说明处理。

### 关于第三方加速服务的现状

同期实测（直连）**已失效**的常见加速站，供参考——网上流传的可用清单往往严重滞后：

| 域名 | 实测结果 |
|---|---|
| `ghproxy.net` | 完全不可达 |
| `gh.llkk.cc` | 完全不可达 |
| `ghproxy.cn` | 返回 HTML 中间页，非规则文件 |
| `gh.con.sh` | 服务已停（"Suspent due to abuse report"） |
| `ghp.ci` | TLS 握手失败 |
| `ghgo.xyz` | 返回 HTML 页面 |
| `gitclone.com` | HTTP 500 |
| `ghproxy.homeboyc.cn` | HTTP 403 |
| `ghfast.top` | 3 轮中仅 1 轮成功 |
| `hub.gitmirror.com` | 完全不可达 |
| `ghproxy.link`（官方地址发布站） | 国内不可达 |

> **结论**：国内 GitHub 加速生态变动频繁，任何静态清单都会很快过时。本项目因此推荐 **gh-proxy.com + jsDelivr 双订阅**，而不是依赖单一渠道。加速站失效时换下一条即可，列表内容本身不受影响。

## 关于国内网络环境的实测结论

### 结论

**国内广告域名生态极度碎片化，已经到了"去重几乎无处可去"的程度。**

这不是情绪化判断，而是本项目在合并 11 个国内规则源（`adblockdnslite`、`anti-ad`、`yhosts`、`adgk`、`easylistchina`、`ad-wars`、`goodbyeads_dns`、`cjx-annoyance`、`xinggsf-rule`、`xinggsf-mv`、`1024_hosts`）时得到的实测结果。

### 理由与数据

**证据一：11 个独立维护的规则源，去重后只剩 12.8 万条**

| 处理阶段 | 规则数 | 说明 |
|---|---|---|
| 11 个源并集 | 143,157 | 多个源分别独立维护 |
| 父域无损收敛后 | **128,368** | 仅减少 14,789 条（**10.3%**） |

**11 个源、上百人年的维护积累，交叉重叠只带来了 10% 的冗余。** 如果国内广告域名集中在少数几个平台手里，各源之间的重叠率会高得多。对比国际源（StevenBlack、EasyList、AdAway、Mvps 等 4 源）：并集 126,907 条，父域收敛后 90,796 条，**减少 28.5%**——是国内向源的 **2.7 倍**。

**证据二：12.8 万条规则散落在 10.8 万个独立注册域上**

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

Lite 版把规则量压到全量的约 **27%**（约 14.6 万条，3.15 MB），在保证国内广告拦截效果的前提下，降低 AdGuard Home 的内存占用与匹配开销。

### 与 Full 版的关系

| 项 | 说明 |
|---|---|
| 产出方式 | `build_lite.py` 独立生成，**不修改 Full 版的任何产出逻辑** |
| 白名单 | **直接沿用 Full 版白名单**（278 条） |
| 冲突处理 | Lite 屏蔽集会**剔除 Full 版白名单中的域名**，杜绝两版结论相反 |
| 订阅关系 | 两版可单独订阅，也可同时订阅（同时订阅时 Lite 是子集，无副作用） |

### 组成来源（按优先级）

| 优先级 | 源 | 说明 |
|---|---|---|
| P1 | **adblockdnslite**（217 Lite） | 官方 Lite 版，仅针对国内域名拦截 |
| P2 | anti-AD、ADgk、EasyList China、yhosts、大圣净化 | 国内向主力源 |
| P3 | CJX's Annoyance、乘风规则、GOODBYEADS | 国内补充 |
| P4 | 1024_hosts | 成人/赌博站点 |
| P5 | URLHaus（filter_11） | 恶意网站/钓鱼（安全类，可用 `--no-security` 去掉） |

> 注意：Full 版中的国际源（EasyList、EasyPrivacy、StevenBlack、Mvps、AdAway、YousList 等）**不参与 Lite 版**，这是体量下降的主要来源。

### 手动调整

```bat
py Lite\build_lite.py                    :: 默认：全部国内向源（约 14.6 万条）
py Lite\build_lite.py --max 120000       :: 限到 12 万条，超限时按「优先级 → .cn 优先 → 域名长度」裁剪
py Lite\build_lite.py --no-security      :: 不纳入 URLHaus 安全源（-3,727 条）
```

## Slim 版说明（面向 229MB 级内存设备）

### 定位

在 Lite 版基础上进一步压缩到 **约 12.9 万条（2.76 MB）**，适用于内存 256MB 上下的低配软路由。

### 与 Lite 版的差异

| 项 | Lite 版 | Slim 版 |
|---|---|---|
| 规则数 | 145,737 | **128,339** |
| 上游源 | 国内向 11 源 + URLHaus | **仅国内向 11 源**（不含 URLHaus） |
| 压缩手段 | 仅整行去重 | 整行去重 + **父域无损收敛** |
| 整域放行 | 无 | **简书整域放行** |
| 保底清单 | 无 | **4 条强制保留** |

**父域收敛**是 Slim 版独有的无损优化：AGH 中 `||a.com^` 已覆盖 `b.a.com`，因此所有被父域规则覆盖的子域规则都被删除，**不损失任何拦截能力**。

### 整域放行（按维护者要求）

| 域名 | 策略 |
|---|---|
| `jianshu.com` | **整域放行**（上游误判） |

> 360 品牌保护已**彻底移除**（含相关代码，非仅失效）。早期版本曾对 360 系列做「只拦广告子域、主域与功能域放行」的特殊处理，现 360 系列与其他域名一视同仁，一律照常拦截。
>
> 附注：上游 `anti-ad` 自带 2 条 360 白名单（`@@||profile*.se.360.cn^`、`@@||s.mvconf.f.360.cn^`），属上游规则内容，按「机械合并、不干预内容」原则原样保留。

### 保底清单

以下 4 个国内广告域在无损收敛后可能被挤出，因此**强制保留**（`MUST_KEEP`）：

| 域名 | 说明 |
|---|---|
| `tanx.com` | 阿里妈妈广告交易平台（原易传媒 Tanx） |
| `jiathis.com` | 加网分享按钮 |
| `ad.m.iqiyi.com` | 爱奇艺移动端广告 |
| `ad.jia.360.cn` | 360 广告投放域 |

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
| 12.8 万（默认） | 125–250 MB |
| 8 万（`--max 80000`） | 78–156 MB |
| 5 万（`--max 50000`） | 49–98 MB |

> **该数值为估算，不是实测值**——准确占用需在目标设备上运行 AdGuard Home 后查看其内存统计。若 229MB 设备运行默认版吃力，请用 `--max` 下调。

## 自定义名单（手动维护）

除了自动拉取的上游源，本项目还支持三个**手动维护**的名单，位于 `Lists/` 目录，**参与全部四个版本（Full / Pro / Lite / Slim）的构建**：

| 文件 | 作用 | 放行写法 |
|---|---|---|
| `Lists/whitelist.txt` | 只放行 | 裸域名即可（无需前缀） |
| `Lists/blocklist.txt` | 只拦截 | 裸域名即可（无需前缀） |
| `Lists/mixed.txt` | **黑白混写** | 需显式写 `@@` 前缀 |

### 书写格式

大小写不敏感，两种语法都支持：

```text
# whitelist.txt / blocklist.txt：裸域名即可
example.com

# mixed.txt：靠前缀区分黑白
example.com            ← 拦截（裸域名默认按拦截处理）
||example.com^         ← 拦截
@@||example.com^       ← 放行
```

- 以 `!` 或 `#` 开头的行是注释，空行忽略
- **写主域即可覆盖全部子域**（AdGuard Home 中 `@@||example.com^` 已含子域）
- 不支持通配符（`*.example.com`）、路径（`a.com/path`）、`$` 修饰符——这类写法会被忽略并打印警告
- ⚠️ **`mixed.txt` 里的裸域名按「拦截」处理**，要放行必须显式写 `@@`

### 优先级与冲突处理

放行一律优先于拦截。三者与上游的优先级从高到低：

```
1. Lists/whitelist.txt          手写白名单
2. Lists/mixed.txt 的 @@ 条目    混合源放行
3. Lists/blocklist.txt          手写拦截名单
4. Lists/mixed.txt 的拦截条目    混合源拦截（裸域名）
5. 上游源
```

| 情况 | 处理 |
|---|---|
| 同一域名写在 whitelist 与 blocklist | **放行优先**，拦截条目被忽略并打印警告 |
| 同一域名在 mixed 与单用途名单中冲突 | **放行优先**，打印警告 |
| 同一域名在 mixed.txt 内既写放行又写拦截 | **放行优先**（同一文件内自动处理） |
| 手写放行的域名同时在上游黑名单中 | 该域及其**子域**的上游黑名单条目被自动移除（避免既拦又放） |
| 手写拦截的域名同时在上游白名单中 | 该条被忽略（兜底，防止自我矛盾） |

### 生效方式

推送到仓库后，GitHub Actions 会在下次运行时自动纳入，无需改脚本。产物头部会记录当前生效的条数：

```text
! Manual whitelist: Lists/whitelist.txt  (0 domains)
! Manual blocklist: Lists/blocklist.txt  (0 domains)
! Manual mixed    : Lists/mixed.txt  (allow 0 / block 0)
```

> 三个文件默认只有注释、不含任何规则，因此初始状态下对产物**零影响**。

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

### 附加源（28 个，经格式清洗）

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
| **halflife（My AdFilters）** | https://github.com/sbwml/halflife-list | 国内综合去广告（ABP 格式） |
| **AWAvenue Ads Rule** | https://github.com/TG-Twilight/AWAvenue-Ads-Rule | 国内去广告（GPL-3.0） |
| **Spam404** | https://github.com/Spam404/lists | 诈骗/盗版/外挂站点（纯域名格式） |
| **Peter Lowe's List** | https://pgl.yoyo.org/adservers/ | 老牌广告服务器列表 |
| **Dan Pollock's List** | https://someonewhocares.org/hosts/ | 综合拦截（0.0.0.0 版） |
| **NoCoin Filter List** | https://github.com/hoshsadiq/adblock-nocoin-list | 浏览器挖矿域名（MIT） |
| **neohosts** | https://github.com/neoFelhz/neohosts | 国内综合（已停更） |
| **Scam Blocklist** | https://github.com/durablenapkin/scamblocklist | 诈骗域名（MIT） |
| **AdGuard Chinese filter** | https://github.com/AdguardTeam/AdguardFilters | AdGuard 官方中文过滤器（GPL-3.0） |
| **Hblock** | https://github.com/hectorm/hblock | 综合拦截（MIT；经官方镜像 [hmirror](https://github.com/hectorm/hmirror) 获取） |

**附加源清单来源**：[otobtc/ADhosts](https://github.com/otobtc/ADhosts) —— 本项目的附加源即从该仓库的推荐列表中筛选非翻墙类源，再统一做格式清洗。标粗的 10 个源于 v2.1.0 从 [BlueSkyXN/AdGuardHomeRules](https://github.com/BlueSkyXN/AdGuardHomeRules) 引用的规则源中补充引入。

> 附加源各自适用其仓库声明的许可，使用与再分发前请查阅对应仓库。
>
> `Hblock` 官方站点 `hblock.molinero.dev` 在部分网络环境不可达，本项目改用其官方镜像项目 `hectorm/hmirror` 提供的同源数据（纯域名格式，体积更小）。

### 清洗规则明细

| 输入形式 | 处理 |
|---|---|
| hosts 行 `0.0.0.0 域名` / `127.0.0.1 域名` / `::1 域名` | 视为屏蔽，转为 `\|\|域名^` |
| hosts 行 `其它IP 域名` | 视为重定向（翻墙/加速/解锁），**排除**并单独记录到 `out/excluded_redirect_entries.txt` |
| 裸域名行（无 IP 前缀，如 Spam404 / Hblock） | 视为屏蔽，转为 `\|\|域名^` |
| `\|\|域名^` / `\|http://域名^` | 保留（仅接受纯域名形式） |
| `\|\|域名^/路径`（带路径） | **丢弃**（DNS 层无法表达路径，抽成整域会造成误拦） |
| `\|\|域名^$domain=x` / `$app=x`（站点/应用限定） | **丢弃**（转成整域会严重放大范围） |
| `@@\|\|域名^`（无修饰符白名单） | 保留为白名单 |
| `@@\|\|域名^$generichide` 等带修饰符白名单 | **丢弃**（场景限定豁免，转成无条件豁免会放行本该拦截的广告域） |
| 元素隐藏规则（含 `##`、`#@#`、`#?#`、`#$#`、`#%#`） | **丢弃**（DNS 层无效） |
| 正则规则 `/regex/`、扩展名式规则（如 `\|\|*.js`）、IP 形式规则 | **丢弃** |

> 被整体排除的翻墙/加速专用源：`googlehosts`（内容全为 IP 重定向）。
> 另外 Koolproxy / Adbyby（代理端专用格式，非 DNS 规则）未纳入。

## 免责声明

- 拦截列表可能包含**误报**，启用后请关注日常访问，必要时在 AdGuard Home 中添加例外。
- 本项目仅做机械合并、格式转换与去重，不对上游规则内容作正确性担保。

## License

本项目（脚本与文档）采用 **GNU General Public License v3.0（GPL-3.0）**，详见仓库根目录 [LICENSE](LICENSE) 文件。

> 注意：**合并产物（域名数据）的再分发仍受上游各自许可约束**（见上表），发布时请保留来源与许可声明。
