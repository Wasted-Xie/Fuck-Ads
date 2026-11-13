# Merged DNS Blocklist（合并 DNS 拦截列表）

将 **31 个上游**黑名单/去广告列表（3 主源 + 28 附加源）自动拉取 → 格式清洗 → 整行精确去重 → 合并为 AdGuard 语法列表，供 [AdGuard Home](https://github.com/AdguardTeam/AdGuardHome) 订阅使用。

每次运行产出**四套并列的列表**，按设备性能任选其一（同时订阅也不冲突）：

| 版本 | 产物 | 规则量 | 上游源 | 适用场景 | 订阅 |
|---|---|---|---|---|---|
| **Full** | `merged_dns_rules.txt` | 约 36 万 | 21 个（3 主源 + 18 附加源） | 性能充足设备，拦截与占用的平衡点 | [订阅](https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt) |
| **Pro** | `merged_dns_rules_pro.txt` | 约 56 万 | 31 个（3 主源 + 28 附加源） | 追求最大拦截覆盖，接受更高内存 | [订阅](https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_pro.txt) |
| **Lite** | `merged_dns_rules_lite.txt` | 约 15 万 | 国内向 12 个 | 中等配置，优先国内域名 | [订阅](https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt) |
| **Slim** | `merged_dns_rules_slim.txt` | 约 14 万 | 仅国内向 11 个 | **229MB 级内存低配软路由** | [订阅](https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt) |

> 上表「订阅」链接走 gh-proxy.com（国内可直连）。其它加速渠道见 [订阅加速镜像](#订阅加速镜像)。

> **Full 与 Pro 的区别**：Pro 额外并入 10 个补充源（Hblock、Spam404、halflife、AWAvenue、AdGuard Chinese、scamblocklist、NoCoin、Peter Lowe、Dan Pollock、neohosts），规则量约 1.7 倍。这些源偏重**反诈/恶意域名**，若只需拦截广告，Full 已足够。

## 特性

- **多格式清洗**：识别 hosts（`0.0.0.0 域名`）、adblock（`||域名^`）与裸域名格式，统一转为 AdGuard 语法
- **整行精确去重**：只删完全相同的规则，不改写保留规则的写法
- **父域无损收敛**：`||a.com^` 已覆盖 `b.a.com`，删除被覆盖的子域规则**不损失拦截能力**
- **完整保留白名单**：上游 `@@` 规则置于文件末尾，避免误拦正常服务
- **剔除 DNS 层无法表达的内容**：带路径规则、`$domain=` / `$app=` 限定规则、元素隐藏（`##`）、正则
- **排除翻墙/加速条目**：指向非本地 IP 的 hosts 重定向一律不纳入
- **自定义名单**：`Lists/` 下三个手写文件参与全部版本构建
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
├── docs/analysis.md          # 详细实测数据与参数说明
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

### 订阅

在 AdGuard Home → 过滤器 → DNS 拦截清单中添加以下地址（点击即复制到剪贴板）：

| 版本 | 规则量 | 订阅地址 |
|---|---|---|
| **Full** | 约 36 万 | [订阅](https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt) |
| **Pro** | 约 56 万 | [订阅](https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_pro.txt) |
| Lite | 约 15 万 | [订阅](https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt) |
| Slim | 约 14 万 | [订阅](https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt) |

> 上表为 raw 直连地址，国内常超时。**推荐使用文档开头表格中的 gh-proxy 订阅链接**，其它加速渠道见下方 [订阅加速镜像](#订阅加速镜像)。

## 订阅加速镜像

AGH 由**你的设备**拉取规则，国内直连 `raw.githubusercontent.com` 常超时。下表按稳定性排序，任选一条添加到「DNS 拦截清单」。

**建议同时添加 gh-proxy.com 与 jsDelivr 两条**（AGH 支持多过滤器，重复规则无害），互为兜底。

| 渠道 | 缓存 | 特点 |
|---|---|---|
| **gh-proxy.com** | 60 秒 | TTFB 最稳（波动 1.4 倍），**首选** |
| **jsDelivr** | 最长 12 小时 | 偶有 TTFB 尖峰，作备用 |
| raw 直连 | 5 分钟 | 耗时波动可达 31 倍，**不推荐** |

### gh-proxy.com（首选）

| 版本 | 订阅地址 |
|---|---|
| **Full** | [订阅](https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules.txt) |
| **Pro** | [订阅](https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_pro.txt) |
| Lite | [订阅](https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_lite.txt) |
| Slim | [订阅](https://gh-proxy.com/https://raw.githubusercontent.com/Wasted-Xie/Fuck-Ads/main/out/merged_dns_rules_slim.txt) |

### jsDelivr（备用）

| 版本 | 订阅地址 |
|---|---|
| **Full** | [订阅](https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules.txt) |
| **Pro** | [订阅](https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_pro.txt) |
| Lite | [订阅](https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_lite.txt) |
| Slim | [订阅](https://cdn.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_slim.txt) |

> jsDelivr 缓存异常时，把 `cdn.jsdelivr.net` 换成 `fastly.jsdelivr.net` 或 `gcore.jsdelivr.net` 再试。
> 也可主动清缓存（浏览器打开，返回 `"status": "finished"` 即成功）：[清 Full](https://purge.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules.txt) · [清 Pro](https://purge.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_pro.txt) · [清 Lite](https://purge.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_lite.txt) · [清 Slim](https://purge.jsdelivr.net/gh/Wasted-Xie/Fuck-Ads@main/out/merged_dns_rules_slim.txt)
>
> 该清除已写入 Actions：产物有变化时自动 purge 四个地址。

**确认拿到最新版**：看文件头部 `! Block rules:` 与 `! Generated:`，与仓库 [out/](out/) 不一致即命中旧缓存。

## AGH 订阅稳定性建议

AGH 对过滤器源有超时判定：**某次拉取超时或连接被重置，就会标记该订阅「连接不稳定」**。因此对 AGH 而言「每次几秒内响应」比「平均速度快」更重要——偶发 20 秒尖峰比稳定的 2 秒更容易触发告警。

**为何 jsDelivr 偶尔不稳定**：用 4 个国内公共 DNS 解析其各节点，**全部返回境外 IP**（Cloudflare / Fastly），无任何国内节点。每次拉取都要跨境，于是出现「多数几百毫秒、偶尔 20 秒」的尖峰。

**推荐**：gh-proxy.com 首选（TTFB 波动仅 1.4 倍），jsDelivr 备用，两条同时订阅互为兜底。

**已被标记不稳定时**：删掉该过滤器重新添加（重置失败计数）→ 换成 gh-proxy.com 地址。

> 完整实测数据（各渠道 TTFB、成功率、11 个已失效加速站清单）见 [docs/analysis.md](docs/analysis.md)。

## 自定义名单（手动维护）

`Lists/` 下有三个手写文件，但它们的处理方式**完全不同**：

| 文件 | 处理方式 | 是否参与清洗 |
|---|---|---|
| `whitelist.txt` | 解析为域名 → 加入白名单 | 是 |
| `blocklist.txt` | 解析为域名 → 加入黑名单 | 是 |
| `Append.txt` | **原样追加到产物末尾** | **否** |

### whitelist.txt / blocklist.txt（参与清洗）

裸域名即可，大小写不敏感：

```text
example.com
```

- 以 `!` 或 `#` 开头为注释，空行忽略
- **写主域即覆盖全部子域**（AGH 中 `@@||example.com^` 已含子域）
- 不支持通配符（`*`）、路径（`/`）、`$` 修饰符——这类写法会被忽略并打印警告

两者的冲突处理：

| 冲突情况 | 处理 |
|---|---|
| 同一域名同时写在两个文件 | 放行优先，打印警告 |
| 手写放行的域在上游黑名单中 | 该域**及子域**的上游黑名单条目自动移除 |
| 手写拦截的域在上游白名单中 | 该条被忽略（兜底） |

### Append.txt（不参与清洗）

**这个文件是"扩展区"，不是"名单"。** 它的内容逐行原样追加到产物末尾，构建脚本**不做任何解析、清洗、去重或冲突处理**：

- 不判断 `@@` 前缀，不区分黑白
- 不剥离 `$` 修饰符
- 不过滤通配符 `*`、路径、正则、元素隐藏规则
- 不与 `whitelist.txt` / `blocklist.txt` / 上游源做冲突检查
- 保留注释行（`#` 开头）与原始顺序

换句话说：**你写什么，产物末尾就是什么**，规则是否有效完全由 AdGuard Home 判定。

#### 内容来源

当前内容提取自 [liuzq2002/Adguard-Home-For-Magisk-Mod](https://github.com/liuzq2002/Adguard-Home-For-Magisk-Mod) 的 release 包内 `AdGuardHome.yaml` 的 `user_rules` 字段（1263 条），加上文件头的模板说明注释，以及末尾 2 条手工追加的规则。

- 来源仓库许可证：**MIT**（Copyright 2025 liuzq2002）
- 该仓库 README 声明其规则基础为 **GOODBYEADS**（MIT）+ 自定义增补
- 提取方式：`py extract_agh_rules.py`（本地工具，不入库）

规则构成：1146 条规则（1040 拦截 + 106 放行）+ 152 行分组注释，覆盖各 App 的定向拦截/放行（腾讯、百度、字节、快手、美团、喜马拉雅、哔哩哔哩、网易云等），其中约 91% 的规则不在本项目的其它上游源中。

> **重新提取时注意**：`extract_agh_rules.py` 只输出到 `temp/agh_rules/`，**不会写入 `Lists/Append.txt`**。该文件末尾有手工追加的规则（不在 yaml 中），直接覆盖会丢失。替换前请先比对差异，脚本运行后会打印比对命令。

```text
# 原样保留，不解析
#针对转转App的放行规则，勿删
@@||zhuanzhuan.com^$important
||tnc*-aliec*.zijieapi.com^$important
```

> ⚠️ 因为不参与清洗，**如果你在 `Append.txt` 里写了裸域名（如 `example.com`），它不会像 `blocklist.txt` 那样被自动转成 `||example.com^`**。请直接写完整的 AdGuard 语法。

### 产物头部记录

```text
! Manual whitelist: Lists/whitelist.txt  (5 domains)
! Manual blocklist: Lists/blocklist.txt  (0 domains)
! Manual append   : Lists/Append.txt  (1146 rules / 152 comments, passed through verbatim)
```

> 三个文件默认只有注释、无规则，初始状态对产物**零影响**。推送后 Actions 下次运行自动纳入。

## 数据处理规则

### 主源（3 个，未经格式改写）

由 `merge_dedup.py` 直接读取，**整行精确去重，不做格式改写或豁免**：

| 源 | 许可证 | 内容 |
|---|---|---|
| [URLHaus](https://github.com/AdguardTeam/HostlistsRegistry)（Hostlists #11） | GPL-3.0；数据源头 abuse.ch 无标准开源许可，仅 Fair Use + ToS | 恶意网站/钓鱼/木马 |
| [GOODBYEADS dns](https://github.com/8680/GOODBYEADS) | MIT | 去广告域名 |
| [AdBlock DNS](https://github.com/217heidai/adblockfilters) | GPL-3.0 | 去广告合并域名（含 `@@`） |

> URLhaus 数据"available free of charge under the fair use principles"，商业用途可能需 abuse.ch 商业 API；再分发请遵守其 [ToS](https://urlhaus.abuse.ch/faq/#tos)。

### 附加源（28 个，经格式清洗）

经 `integrate_sources.py` 清洗后合并。Full 用 18 个（`Cache/sources/`），Pro 另加 10 个（`Cache/sources_pro/`）。

| 源 | 许可证 / 说明 |
|---|---|
| yhosts、ad-wars、1024_hosts、xinggsf、cjx-annoyance、adgk | 国内去广告 |
| AdAway、Mvps、YousList、StevenBlack、EasyList、EasyPrivacy、EasyList China | 国际主流（EasyList 系为 GPL-3.0 或 CC BY-SA 3.0） |
| anti-AD、antiadblock、i-dont-care-about-cookies | 综合/专项 |
| **Pro 专用**：Hblock、Spam404、halflife、AWAvenue、AdGuard Chinese、scamblocklist、NoCoin、Peter Lowe、Dan Pollock、neohosts | 反诈/恶意域名为主 |

> 附加源各自适用其仓库声明的许可，使用与再分发前请查阅对应仓库。

### 清洗规则明细

| 输入形态 | 处理 |
|---|---|
| `0.0.0.0 域名` / `127.0.0.1 域名` | 转为 `\|\|域名^` |
| 非本地 IP 的 hosts 重定向 | **排除**（翻墙/加速/解锁类） |
| `\|\|域名^`、`\|\|域名^$important` | 保留（剥离修饰符后取域名） |
| `@@\|\|域名^` | 进白名单 |
| `\|\|域名^$domain=` / `$app=` | **丢弃**（站点限定型，放大范围） |
| 带路径 `/`、正则 `/.../` | **丢弃**（DNS 层无法表达） |
| 元素隐藏 `##`、`#@#`、`#?#`、`#$#`、`#%#` | **丢弃**（非 DNS 层） |
| 裸域名 | 按拦截处理 |

> 上表仅适用于**上游源**与 `whitelist.txt` / `blocklist.txt`。
> `Lists/Append.txt` 不经过上述任何清洗步骤，内容原样追加到产物末尾。

## 免责声明

- 所有规则来自第三方公开列表，本项目仅做机械合并、格式转换与去重，**不对上游内容作正确性担保**
- 误拦正常服务时，请在 `Lists/whitelist.txt` 中添加对应域名
- 使用本列表产生的任何后果由使用者自行承担

## License

本项目**代码与产物适用不同许可**：

| 范围 | 内容 | 许可证 |
|---|---|---|
| 代码与文档 | Python 脚本、Actions 工作流、Markdown | **MIT** — [LICENSE](LICENSE) |
| 规则产物 | `out/` 下四份 `.txt` | **GPL-3.0** — [LICENSE-GPL-3.0](LICENSE-GPL-3.0) |

### 产物为何是 GPL-3.0

`out/` 是多个上游黑名单的汇编，版权状态继承自输入源。按 [GNU GPL FAQ](https://www.gnu.org/licenses/gpl-faq.en.html#GPLOutput)：

> when a program translates its input into some other form, the copyright status of the output inherits that of the input it was generated from.

本项目上游中，EasyList 系（GPL-3.0 或 CC BY-SA 3.0 双许可）、URLHaus、217heidai/adblockfilters、AdguardFilters、AWAvenue、AdAway **均为 GPL-3.0**，故产物整体按 GPL-3.0 分发。

### 关于 Lists/Append.txt

该文件追加的 1164 条规则提取自 [liuzq2002/Adguard-Home-For-Magisk-Mod](https://github.com/liuzq2002/Adguard-Home-For-Magisk-Mod) 的 release（**MIT**，其规则基础 GOODBYEADS 亦为 MIT）。MIT 与 GPL-3.0 兼容，这部分内容可合法地并入 GPL-3.0 产物；但**单独取用 `Append.txt` 时，适用其原始 MIT 许可**。

### 代码为何是 MIT

脚本只做下载、清洗、去重、合并，不含任何上游规则内容。GNU FAQ 亦指出自由软件许可"cannot limit what data you use the interpreter on"——代码许可与它处理的数据无关。

### 你的义务

| 使用方式 | 要求 |
|---|---|
| 仅订阅使用 | 无需任何操作 |
| 再分发 `out/` 列表 | 遵守 GPL-3.0，注明来源与本项目 |
| 单独复用 `Lists/Append.txt` | 遵守 MIT，注明来源 liuzq2002 与 GOODBYEADS |
| 复用/修改脚本 | 遵守 MIT，保留版权声明 |

> 各源许可明细见 [数据处理规则](#数据处理规则)。
