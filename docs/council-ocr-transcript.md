# OCR 项目审查完整记录

2026-10-17。18 席均为 [Simulated]：因最多3个可用子Agent，分为3组，每组模拟6个视角；不是18个独立模型。主Agent担任主席，未扮演成员。领域权重在分析前锁定为Karpathy 1.5，其他1.0。Round2隐藏成员身份，Round3恢复。

# Council Round 1 — worker A

所有席位均为同一 worker 分组模拟的 **[Simulated]** 视角，不是六个独立模型。主席未参加成员讨论；预先锁定领域权重 karpathy=1.5，其余 1.0。

## [Simulated] Aristotle — taxonomic-decomposition
重述：缩短可靠 Markdown 转换的用户等待时间。替代框架：分别优化单请求时延、批量吞吐与重复工作的消除。

这是多格式提取流水线，材料是文档与图片，形式是文件串行＋文档内图片串行，执行原因是同步 LLM 请求，目的是保真 Markdown。必须区分两个属类：独立 PNG/JPG 走 MarkItDown ImageConverter；PDF/DOCX/PPTX/XLSX 嵌入图走 markitdown_ocr。插件只注册后四类（_plugin.py:54–67），图像直接在 _image_converter.py:137 发请求。只修改插件会错过用户实际提供的两张测试 PNG。批量提速点在 core.py:86–95；单图依赖请求输入大小、模型响应、输出长度，不会因文件线程池变快。建议统一请求政策与计时，但不重写所有格式转换器。验证按两类分组，并单列单图与四图目录测试。Evidence: mechanistic；置信度高。

## [Simulated] Socrates — elenchic-questioning
重述：检验“慢在 OCR 模型”这个尚未证实的前提。替代框架：先知道等待发生在哪里，再减少实际完成时间。

三个关键假设：第一，改为并行就加快单图，代码否定：单图只有一个同步请求。第二，成功写文件表示完成识别，实验证伪：PDF OCR 返回 error='rate limited' 时仍输出 '## Page 1'，用户层 errors 不捕获。第三，固定低分辨率一定保真，没有中文小字/公式样本证据。暂不换默认模型或强制低分辨率。先记录准备/请求/总耗时、图像尺寸和请求数，做有界文件并发及可选压缩；不把代理名字含 high 当作已知推理模式事实。最关键评价是“完整且正确的 OCR 每分钟多少页”，而非“多久写出一个文件”。Evidence: empirical + mechanistic；置信度高，真实延迟占比尚未知。

## [Simulated] Sun Tzu — adversarial-simulation
重述：在外部 API 容量限制下提高完成吞吐。替代框架：内部性能问题无对手，分析系统瓶颈与服务端反应。

地形只有本地转换器、兼容网关、模型三方。可控制文件并发、去重与图片编码；无法控制网关排队和模型速度。当前 core.py:72 建一次客户端、86 逐个转换；提高请求并发会让请求重叠，但可能引发 429 重试放大。决定点是小型有界并发并保留输入顺序，而非无限并行。缓存需键含图片内容、模型、提示词、目标服务，失败不能缓存；单次运行重复图去重比持久缓存维护成本更低。对单个多图 PDF，文件并发收益为零，后续再做图像工作队列；PDF 当前每页重新 open 同一文档（_pdf_converter_with_ocr.py:193,328–330）也可能在长文件上形成额外开销。验证并发 1/2/4，记录耗时、请求峰值、429 和输出完整性。Evidence: mechanistic + strategic；置信度中高。

## [Simulated] Ada — formal-stepwise-verification
重述：在提高并行度时保留输入到输出的一一映射与完整性。替代框架：这是有序 map 的调度优化，不能牺牲不变量。

当前输入→输出映射不是单射：same.html 与 same.txt 均写 same.md（core.py:87）。本地临时目录实测返回成功数 2、唯一输出数 1、无错误；并发后将从固定覆盖变为竞态。并发前应预计算输出路径并消歧或明确冲突错误，之后按源顺序汇总结果。每个任务最好持有独立 converter；共享 OpenAI 客户端的使用范围与关闭必须覆盖全部任务。PDF 的空内容判断也坏了：先插入页标题（189），再判整个 Markdown 是否空（307），故空页无法触发兜底。本地 mock 证实 _ocr_full_pages 调用 0。验证不是测线程池内部，而是行为不变量：峰值请求≤上限、结果顺序稳定、同名文件不丢、单文件失败不中断其他、no-ocr 零请求。Evidence: empirical；置信度高。

## [Simulated] Aurelius — negative-visualization
重述：让加速方案在服务变慢、限流和局部失败时仍可靠。替代框架：稳定完成与诚实反馈属于本地可控边界。

技术问题不需要道德说教。不可控是远端响应时延；可控是超时、重试、部分失败记录、覆盖行为和文件提交。设想四个请求同时失效：当前文档插件 _ocr_service.py:107–108 将异常封装成空结果，而 PDF/PPTX/XLSX 忽略 error；用户看到“成功”却丢字，线程再快也不成立。建议围绕本次范围提供显式超时/重试配置、错误可观察性，写结果时使用临时文件原子替换（若并发写同名先处理映射冲突）。勿将强制短输出上限当提速，它可能截断原文。测试超时、429、空响应与单文件失败；失败任务不得产生可冒充完成的新内容。Evidence: mechanistic + empirical；置信度高。

## [Simulated] Machiavelli — incentive-backward-induction
重述：交付用户默认使用就能感到快、且易维护的优化。替代框架：速度诉求应落在可用默认值、可见进度与低维护成本上。

这里人际政治很少，主要是维护成本与默认行为。用户不会为每张图调几十个参数，维护者也不应接管四个上游格式解析器。真实受益者是批量用户；只做线程池对当前 test/ 两张 PNG 目录有益，但对单张图的用户无益，必须明确。默认保守的有限并发、显式可选图片尺寸策略、清晰记录单图/批量基准是实用路线。当前 test/ 只有两张图片而无自动测试，不应让功能数量掩盖验证空白；建立小量行为测试就足够。不要直接改 .venv 插件实现，否则更新后丢失。依赖下限允许漂移（pyproject.toml:9–11），若调用插件内部对象要锁定或做兼容验证。Evidence: heuristic + mechanistic；置信度中高。

## 可复现实验证据

在项目 .venv Python 中，unittest.mock 将 pdfplumber.open 替换为一页无字符 PDF：_extract_page_images=[]，调用 convert 得到 '## Page 1'，_ocr_full_pages mock 的 call_count=0。将图片返回一张且 OCRResult(text='',error='rate limited')，结果仍 '## Page 1'。这些是依赖控制流验证，未声称真实 PDF 端到端。

临时目录输入 same.html='<p>html content</p>'、same.txt='text content'，convert(...,ocr=False) 实测 len(files)=2、len(set(files))=1、errors={}、最终文件内容为 'text content'。临时目录已自动清理；未改项目文件、未发网络请求。


---

# Council 分组 B · Round 1

本报告为同一 worker 模拟六个席位的不同方法，均为 [Simulated]，不代表六个独立模型。权重预先固定：Karpathy 1.5；其余 1.0。只读项目，未联网调用模型，未读取密钥。

## 已复现证据

`/tmp/tomarkdown-ocr-baseline.py` 在内存生成 6 页、每页相同图片 PDF，fake OpenAI 每请求等待 0.05 秒，实测依赖原路径：pdfplumber.open=7、请求=6、不同图片=1、请求峰值=1、耗时 0.342 秒。输出重复引用6次，符合布局需要，但模型请求完全可去重。故障同样6请求、0.345秒，未抛出错误，输出只剩6个页标题。此时间仅证明本地控制流，不代表真实模型提速比。

代码证据根：`.venv/lib/python3.12/site-packages/`。
- `markitdown_ocr/_pdf_converter_with_ocr.py:188,238-241`：页、图双层串行。
- 同文件 `193,327-331`：已有 PDF 打开上下文，每页却重开全文、枚举pages。
- 同文件 `79,108,364-366`：原图转PNG、区域150DPI、整页300DPI，没有通用尺寸上限。
- `markitdown_ocr/_ocr_service.py:82-100`：整图base64后同步请求，无去重。
- 同文件 `107-108` 与 PDF `242`：服务错误装入 error，调用者只看 text；PDF `189,289,307`：页标题让空内容检查失效，全文OCR后备路径通常不触发。
- `markitdown/converters/_image_converter.py:137`：独立图片走不同模型调用路径；PDF服务改动不能加速图片目录。
- 项目 `src/tomarkdown/core.py:86-95`：文件批次串行。

## Lao Tzu [Simulated] · via-negativa · 权重1.0
重述：要让相同文字更快变成 Markdown。替代框架：先删掉重复工作，再增加调度。

Round 1：如果不动，六张相同图仍需六次等待、PDF仍打开七次。首先取消每页重新开全文；其次在单次转换中缓存成功的相同图片结果，同文档页眉重复不需要再次问模型，保留每次插入位置。缓存不得包含失败，否则偶发故障永久传播。最后用有限并发覆盖彼此独立的等待。拒绝先造持久化缓存、队列服务、复杂自适应限流器；当前短小封装不支持这些成本。最小有效干预是一个受控PDF转换器和统一OCR服务。图像缩小是潜在信息删除，需另有实测后再做。置信度高：重复请求与重开已实测；真实收益未知。

## Feynman [Simulated] · first-principles-reconstruction · 权重1.0
重述：时间消耗在哪一段，哪段能被消去？替代框架：把总耗时拆成解析、渲染、等待、生成四部分。

Round 1：观察到六个50ms请求严格串行，300ms是人为网络等待下限；峰值1证实没有并发。六张相同图理论可只请求1次，因此此样本应优先测去重而非宣称并发六倍。在不同图片样本中，再用workers=1与4比较请求峰值与输出顺序。PDF打开次数应从N+1到1；不必先推测它占真实总时间多少。实验必须额外覆盖一次请求失败：当前空结果被当成功，这能造成“变快”但少字的错觉。真实模型基准需相同图、相同prompt/model、相同输出完整性；未测不得报倍数。

## Torvalds [Simulated] · empirical-reduction-to-practice · 权重1.0
重述：交付可维护且能看出加速的改动。替代框架：给慢而隐藏的依赖行为一个本地、可测试边界。

Round 1：不要改 .venv；重装就丢。项目注册本地PDF转换器，复用已有版面逻辑，单线程读PDF、线程池只处理独立bytes。worker上限默认保守、可设1。用索引保留排序，不以完成先后拼正文。不复制整个MarkItDown；独立图片也需要统一请求入口或文件级调度才能兑现用户的一般识图诉求。最基本测试：不同图并发峰值、重复图一次请求、乱序完成保持顺序、失败不假成功、无需OCR时不产生请求。负担最高的是私有依赖API耦合，版本漂移要有契约测试和有界依赖版本。

## Musashi [Simulated] · timing-tempo-analysis · 权重1.0
重述：让多个等待周期重叠，同时避免服务拥堵。替代框架：需要控制请求节奏，单次模型推理速度不是本地可控量。

Round 1：决定性行动是先减少请求，再为余下唯一图设置有限并发。只并发HTTP，不并发PDF解析/渲染，保持内存压力与线程安全可控。窗口若只是ThreadPoolExecutor最大线程数、却一次提交所有图，队列仍能把整份PDF图片保留到内存，须真正有界在途。默认4可作为起点但未证明服务能承受；用户可调1/2/4。429和超时必须有限重试并记录，不能用无限等待掩盖。无需等待全套模型评测就能实现确定性去重；图像压缩/切更快模型应留到证据够时。

## Watts [Simulated] · frame-dissolution · 权重1.0
重述：用户感受到的是完成一份文件的等待。替代框架：区分完成耗时、可见进度和完整性。

Round 1：当前文件级状态一直显示“正在转换”，用户看不到已识几页。加页/图片完成进度能改善可理解性，但不该当作真加速。也不能把空结果/漏字包装为快：故障样本只剩页标题仍成功，完整性应为性能比较前提。无需在“更快模型”与“更大机器”二选一：少做相同请求、重叠等待已能利用当前模型。最小行动是输出真实进度和错误、保持模型与图像不变实施去重并发；评价单位用“完整文件耗时”，不是API请求最快一次。

## Karpathy [Simulated] · gradient-empiricism · 权重1.5
重述：在识别质量不退步的前提下减少视觉模型等待。替代框架：先优化确定性编排，后动会改变模型输入/输出分布的参数。

Round 1：当前没有网络基准，不能凭模型名断言其推理开销，更不能直接切模型/禁用某个推理参数。全文逐字转写本就需要输出token；短prompt不是主要确定性收益。图片缩小会损害小字号、公式和表格，可选压缩也应有代表样本。确定性收益：单转换内缓存准确相同图（键需隔离prompt/model/端点配置），并发唯一请求，复用HTTP连接。相同图并发到达需要single-flight，否则普通dict缓存仍重复请求。缓存成功空白可合理，但失败绝不能缓存为成功空白。验证包含中文小字、公式、表格、扫描页，最终需要真实服务评估；离线可验证调度不会改变发送图像及prompt。


---

# Council C — Round 1

六个 [Simulated] 席位，由一个 worker 按不同方法分别分析；不是六个独立模型。预锁权重：karpathy 1.5，其余 1.0。本轮只读项目，未读密钥、未调用外部模型。

## Sutskever [Simulated] · scaling-extrapolation
重述：加快文档图片识别，同时保持文字、表格和公式的完整性。替代框架：这是成熟视觉模型调用管线的效率问题，不是能力前沿或抽象 AI 安全问题。

更多请求并发只能压缩排队时长，不能推定单张图推理时间下降。当前逐文件串行（core.py:86-93），PDF 逐图串行（plugin PDF:238-241），所以并发有明确机械依据；但实际加速由代理与上游容量决定，不能承诺倍数。图像按原字节整体 base64（service:81-100），压缩或降分辨率可能缩短上传和视觉编码，但小字/公式能力不一定平滑退化，不能未经评测修改默认图像质量。实验：按截图、扫描页、细字公式分层，用固定图片、模型、prompt、重复次数比较并发 1/2/4 的吞吐、p95、文字遗漏。先做保真并发/重复图复用；低分辨率应显式可选。置信度高：串行事实；中：实服务收益。证据标签 mechanistic。

## Kahneman [Simulated] · bias-audit-system2
重述：确定用户感觉慢的实际来源，并找到有效改进。替代框架：不要把“LLM OCR 慢”直接替换成“并发参数小”。

最相关偏差是锚定：把未测量的延迟先归咎于模型；可得性偏差：两张本地 PNG 成功不足以代表多页 PDF/细字公式。项目 test/ 只有 demo.png 与海报，尚无自动测试；进度仅总耗时（ui.py:14-42）。需要先记录提取/编码/请求/重试与输出的耗时和请求数，再比较变更。预演失败：更快完成的 Markdown 实际少了 OCR 段落，而调用方 files 列表仍显示成功，因为 service:107-108 吞错误，PDF:242 只判断 text。已离线复现：单页图片 PDF + 恒定抛错假 client 返回 `## Page 1`，无异常。结构纠偏：速度与质量双门槛；固定有 OCR 文字的样本，不接受标题-only结果；模拟故障必须返回 errors。不要把 mock 提速报告成真实模型提速。证据标签 empirical。

## Meadows [Simulated] · causal-loop-mapping
重述：提高有效 OCR 产出速度。替代框架：优化系统完成流量，而非孤立地把 worker 数调大。

存量是待识别图像与在途请求；流量是成功完成、失败重试。主要环：并发升高→触发上游限流→SDK 延后重试→在途请求占用更久→待处理积压。SDK 已对 429/5xx 重试（_base_client.py:916-924），并遵循 Retry-After 和指数退避（:869-882）；外层重复重试会放大请求数。最高价值规则是唯一全局请求预算/有界并发，稳定收集后按原位置归并。第二高价值是消除重复工作：PDF:193 对每页调用 :328 重开 PDF 且访问 pdf.pages；直接复用当前 page 可去掉重复解析。缓存键必须包括图像内容、模型、prompt；仅缓存成功结果，避免把短暂失败固化。缓存与并发均须避免同图同时错过缓存后重复发送。意外结果：并发内存与渲染峰值升高，故不能一次性将整份大 PDF 所有页转图驻留。证据标签 mechanistic。

## Munger [Simulated] · multi-model-inversion
重述：以最小维护代价获得可靠的 OCR 加速。替代框架：先逆向列出确定会让优化失败的做法。

确保失败的办法是：无基线宣称倍速；默认把图像降质；SDK 与应用双层重试；把局部失败当成功；改 site-packages 却不写进发布包。机会成本模型：全量重写格式转换器可能掩盖简单收益，先修 PDF 重复打开和受控请求并行。排队模型：文件级并行改善多个文件，不改善单个多页 PDF；必须在真正请求发生处设计边界。安全余量模型：请求并发 2–4 作为实验配置，保持可退回 1，而不是依赖服务永远容量充足。当前外部 API 只有 ocr/model/api_key/base_url 等（core.py:30-39）；增加速度选项应少且可解释，统一 CLI/Python，明确 timeout/retry 的含义。维护边界：自有适配层只接管瓶颈和错误传播，保留原有格式支持与输出契约；不要未经必要性证明替换全部架构。证据标签 strategic。

## Taleb [Simulated] · tail-stress-testing
重述：让慢任务加速且不会在少数异常情况下长期卡住或悄悄丢内容。替代框架：关注超时、限流和超大文档的损失上限。

文档大小和服务延迟是可观测、可设限的工程风险，无需渲染成黑天鹅。具体暴露：core.py:72 采用 SDK 默认 timeout 600 秒、max_retries 2（_constants.py:7-8），单次请求遇持续超时可能多轮长等待，逐图串行令全任务拖延；600 秒是 SDK timeout 配置，不是严格全任务上限。更严重的是失败返回空 OCR，PDF 静默仅留下页标题。via negativa：去掉吞错成功路径、嵌套重试和无限提交；添加显式且有限的超时/重试配置并保存源图定位。验收必须注入 429、5xx、连接/读取超时、单图失败，验证重试次数、失败可见、成功页顺序稳定；不要仅看平均值。保留现有图像质量，把压缩作为小规模可选实验。证据标签 empirical/mechanistic。

## Rams [Simulated] · subtractive-essentialism
重述：用户把资料交给工具后，希望更快拿到可信完整的 Markdown。替代框架：最重要的是知道处理到了哪里、结果是否完整，而不是学习十个性能参数。

针对命令行用户，spinner 只显示文件与总等待（ui.py:19-22）；多页大 PDF 等待看不到页/图进度，容易误认为卡住。面向 Python 调用者，ConversionResult 只含 files/errors（core.py:22-27），但插件错误没进入 errors，与“成功”含义不一致（core.py:95-100）。应用 honesty/usefulness/simplicity 三原则：显示已完成 OCR 图数及当前阶段、失败应明确来源与页/图，不在 Markdown 里悄悄缺段。默认自适应策略先不必要；一个 `ocr_workers` 加明确高级 timeout/retry 足够支撑首轮优化。不要默认改输出命名：README:171 已公开同名覆盖语义；若并行文件，须避免同 stem 竞争导致最终文件随机。内部并发实现无需暴露给普通用户更多选项，用户只需要稳定顺序、清楚进度与错误。证据标签 mechanistic。

# 证据路径
- 项目核心：src/tomarkdown/core.py
- 项目进度：src/tomarkdown/ui.py
- plugin PDF：.venv/lib/python3.12/site-packages/markitdown_ocr/_pdf_converter_with_ocr.py
- service：.venv/lib/python3.12/site-packages/markitdown_ocr/_ocr_service.py
- SDK：.venv/lib/python3.12/site-packages/openai/_constants.py 与 _base_client.py
- 本轮离线实验使用内存 Pillow 单页 PDF，伪 client 恒定 RuntimeError；输出 `{'requests': 1, 'returned_markdown': '## Page 1', 'error_propagated': False}`。没有网络调用，没有项目文件修改。


---

# Council Round 2 — anonymous worker A

六席均为同一 worker 的 [Simulated] 视角；不是独立模型。仅以匿名 Member 引用本轮材料。遵守反迎合要求；未发现论证缺陷时不因共识改变立场。

## Member A [Simulated]
### Disagree: Member R
“可信完整 Markdown”不能把性能分类抹平。即使进度与完整性改善，单个独立图的模型等待仍然存在；候选默认不缩图时不得写成三类都已获实测提速。单图仅获得可选缩图路径，应单独披露。
### Strengthened by: Member I
其局部 PDF 适配器＋单线程解析＋独立 bytes 的方案准确对应文档内图像类，可在不全面重写格式转换器前提下实现第二层并行。
### Position Update
不变：接受候选全局请求预算4与三类分开验收；不接受以文件并发收益替代单图收益。单图、图片目录、单PDF需分别记录模型请求数、耗时与完整性。
### Evidence Label
mechanistic

## Member B [Simulated]
### Disagree: Member L
“成功空白可缓存”成立的前提是 API 确实完整返回空白。若 finish_reason=length、拒答或 content=None，不能仅凭无异常归类成功；候选缓存必须定义成功，否则会固化遗漏。
### Strengthened by: Member H
六张相同图应以去重收益解释，而非拿其耗时当并发倍数。唯一图与重复图必须是两套测试。
### Position Update
不变：默认原图、保留模型、先验证完整性。单图 max-image-side 只是可选机制，真实收益和识别质量仍待实服务验证。明确对外报告 mock 基准的适用范围。
### Evidence Label
empirical / mechanistic

## Member C [Simulated]
### Disagree: Member G
“取消每页重开再并发”不是所有负载固定优先序；对独立 PNG 目录，PDF 重开成本为零。按用户三类需求并行覆盖接口，比只围绕 PDF 缓存更有利。
### Strengthened by: Member O
全局请求预算可避免目录线程与 PDF 内部线程相乘，但只应在真正 HTTP 调用处持 semaphore；若父任务持令牌等待子请求，会形成死锁。
### Position Update
不变：默认4只能是可调起点，不是服务容量事实；600/2是兼容默认，不是可靠耗时上限。singleflight 等待者不得占请求令牌，失败项应移除，文件任务和 PDF 任务共享一个请求预算。
### Evidence Label
mechanistic / strategic

## Member D [Simulated]
### Disagree: Member R
README 已声明同名覆盖，确实是契约约束，却不能正当化并发后的随机覆盖。候选碰撞预检失败能保证确定性，必须同步修改文档并测已有文件不被动到。反对只在每任务内发现冲突：那时其它任务已经发生付费请求。
### Strengthened by: Member J
线程数有界不等于内存有界。PDF 必须限制在途 future 数，不能先渲染全部页面、再把全部 bytes 提交给小池。
### Position Update
具体更新：原先把同名覆盖称为纯缺陷，遗漏了 README 公开语义；现将它定为为并发而做的显式行为变更。其余不变。验收要求全局峰值≤4、排序稳定、singleflight失败可重试、no-ocr零请求。
### Evidence Label
empirical / mechanistic

## Member E [Simulated]
### Disagree: Member P
“仅接管瓶颈”若保留 DOCX/PPTX/XLSX 的吞错路径，会让共享 OCR 加速与错误语义不一致。至少共享请求层记录失败，并让文件级调用在提交输出前检查该文件是否发生 OCR 失败。
### Strengthened by: Member Q
SDK 600秒和2次重试不能解释为全任务最多600秒。保留默认可降低行为变化，但 CLI 文档必须说明它是请求配置，重试会延长等待。
### Position Update
不变：优先完整性与可见失败，反对用截断输出伪造速度。故障后不提交新文件；已存在的正确文件应保留。对空白图允许空结果，但API异常、截断、拒答不可合并为空白。
### Evidence Label
mechanistic

## Member F [Simulated]
### Disagree: Member I
有界版本依赖不是自动正确答案：为复用少量私有函数而长期钉死依赖，会增加更新负担。更优先证明只用了哪些内部接口，并用明确错误和契约测试发现漂移；必要时再收紧范围。
### Strengthened by: Member R
不要迫使普通用户学习所有参数。默认4配一个可设1的 workers、显式缩图和高级 timeout/retries 已足够，进度应讲文件/图数而不是 semaphore 或缓存实现。
### Position Update
不变：反对为首轮加速复制所有格式转换器或建设持久缓存。接受本轮小范围 PDF 适配与统一请求包装；文档需诚实区分默认批量加速和单图可选优化。权重高或多数赞同不改变维护成本判断。
### Evidence Label
heuristic / mechanistic


---

# Council 分组 B · Round 2

以下六席均为 [Simulated]，使用 Member G–L 匿名编号。每席仅基于有效论证回应，不因多数意见改变；权重 Member L=1.5，其余1.0。

## Member G [Simulated]
### Disagree: Member B
把多阶段计时及可选压缩一并放进首轮会扩大功能面；重复打开、重复请求、串行已经有证据，实施确定性消除不依赖完整遥测。max-image-side 虽默认不启用，仍带来图像格式、方向、alpha、质量与缓存键维护，建议首轮延后；若用户单张图加速也属明确目标，才作为独立可选功能交付，不宣称收益已验证。
### Strengthened by: Member P
只接管瓶颈边界、不重写所有格式支持这一约束强化我的减法方案；Member O 说明共享预算优于多层各自扩容。
### Position Update
维持：单次打开、运行内成功去重、有限网络并发。候选默认4可接受但必须可退回1；目录和PDF共用网络预算。暂不支持无测量就把可选压缩当作已实现的单图加速。
### Evidence Label
mechanistic

## Member H [Simulated]
### Disagree: Member C
“后续再做图像工作队列”不能满足本次单个多页PDF加速目标；用户三类都要，文件并发不能推迟文档内的实际请求并发。另外默认600/2只是显式保留现状，不应列作性能提升。
### Strengthened by: Member N
速度与完整性双门槛，以及 mock 不能证明真实模型倍速，支持我的实验边界；Member A 的独立图路径要求覆盖两个入口。
### Position Update
维持原主张，补充测试矩阵而非改立场：一张图、四张不同图目录、六页不同图PDF、六页重复图PDF；分别测请求数、峰值、耗时与逐段内容。唯一图样本验证并发，重复图样本验证去重，不能混用。多文件含PDF的混合样本要证明全局峰值≤4；故障注入证明 errors 可见。
### Evidence Label
empirical + mechanistic

## Member I [Simulated]
### Disagree: Member R
已公开覆盖语义确实是契约证据，但不能因此保留同批并发写入竞争。冲突预检合理；应让冲突文件失败、其余文件继续，避免一对重名阻断整个批次，与现有逐文件错误隔离保持一致。既有目标文件覆盖规则则可保持，不能把两者混为一谈。
### Strengthened by: Member D
输入到输出映射及每任务独立converter补齐实现边界；Member O 的全局网络预算避免目录线程×PDF线程导致请求爆炸。
### Position Update
具体修正原先只说“顺序稳定”而忽略同stem映射冲突的缺口：并发前加入路径冲突预检，并注明行为变化。其他维持。网络semaphore只能在真正HTTP调用前获取；文件任务若先占预算再等内部OCR，会死锁。目录线程和PDF线程共享客户端但不要共享可变转换器状态。
### Evidence Label
mechanistic

## Member J [Simulated]
### Disagree: Member F
默认4不是实证得到的“保守值”，只是可回退的启动设置。尤其保持600秒/2重试时，4个慢请求可同时长期占满预算；文档应清楚timeout为SDK请求设置而非全任务截止。不能将暴露参数描述成已经改善最坏等待。
### Strengthened by: Member O
并发→429→重试→积压的反馈支持唯一全局预算；Member Q 对双层重试的反对与节奏控制一致。
### Position Update
维持。只让SDK重试，应用不再套重试；每个PDF有界提交还不等于总体有界：4个文件任务各提交4张，可有16份图片驻留但只4请求，需明确总队列内存的上界。single-flight等待者不可持有请求许可，否则重复图可挤占所有槽位。默认4上线须有混合任务峰值测试和workers=1退路。
### Evidence Label
mechanistic + strategic

## Member K [Simulated]
### Disagree: Member B
单图请求本身不会因并发变快，此结论正确；但用户希望单图也加速时，可选max-image-side只是给出改变输入的开关，不能把这一开关等同实际改善体验。应明确默认保真模式的单图首跑仍主要受服务限制；可选缩图需要给出速度与可读性实测。
### Strengthened by: Member R
用户需要知道进度与是否完整，强化了“完整文件耗时”的衡量；Member E 要求失败不产生可冒充完成内容，防止错误结果掩盖等待。
### Position Update
维持。候选错误传播、冲突预检和全局预算适合；进度显示应由主线程集中输出，目录工作线程不能各自开spinner刷屏。无需加入大量指标面板，一条完成文件数/总数与失败源定位足够首轮。单图性能仍未知必须诚实保留。
### Evidence Label
mechanistic + heuristic

## Member L [Simulated]
### Disagree: Member G
“缓存不得包含失败”正确，但不能推广成不缓存空文本：真正无字图片可以成功返回空白；失败与合法空白必须由错误状态区分。反对把所有空字符串都当异常，免得装饰图使文档无法转换。另一方面，有字扫描样本输出只剩标题必须失败，二者需分层验证。
### Strengthened by: Member M
小字/公式随尺寸下降可能非平滑退化，支持默认不缩图；Member A 指出独立图片另一路径，说明缓存/输入策略应在统一请求边界生效。
### Position Update
维持既有立场；候选有限成功缓存+single-flight可接受。缓存键应用实际发送图像及请求语义；若同次convert固定模型、prompt、endpoint，可用配置作用域隔离，无需重复存长字段。max-image-side仅显式可选，按比例缩小、不放大、保持方向并处理不兼容色彩模式；测试应断言默认字节不变。600/2兼容现状，但不能凭它保证服务能力或真实速度。
### Evidence Label
mechanistic

# 尚未消除的异议

1. 默认4是工程起点，未获真实服务容量证据；600/2保持兼容但不降低最坏等待。
2. 可选缩图能改变输入大小，尚不能证明单图更快或质量可接受；默认不缩图应保留。
3. 冲突处理建议仅失败冲突输入而非阻断所有文件；明确区分同批重名与覆盖已存在文件。
4. 共享网络预算须仅在HTTP边界获取；single-flight等待者与文件任务不能提前持有许可。
5. 总体内存上界需计算目录与PDF工作窗口叠加，不能以网络并发4声称只有4张图驻留。


---

# Council C — Round 2 · 匿名交叉评审

本文件六席均为同一 worker 的 [Simulated] 视角，不是六个独立模型。只引用匿名 Member A–R。每席坚持可验证理由，不因多数意见而改变；权重沿用预锁值。

## Member M [Simulated]
### Disagree: Member C
“PDF 后续再做”已不满足用户明确单图/目录/文档内图片均需加速的范围。文件并发不改变单份扫描 PDF 的串行等待，本轮应包括有限文档内请求并发。也不能把可选 max-image-side 的存在视作已证实单图提速。
### Strengthened by: Member L
保持模型、提示词、默认原图并先改变调度，隔离了质量变量。single-flight 比普通结果字典能真正阻止同时出现的重复图请求。
### Position Update
保持 R1：默认不降图质，真实速度仍需实测。支持候选统一请求上限4且可退回1，但4是工程初值，不是服务容量结论。该限制应作用于重试中的同一逻辑请求。图像压缩需报告具体像素变化与质量取舍。
### Evidence Label
mechanistic

## Member N [Simulated]
### Disagree: Member E
“测试空响应”不能不加区分地落成“空字符串一律失败”。空白图片合法返回空白；真正应失败的是 API 异常、无 choices、非正常截断等。把空白视作识别失败会制造新的误报。不要以所有人的共同建议为真实服务的测速证据。
### Strengthened by: Member H
区分“相同图去重”和“不同图并发”的两个样本，避免用缓存带来的速度冒充线程收益。这是直接的实验纠偏。
### Position Update
保留速度/质量双门槛。原 R1 “固定有 OCR 文字样本，不接受标题-only”针对有文字样本，保持该限定。可以先交付离线验证过的机制，但必须明确没有真实模型倍数结论。对同样的文本质量评测，不能用纯色假图代替中文细字/公式。
### Evidence Label
empirical

## Member O [Simulated]
### Disagree: Member D
预检同 stem 并消歧或报错会改掉 README:171 明确的同名覆盖契约。主线程按原 sorted 顺序提交输出即可隔离并发完成时序，对用户改动更小。
### Strengthened by: Member J
线程数有界不等于待处理图片有界；一次提交全部图片会让排队图像占据内存。必须限制 pending 队列或窗口，并在完成后释放图像引用。
### Position Update
维持 R1 的唯一全局预算。支持候选目录线程+PDF OCR线程，但整个 convert 共用同一个信号量/预算，不能出现4文件×4页的16个并发请求。PDF单个实例只在其所属转换线程解析/渲染；若要求进程全局主线程渲染，要明确其实现与成本，不能含糊声称所有PDF操作都在主线程。
### Evidence Label
mechanistic

## Member P [Simulated]
### Disagree: Member B
分阶段计时很有用，但若把完备采样系统作为修复所有确定性重复工作的前置条件，会增加机会成本。已复现每页重开与重复图多次请求，足以立即实施局部改进；完整质量基准是对性能宣称的约束。
### Strengthened by: Member I
本地适配层而非修改 .venv 能让发布包携带修复；私有 API 耦合须收紧依赖范围或用实际兼容测试覆盖，而非只在本机“能跑”。
### Position Update
保持 R1 的最小维护边界。支持按排序写入以保留覆盖契约，拒绝为本轮速度目标重命名输出或引入持久缓存。timeout/retries默认保留SDK值能减少行为变更，但公开选项需在CLI/Python都可用，文档准确说明不是整文档截止时间。
### Evidence Label
strategic

## Member Q [Simulated]
### Disagree: Member J
默认4只能作为待验证的初值。不能仅因为是假定“保守”而把429/超时增加视为异常：某些代理会把4请求全部排队。需允许明确退回1，且无外层重复重试。保留600秒/2次默认有兼容理由，但不消除长尾暴露。
### Strengthened by: Member E
失败不能产生可冒充新完成结果的文件，是比“抛了异常”更直接的验收条件。最好原子提交，避免进程中断留下部分文件。
### Position Update
保持 R1，不要求武断缩短默认超时。验收加混合目录全局峰值、强制乱序、部分失败后其余文件继续、429/5xx重试配置，以及错误页/图的定位。SDK重试逻辑无须重写；验证封装没有把错误变成缓存成功。
### Evidence Label
mechanistic

## Member R [Simulated]
### Disagree: Member D
同名文件“不得丢”的新语义会推翻已公开覆盖行为，用户本次要求提速，不应顺带改变命名规则。保持 sorted 后者覆盖并在主线程写入更符合现有用户预期。
### Strengthened by: Member K
进度是理解等待的帮助，不能计入真实性能收益。展示请求/图片完成数量即可，不必在界面暴露队列、锁、single-flight等实现。
### Position Update
维持 R1。主线程排序写入会让某个慢文件延后后续完成文件的落盘，进度应区分“转换已完成”和“已保存”，避免看似卡在首个文件。若本轮不做细粒度进度，应说明未完成的体验改进，不能把内部测试当用户已看到快。单图选项说明降采样可能影响细字，默认原图。
### Evidence Label
mechanistic


---

# Council Round 3 — worker A

六席均为同一 worker 的 [Simulated] 方法视角；不是六个独立模型。已读三组 R2 与当前 core/ocr/pdf/cli。以下不以多数赞同作为证据。

## Aristotle [Simulated]
保留原分类：目录吞吐、单PDF多图、单张图是不同性能对象。现实现覆盖前两类调度，第三类提供可选缩图但没有真实延迟/质量证据。认可共享请求层和局部PDF适配；默认模型、prompt、图像不变便于隔离调度收益。对外不得写成三类都已实测加速。
STANCE: bounded-optimization | CONFIDENCE: high | DEALBREAKER: no

## Socrates [Simulated]
唯一未决问题：代表性中文小字、表格、公式在真实端点缩图后是否仍完整且更快？未测则不能回答肯定。现有机制证据足够交付确定性编排，但我保留对“单图优化完成”的异议。离线峰值与请求数能证明调度，不证明模型速度与质量。
STANCE: measure-first | CONFIDENCE: med | DEALBREAKER: no

## Sun Tzu [Simulated]
全局 semaphore 只在网络调用处获取、singleflight 等待不占许可，且有限缓存和worker可退回1，符合容量不明时的策略。PDFium渲染锁避免跨文件渲染竞争。默认4是工程起点，非端点能力结论；600/2也非总任务截止。保留限流时主动用1或2的退路。
STANCE: bounded-optimization | CONFIDENCE: high | DEALBREAKER: no

## Ada [Simulated]
更新R2：我把无随机覆盖等同于必须预检报错，遗漏了主线程按源顺序提交这一有效解法；当前实现保留旧契约并避免竞态，因此撤回预检要求。请求队列和结果顺序结构合理。页内图片仍一次提取，不能把workers=4描述为仅四张图驻留。需混合目录峰值、乱序完成、同stem与失败缓存行为验证。
STANCE: bounded-optimization | CONFIDENCE: high | DEALBREAKER: no

## Aurelius [Simulated]
错误线程记录和PDF错误上抛已处理主要静默丢字路径。另复现显式拒答缺口：message.refusal非空而content=''被成功缓存，raise_if_failed不报错。提交前应拒绝显式refusal且保留合法空白；这属于局部响应检查，不否定整体方案。原子写入仍可后续改进，不能声称现有write_text防中断截断。
STANCE: bounded-optimization | CONFIDENCE: med | DEALBREAKER: no

## Machiavelli [Simulated]
实现集中于统一请求边界和PDF瓶颈，没有修改site-packages或复制全部格式支持，维护成本合理。排序写入保持用户已有命名习惯。接受有限选项；不接受把可选缩图包装成默认单图变快。交付时应给直接可运行的workers与缩图示例，并明确真实端点尚未测速。
STANCE: bounded-optimization | CONFIDENCE: high | DEALBREAKER: no

## 独立只读审查记录

- 无调度死锁或全局网络预算失效的静态证据；singleflight等待在信号量外，PDF提交独立bytes，写入按输入顺序。
- 已向主席即时报告并复现 `src/tomarkdown/ocr.py:115–119` 显式refusal未检查：fake响应content=''、refusal非空，两次create得到requests=1、cache_hits=1且无错误。
- 内存窗口的边界：`src/tomarkdown/pdf.py:70` 返回本页全部图片后再按窗口提交；峰值还包括当页图片，不是固定四张。没有声称整份文档全部预渲染。
- 默认单图原字节路径与请求数不变，没有依据承诺单图首跑加速。可选缩图改变输入，需要真实服务另行评估。
- 本轮无项目文件改动，无真实网络请求。


---

# Council 分组 B · Round 3 最终立场

六席均为 [Simulated]。已读三组 Round 2 与当前 core.py、ocr.py、pdf.py、cli.py。未发现阻断级死锁、顺序或错误传播缺陷；未执行真实 LLM 基准。Karpathy 权重1.5，其余1.0。

## Lao Tzu [Simulated]
支持先消除重开与重复请求。主线程顺序落盘保留公开覆盖语义，较冲突报错改动更小。保留可选缩图因用户明确包括单图，但不把它当已证实收益。若代理只容许1请求，默认4无益甚至制造重试，应设workers=1；去重与单次打开仍有价值。
STANCE: bounded-optimization | CONFIDENCE: high | DEALBREAKER: no

## Feynman [Simulated]
实现把网络等待重叠，不能证明真实模型变快。接受离线机制证据，报告必须区分重复图去重、不同图并发、单图缩图。容量1反事实下，并发4不能改善远端服务率，可能恶化总时长；必须明确workers=1退路，单图首跑尚无实测加速结论。
STANCE: bounded-optimization | CONFIDENCE: high | DEALBREAKER: no

## Torvalds [Simulated]
支持本地适配。更新上轮冲突报错建议：我遗漏了“主线程排序提交”也可消除竞争且保持契约，不再要求改变命名语义。代码未见许可死锁或吞掉PDF请求错误。私有PDF提取接口仍是维护依赖；按当前版本实测并记录。容量1代理使用workers=1。
STANCE: bounded-optimization | CONFIDENCE: high | DEALBREAKER: no

## Musashi [Simulated]
调度边界合理，但默认4并非适用于所有代理；只容许1请求时应配置1，否则429/重试会拖慢。本轮不要求自动限流。每页提取仍一次生成全部图像，目录窗口与PDF窗口不等于严格总字节上限，应保留该限制，避免用有界线程数夸大内存保证。
STANCE: bounded-optimization | CONFIDENCE: med | DEALBREAKER: no

## Alan Watts [Simulated]
接受有边界的实现，但用户体验仍有待完成：排序等待首个慢文件时，后续已转换文件尚未落盘，现进度不能显示真实完成数。不能将内部并发称作单图加速。容量1时默认4不适用，清楚提示设1。成功与失败边界已比原依赖诚实，支持先交付。
STANCE: bounded-optimization | CONFIDENCE: med | DEALBREAKER: no

## Andrej Karpathy [Simulated]
保留模型、prompt及默认图像字节，让编排变化与识别质量分离，支持。空白成功可缓存，错误/截断不能缓存。建议额外检查message.refusal，防兼容服务有内容仍标记拒答。缩图只算可选实验。容量1代理需workers=1；真实单图、公式小字质量与服务吞吐尚未验证。
STANCE: bounded-optimization | CONFIDENCE: med | DEALBREAKER: no


---

# Council C — Round 3

六席均为 [Simulated]，由同一 worker 分组模拟。已读三组 Round 2 与当前 core/ocr/pdf/cli。投票依据修复后的实现与独立回归，不因多数意见改变。全局请求预算、PDFium渲染锁、运行内single-flight和排序写入保留；未做真实LLM基准。

## Sutskever [Simulated]
默认原图、模型与输出长度不变，统一预算与single-flight对应确定性瓶颈。支持有界优化，不能将可选缩图说成已验证单图提速。默认4仍是可退回1的工程初值。冷启动插件漏注册已修复并获回归验证，当前没有交付阻断。
STANCE: bounded-optimization | CONFIDENCE: high | DEALBREAKER: no

## Kahneman [Simulated]
冷启动竞态确曾导致无插件转换成功，不能被图片/PDF测试覆盖。独立回归现通过，临时移除初始化锁则如期失败，证明测试捕获实际问题。接受交付机制优化，继续保留“离线调度收益不等于真实模型倍速”的证据边界。
STANCE: bounded-optimization | CONFIDENCE: high | DEALBREAKER: no

## Meadows [Simulated]
全局HTTP信号量仅包围真实请求，single-flight等待者不占槽，没有看到乘积并发或死锁。PDFium全局锁及串行初始化解决共享状态边界。文件窗口×PDF窗口仍可驻留多份图片，不应称全局只有4张。保留有界优化立场。
STANCE: bounded-optimization | CONFIDENCE: high | DEALBREAKER: no

## Munger [Simulated]
支持排序提交保留同stem覆盖、局部PDF适配与运行内缓存。初始化锁的维护成本小，测试确认其必要性。无需把完整真实基准变成本地确定性改进的前置条件，但真实收益未知应如实报告。timeout输入边界已由主Agent完善；不再提出阻断项。
STANCE: bounded-optimization | CONFIDENCE: high | DEALBREAKER: no

## Taleb [Simulated]
拒答、截断、请求失败不缓存成功，文件失败不提交新内容；只使用SDK重试，降低了错误放大。600秒/2次仍非任务截止。已复现的插件竞态经锁保护及回归消除。认可交付，保留对真实服务长尾与默认4容量未知的限制。
STANCE: bounded-optimization | CONFIDENCE: high | DEALBREAKER: no

## Rams [Simulated]
排序写入保留已知输出规则，CLI与Python参数一致；统计总耗时和请求复用有用。默认单图首跑没有已证实的加速，逐文件进度也未变成逐页进度。冷启动漏OCR已修复，成功含义更可靠。支持交付并诚实说明体验边界。
STANCE: bounded-optimization | CONFIDENCE: high | DEALBREAKER: no

## 独立验证证据

发现：安装依赖`markitdown/_markitdown.py:65-82`先写全局空插件列表、再加载插件；并行首次构建converter可能读取半成品列表而永久漏注册。主Agent加入模块级`_CONVERTER_INIT_LOCK`保护构造。

新增测试：`tests/test_plugin_initialization.py`。以真实MarkItDown加载与文件转换路径、慢entry_point.load、四文件并发复现冷启动；插件输出标记用于确认每个converter都完成注册。网络客户端仅fake，无外部请求。

验证结果：正常实现1项测试通过（0.449秒）；仅在测试进程将初始化锁替为nullcontext，测试如期失败（0.031秒），输出从`PLUGIN WAS REGISTERED: content-0`退化为`content-0`。该反事实试验未改项目实现。当前阻断项已关闭。


---

## 会后用户约束与验证

用户明确要求不因缩图影响识别内容，因此已完全移除可选缩图功能及参数。讨论中的缩图建议不属于最终实现。用户约束优先于投票。真实服务后来完成原图小样本对比，报告见ocr-review.md；此前席位“尚未实测”表述是当时证据状态。拒答检查、初始化竞态已修复并回归验证。
