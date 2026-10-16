# OCR 性能审查与优化交付

日期：2026-10-17。范围：单份多页 PDF、文件夹批量文档/图片、单张图片。最终约束：不缩图、不截短输出、不切换模型，不以删减识别内容换速度。

## 结论与改动

本地可消除的主要耗时来自串行请求与重复工作。已在项目源码中实现全局有界请求并发、单次调用内去重、PDF 单次打开及错误传播，并补充回归测试。没有修改安装目录内的第三方代码。

| 项目 | 原行为 | 已交付行为 |
|---|---|---|
| 文件夹 | 按文件串行转换 | 默认4个文件任务，按原顺序写入 |
| 单份PDF | 每张图片串行等待模型 | 页内及跨页OCR可重叠；解析/渲染不进OCR线程 |
| 全局请求预算 | 无并发 | 所有文件和PDF共享上限，默认4、可设1–32 |
| PDF打开次数 | N页打开N+1次 | 整份文件打开1次 |
| 重复请求 | 同图重复调用 | 相同请求single-flight，最多缓存128个成功响应，只存内存 |
| 单张图片 | 原图发送 | 保持原字节，无缩图入口；首次请求无已证实的编排提速 |
| 识别异常 | 插件可吞错后记为成功 | 请求失败、截断、拒答记录文件失败，不写新的不完整结果 |
| 冷启动插件 | 新增并发会触发初始化竞态 | 构造转换器时串行初始化，避免漏加载插件 |

图片提取、公式、表格、复杂排版及模型内容完整性仍需与原文核对。这里保证的是不新增缩图、主动删减或输出截短策略，不能把错误检测等同于识别准确率100%。PDF图片沿用插件提取策略；提取不全时改用整页300 DPI后备识别。合法空白图片允许返回空文本。

## 性能证据

### 真实本地服务：原图小样本

使用程序生成的两张1800×1200英文测试图，包含数字及简单公式文本，调用已配置的默认模型`gemini-3.8-flash-high`。每组只跑一次，测试超时45秒、重试0；这不是完整文档准确率评测。

| 场景 | 串行/原图 | 并发/原图 | 结论 |
|---|---:|---:|---|
| 同样两张图片 | 12.693秒 | 6.587秒 | 本次约1.93倍，等待减少48.1% |
| 单张图片首次识别 | 4.733秒 | 未对单请求并发 | 无单图提速承诺 |

两张图在串行和并发运行中均成功返回，预设字段存在。模型输出具有随机性，未宣称真实输出逐字一致；样本数量不足以估算p50/p95或稳定收益。曾试验缩图，但用户要求完整性后已移除该功能，其结果不计入交付证据。

原始记录：[ocr-live-benchmark.json](ocr-live-benchmark.json)。服务限流、排队或只允许一个请求时，并发可能没有收益，应使用`--workers 1`。

### 离线确定性基准

实际转换器处理8张图片/8页PDF，假模型每请求固定等待100ms。以下数字验证本地调度，不能用于宣称真实模型倍速；逐项断言新旧输出完全一致。

| 场景 | 旧实现 | 新实现 | 请求数变化 | 峰值并发变化 |
|---|---:|---:|---:|---:|
| 8张不同图片的文件夹 | 0.871秒 | 0.239秒 | 8→8 | 1→4 |
| 8页不同图片PDF | 0.860秒 | 0.212秒 | 8→8 | 1→4 |
| 8页相同图片PDF | 0.864秒 | 0.113秒 | 8→1 | 1→1 |

原始记录：[ocr-offline-benchmark.json](ocr-offline-benchmark.json)。复现：`uv run python tests/benchmark_ocr.py`。计时有机器噪声，不将这些秒数设为测试阈值。

## /council --full 裁决

### Selected Panel

完整18席、3轮：Aristotle、Socrates、Sun Tzu、Ada、Aurelius、Machiavelli、Lao Tzu、Feynman、Torvalds、Musashi、Watts、Karpathy、Sutskever、Kahneman、Meadows、Munger、Taleb、Rams。

受3个子Agent并发槽位限制，分3组模拟18个成员，全部标记`[Simulated]`，不是18个独立模型。每席先做问题重述，再独立分析、匿名交叉质询、最终立场。领域权重在分析前指定Karpathy为1.5，其余为1.0。

### Chairman

主席为主Codex协调Agent（OpenAI，当前会话模型；运行接口未提供可验证的精确型号）。主Agent未担任讨论成员，负责核验源码、复现实验和综合裁决。仅有同一运行时提供商，无法实现跨提供商独立性；未虚构外部主席调用。

### Acceptable Compromises

接受默认4作为可调的工程起点，而非已测得最优容量；缓存只在一次转换期间有效；保留原同名文件顺序覆盖行为。接受单图首次识别暂不承诺提速，以保留输入信息。任务窗口有界，但整页图片会一次提取，所以不声称全局只驻留4张图片。保留SDK默认600秒/2次重试兼容性，不把它称为整个任务的时间上限。

### Kill Criteria

- 若在2026-10-17交付验收中，乱序返回导致正文或图文位置改变，裁决失效→修复归并并暂用`--workers 1`。
- 若在2026-10-17交付验收中，失败或明确截断仍产生新的“成功”输出，裁决失效→先修复完整性状态再交付。上述回归已通过。
- 若在2026-10-24之前的代表性同模型原图重复测试中，并发4的完成时间不低于串行，或限流/错误率上升，则“该服务默认4更快”的假设失效→该服务配置退回1或2。此项为验收建议，没有设置自动监控。

### Concrete Next Step

交付本地可运行优化补丁与回归测试集（已执行；未发布新版本）。

### Unresolved Questions

复杂中文小字、公式、表格、扫描文档的真实准确率与尾延迟尚无代表性评测。当前服务的最优并发值未知。单个DOCX/PPTX/XLSX内的图片仍依赖插件逐张调度；多文件并发和运行内去重已生效。超大单页多图片文档的峰值内存仍需专项测量。

### Key Agreements

优先减少重复工作与重叠网络等待；保持原图及完整提示词；使用统一全局请求预算；按原文顺序归并；失败不缓存、不作为成功；真实服务收益必须与离线基准分开。没有赞成通过截短正文提速。

### Key Disagreements / Minority Report

Socrates保留`measure-first`立场，要求充分测量单图速度和质量再宣称收益；这个限制保留到最终结论。部分成员曾建议同名文件直接失败，后因主线程按排序写入已解决竞争且保留公开契约而撤回。默认并发4不是无条件结论，容量1的服务需串行。用户后来明确不接受缩图造成信息损失，缩图功能已删除，优先级高于讨论建议。

### Vote Tally

最终结构化立场按预定权重及置信度计算：

- `bounded-optimization` — **16.375**：Aristotle、Sun Tzu、Ada、Aurelius、Machiavelli、Lao Tzu、Feynman、Torvalds、Musashi、Watts、Karpathy（领域基础权重1.5）、Sutskever、Kahneman、Meadows、Munger、Taleb、Rams。
- `measure-first` — **0.750**：Socrates。

基础权重总计18.5；共识门槛12.333；有界优化越过门槛。置信度因子high=1、med=0.75、low=0.5。插件竞态修复并通过可复现回归后，C组已解除DEALBREAKER。此为模拟视角的决策记录，不是独立专家投票统计。

### Decision Options

1. **已实施：原图+有界并发+去重。** 保持输入信息，减少批量等待；单请求首跑受服务速度限制。
2. **保守运行：相同实现配`--workers 1`。** 保留去重与单次解析收益，适合容量小或限流严格的服务。
3. **后续服务/模型评测。** 在代表性原图及明确完整性验收下比较服务配置，可能进一步改善单图速度；本轮不自动替换模型。

### Recommended Next Steps

1. 用用户真实中文/公式/表格样本执行重复原图对比，记录完整性、总耗时和限流率。
2. 如单个Office文档仍慢，再扩展其图片调度边界，保持插件内容位置正确。
3. 如大文件内存成为瓶颈，改成逐图提取并限制字节预算，而非只增加线程。

### Confidence

对串行、重复请求和重开PDF的根因判断为高；对实现顺序、去重、预算及错误状态的验证为高；对真实通用速度收益和全部内容准确率为中低。真实并发小样本已验证收益，单图首次识别无更快承诺。

### Execution Reliability

3个实际worker成功完成，18席均为分组模拟席位（live独立席位0、degraded/simulated18、offline0），无超时；未满足2个独立实时席位标准，因此整体按全模拟模式记录。没有冒称18次独立模型调用或跨提供商裁决。完整逐轮记录见[council-ocr-transcript.md](council-ocr-transcript.md)。

## 实现与验证范围

核心文件：`src/tomarkdown/core.py`（调度/顺序写入）、`ocr.py`（全局预算/缓存/错误）、`pdf.py`（PDF提取及有序归并）、`cli.py`（并发及超时参数）。依赖锁保留当前版本，限定插件0.1系列与pdfplumber0.11系列以控制私有提取接口漂移；回归验证真实插件边界。

回归覆盖：目录/PDF并发、混合输入全局上限、原图字节、去重及失败缓存清除、乱序完成保持全文一致、PDF打开一次、异常/截断/拒答和合法空白、同名输出行为、无OCR不调用模型、文本PDF、整页后备识别、Office吞错、插件初始化竞态。发布工作流新增测试步骤。最终16项回归全部通过；源码包和wheel构建成功，已从构建的wheel执行无OCR转换冒烟测试，内容保持一致且未打包本地密钥和结果。

第三方行为依据：[MarkItDown官方转换器实现](https://github.com/microsoft/markitdown/blob/main/packages/markitdown/src/markitdown/_markitdown.py)、[OpenAI Python SDK官方重试与超时说明](https://github.com/openai/openai-python#retries)。本次行为核验以当前环境实际安装源码和回归结果为准。

---
Session Metadata
schema_version: 1
mode: full
panel_size: 18
rounds_run: 3
enforcement_calls: 1
enforcement_breakdown: {agreement_check: 1, dissent_quota: 0, novelty_gate: 0, anti_recursion: 0, missing_stance: 0}
tools_used: [exec_command, spawn_agent, send_message, followup_task, web_search, request_user_input_async]
provider_count: 1
fallbacks_triggered: [three-worker-grouped-simulation, single-provider-chairman]
input_tokens_estimate: ~unknown
output_tokens_estimate: ~unknown
duration_seconds: ~unknown
---
