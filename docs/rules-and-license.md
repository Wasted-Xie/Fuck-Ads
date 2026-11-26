# 数据处理规则与许可说明

本文件收纳从 README 移出的详细内容。日常使用只需看 [README](../README.md)。

---

## 一、数据处理规则

### 主源（3 个，未经格式改写）

由 `Full/merge_dedup.py` 直接读取，**整行精确去重，不做格式改写或豁免**：

| 源 | 许可证 | 内容 |
|---|---|---|
| [URLHaus](https://github.com/AdguardTeam/HostlistsRegistry)（Hostlists #11） | GPL-3.0；数据源头 abuse.ch 无标准开源许可，仅 Fair Use + ToS | 恶意网站 / 钓鱼 / 木马 |
| [GOODBYEADS dns](https://github.com/8680/GOODBYEADS) | MIT | 去广告域名 |
| [AdBlock DNS](https://github.com/217heidai/adblockfilters) | GPL-3.0 | 去广告合并域名（含 `@@`） |

> URLhaus 数据「available free of charge under the fair use principles」，商业用途可能需 abuse.ch 商业 API；再分发请遵守其 [ToS](https://urlhaus.abuse.ch/faq/#tos)。

### 附加源（28 个，经格式清洗）

经 `integrate_sources.py` 清洗后合并。Full 用 18 个（`Cache/sources/`），Pro 另加 10 个（`Cache/sources_pro/`）。

| 源 | 许可证 / 说明 |
|---|---|
| yhosts、ad-wars、1024_hosts、xinggsf、cjx-annoyance、adgk | 国内去广告 |
| AdAway、Mvps、YousList、StevenBlack、EasyList、EasyPrivacy、EasyList China | 国际主流（EasyList 系为 GPL-3.0 或 CC BY-SA 3.0） |
| anti-AD、antiadblock、i-dont-care-about-cookies | 综合 / 专项 |
| **Pro 专用**：Hblock、Spam404、halflife、AWAvenue、AdGuard Chinese、scamblocklist、NoCoin、Peter Lowe、Dan Pollock、neohosts | 反诈 / 恶意域名为主 |

> 附加源各自适用其仓库声明的许可，使用与再分发前请查阅对应仓库。

### 清洗规则明细

| 输入形态 | 处理 |
|---|---|
| `0.0.0.0 域名` / `127.0.0.1 域名` | 转为 `\|\|域名^` |
| 非本地 IP 的 hosts 重定向 | **排除**（翻墙 / 加速 / 解锁类） |
| `\|\|域名^`、`\|\|域名^$important` | 保留（剥离修饰符后取域名） |
| `@@\|\|域名^` | 进白名单 |
| `@@\|\|域名^$xxx`（带修饰符的白名单） | **丢弃**（场景限定豁免，DNS 层无法表达） |
| `\|\|域名^$domain=` / `$app=` | **丢弃**（站点限定型，转无条件会放大范围） |
| 带路径 `/`、正则 `/.../` | **丢弃**（DNS 层无法表达） |
| 元素隐藏 `##`、`#@#`、`#?#`、`#$#`、`#%#` | **丢弃**（非 DNS 层） |
| 裸域名 | 按拦截处理 |

> 上表仅适用于**上游源**与 `whitelist.txt` / `blocklist.txt`。
> `Lists/Append.txt` 不经过上述任何清洗步骤，内容原样追加到产物末尾。

### 优先级顺序

分两个层面，不要混淆。

**构建时（脚本处理顺序）**：

```
1. Lists/whitelist.txt        ← 最高
2. Lists/blocklist.txt
3. 上游源（3 主源 + 18/28 附加源）
4. Lists/Append.txt           ← 不参与优先级判定，原样追加
```

`Full/merge_dedup.py` 的实际步骤：

| 步骤 | 操作 |
|---|---|
| 1 | 读 `whitelist.txt` 与 `blocklist.txt` |
| 2 | 两者冲突 → 白名单胜，blocklist 剔除该条 |
| 3 | 读上游源，并入黑名单 / 白名单集合 |
| 4 | 手写 blocklist 并入黑名单 |
| 5 | 手写白名单 → `@@\|\|d^$important` |
| 6 | 从上游黑名单**删除**与白名单冲突的条目（含子域） |
| 7 | Append **原样追加**，不做任何判定 |

**运行时（AGH 生效顺序）**：

产物物理排列为「拦截规则 → 白名单规则 → Append 段」，但 AGH **不看物理顺序**，只看修饰符：

```
1. $important 例外      @@||d^$important     ← whitelist.txt 输出 + Append 里的 @@ 行
2. $important 拦截      ||d^$important       ← Append 里的拦截规则
3. 普通例外            @@||d^              ← 上游自带的普通白名单
4. 普通拦截            ||d^                ← 上游主源规则
```

**Append 的真实地位**：不参与构建优先级，但参与运行时优先级——其优先级由**自己写的修饰符**决定。

| Append 里的形态 | 运行时档位 |
|---|---|
| `@@\|\|d^$important` | 第 1 档（最高） |
| `\|\|d^$important` | 第 2 档 |
| `@@\|\|d^` | 第 3 档 |
| `\|\|d^` | 第 4 档 |

### 冲突判定速查

| 场景 | 结果 | 机制 |
|---|---|---|
| `whitelist` 有 `d`，上游有 `\|\|d^` | 放行 | 构建时删除上游规则 + 输出 `@@\|\|d^$important` |
| `whitelist` 有 `d`，Append 有 `\|\|d^$important` | 放行 | 不删除，靠 `$important` 例外 > `$important` 拦截 |
| `whitelist` 有 `d`，Append 有 `\|\|d^` | 放行 | Append 不参与删除，靠 `@@$important` 压过普通拦截 |
| `blocklist` 有 `d`，上游白名单有 `@@\|\|d^` | 放行 | 手写 blocklist 剔除（兜底） |
| `whitelist` 与 `blocklist` 都有 `d` | 放行 | 白名单胜，打印警告 |
| Append 内 `@@\|\|d^$important` 与 `\|\|d^$important` 并存 | 放行 | 第 1 档 > 第 2 档 |

### Lite / Slim 的白名单来源

两者**不直接读 `whitelist.txt`**，而是从 **Full 产物**继承：

```python
allow_set = set(load_full_allows())   # 读 Full 产物的 @@ 行
stage2 = {d for d in stage1 if d not in allow_set}
```

| | Full / Pro | Lite / Slim |
|---|---|---|
| 白名单来源 | 直接读 `Lists/whitelist.txt` | 从 **Full 产物** 继承 |
| blocklist | 构建时并入 | 构建时并入（白名单冲突则剔除） |
| Append | 原样追加 | 原样追加 |
| 白名单输出形态 | `@@\|\|d^$important` | 同 |

> Lite / Slim 在 Full 之后运行。若 Full 构建失败或产物缺失，它们的白名单会是空集（脚本有告警）。

---

## 二、许可说明

### 代码与产物适用不同许可

| 范围 | 内容 | 许可证 |
|---|---|---|
| 代码与文档 | Python 脚本、Actions 工作流、Markdown | **MIT** — [LICENSE](../LICENSE) |
| 规则产物 | `out/` 下四份 `.txt` | **GPL-3.0** — [LICENSE-GPL-3.0](../LICENSE-GPL-3.0) |

### 产物为何是 GPL-3.0

`out/` 是多个上游黑名单的汇编，版权状态继承自输入源。按 [GNU GPL FAQ](https://www.gnu.org/licenses/gpl-faq.en.html#GPLOutput)：

> when a program translates its input into some other form, the copyright status of the output inherits that of the input it was generated from.

本项目上游中，EasyList 系（GPL-3.0 或 CC BY-SA 3.0 双许可）、URLHaus、217heidai/adblockfilters、AdguardFilters、AWAvenue、AdAway **均为 GPL-3.0**，故产物整体按 GPL-3.0 分发。

### 关于 Lists/Append.txt

该文件的规则提取自 [liuzq2002/Adguard-Home-For-Magisk-Mod](https://github.com/liuzq2002/Adguard-Home-For-Magisk-Mod) 的 release（**MIT**，其规则基础 GOODBYEADS 亦为 MIT）。

MIT 与 GPL-3.0 兼容，这部分内容可合法地并入 GPL-3.0 产物；但**单独取用 `Append.txt` 时，适用其原始 MIT 许可**。

### 代码为何是 MIT

脚本只做下载、清洗、去重、合并，不含任何上游规则内容。GNU FAQ 亦指出自由软件许可「cannot limit what data you use the interpreter on」——代码许可与它处理的数据无关。

### 你的义务

| 使用方式 | 要求 |
|---|---|
| 仅订阅使用 | 无需任何操作 |
| 再分发 `out/` 列表 | 遵守 GPL-3.0，注明来源与本项目 |
| 单独复用 `Lists/Append.txt` | 遵守 MIT，注明来源 liuzq2002 与 GOODBYEADS |
| 复用 / 修改脚本 | 遵守 MIT，保留版权声明 |
