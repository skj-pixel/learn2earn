# Learn2Earn V3 算法、质量控制与 MemoryBear 技术白皮书

> 版本：V3.0.0。本文描述真实代码契约，不把候选设计写成已实现功能。涉及代码位置时以符号名为准，避免行号漂移。

## 1. 系统目标与执行边界

Learn2Earn 的输入是用户笔记、科目上下文、已安装 Skill、产品策略和可选历史记忆，输出是十四种知识付费产品之一或多个。系统不是单一提示词包装器，而是由输入规范化、策略选择、记忆检索、结构规划、内容生成、规则润色、质量检查、持久化和溯源组成的流水线。生成算法回答“如何产生初稿”，质量控制回答“如何检查或改进结果”，Skill 回答“采用哪些领域工作规范”，MemoryBear 回答“哪些用户历史应该进入本次上下文”。这四者职责不同，不能用一个名称掩盖另一个阶段。

V3 的核心约束是可追溯与不伪装。策略注册表中的 `implemented` 是事实字段：未实现算法不会出现在正常交互选择中；历史任务携带旧 ID 时可以兼容读取，但不能把回退链路宣传成完整实现。每个产品保存 `skill_names`、`algorithms`、`techniques`、MemoryBear 元数据和任务 ID，便于解释结果来源。

## 2. 总体流水线

后台任务从稳定任务记录读取笔记和科目，以用户 ID 约束全部查询。它合并任务级和产品级策略，加载启用的 Skill 私有指令，构造 MemoryBear 与 RAG 上下文，读取图片资产，然后逐产品调用生成器。生成完成后执行内容清洗和质量增强，最后将正文、产品类型、关键词、来源笔记、任务元数据和质量报告写入产品库。

任务在独立线程池运行，页面跳转不会取消任务。SQLite 使用显式数据库路径与有界连接池；MemoryBear 使用另一套按用户哈希隔离的 SQLite 文件，避免记忆库和业务库争抢同一个文件。失败任务保留错误类型和步骤，用户可以删除或重新生成。

## 3. 生成算法注册与选择

### 3.1 分层规划 `hierarchical_planning`

分层规划先建立产品骨架，再填充内容。它适合文章、课程大纲、SOP、PPT 等有明确层次的产物。第一阶段从笔记主题、目标产品和策略约束中抽取章节目标、顺序和覆盖点；第二阶段按规划生成正文。优势是降低长文中后段偏题概率，让标题层级、论证顺序和篇幅分配更稳定。代价是至少增加一次模型调用，规划质量也可能成为上限。

实现入口在 `AgenticProductGenerator` 的规划和生成方法。规划使用较低温度以保持结构稳定，正文阶段允许更高温度以增加表达丰富度。规划不是最终事实源，MemoryBear、源笔记和 Skill 约束仍然优先。失败处理应区分“规划无法解析”和“正文模型返回空内容”，不能把两种错误合并为无意义的生成失败。

适用场景包括长篇教程、课程模块、多个操作步骤和需要目录的材料。不适合极短标题、单句摘要等任务。验收关注章节覆盖、顺序合理、是否存在空章节、计划与正文是否一致。与 `single_pass` 同选属于执行模型冲突，因为前者要求先规划后生成，后者要求一次直出。

### 3.2 迭代精炼 `iterative_refinement`

迭代精炼将初稿再次交给模型或规则处理器，要求检查完整性、可读性、结构、术语一致性和用户目标，然后输出修订稿。它不是质量技术列表中的重复项，而是生成算法的一部分：它改变生成过程和模型调用次数。质量评分只评价结果，迭代精炼会产生新结果。

实现由生成器的精炼调用和 `ContentPolisher` 共同完成。模型精炼负责语义层面的修改，规则润色负责删除提示泄漏、整理 Markdown、合并异常空段和稳定格式。较低温度用于减少二次改写引入的新事实。必须保留源笔记约束，不能为了语言流畅覆盖用户事实。

适用于高价值文章、课程、销售材料和需要较强一致性的长内容。代价是延迟和 token 成本上升。空响应必须有限重试并保留原始初稿，不能把已有可用内容覆盖为空。它与 `single_pass` 冲突，因为一次直出明确禁止后续生成轮次。

### 3.3 分块生成 `chunked_generation`

分块生成的设计目标是把超长来源或超长目标切成可控片段，分别处理后再合并。V3 注册表保留这个历史 ID，但完整的并行分块生成仍未实装；当前真实能力主要是来源文本切块、重叠窗口和提示透传，最终仍进入标准规划生成链。文档必须将其标为兼容占位，不能声称已经获得并行吞吐收益。

完整实现应包含稳定切分边界、相邻片段重叠、片段级计划、全局术语表、并发限制、失败重试、顺序合并、重复消除和跨块一致性检查。V3 只有其中一部分基础能力。历史任务读取该 ID 时会给出降级信息，正常 UI 会过滤未实现项。

### 3.4 并行草拟 `parallel_drafting`

该算法设想让多个候选草稿并行生成，再由评审器选择或融合。它可提升创意覆盖，但会显著增加模型调用和选择偏差。V3 仅保留注册 ID，没有实现候选隔离、评分仲裁和融合，因此属于未实现算法。系统不应让普通用户误以为勾选后真的运行多草稿。

未来实现需要固定候选数量、随机种子或温度策略、评分维度、事实一致性门禁和成本上限。融合不能简单拼接，否则会产生重复和冲突。测试应验证并发失败时仍有最小成功候选，并验证评分器不会看到候选来源标签造成偏置。

### 3.5 单次直出 `single_pass`

单次直出追求最低延迟：一个提示、一次主要模型调用、一个结果。它适合短文本，但结构和事实稳定性弱于分层规划。V3 将其保留为历史兼容 ID，未作为正式实现开放。它与分层规划、迭代精炼冲突，冲突规则会在用户实际选中矛盾配对时显示具体名称和原因。

若未来实装，应明确跳过规划和模型精炼，只保留必要的安全清洗与持久化。质量检查是否运行应由独立质量策略决定，因为“单次生成”不等于“不做生成后检查”。

### 3.6 分块并行 `chunked_parallel`

分块并行结合长文切块和并发生成，理论上降低长内容墙钟时间。难点不是并发本身，而是全局一致性、API 限流、部分失败恢复和确定性合并。V3 未实装。未来需要任务级并发预算，不能与现有生成线程池无界叠加；还需要按产品保存每块状态，避免重试整篇造成成本翻倍。

### 3.7 反思式自修 `reflexion`

反思式自修要求模型显式识别失败模式、提出修改计划并重新生成。它不同于普通精炼：反思应有结构化问题清单和可验证修改。V3 未实装完整轨迹，只保留候选 ID。未来实现时不得把隐藏推理链原样保存或展示，应只保存简洁的问题类别、修改动作和验证结果，避免泄露模型内部推理或敏感内容。

## 4. 生成前上下文技术

### 4.1 源笔记约束 `source_grounding`

源笔记约束把当前笔记作为首要事实来源。它在生成前生效，不属于生成后质量矩阵。系统会截取或分块来源，构造清晰边界，并要求模型不虚构来源中不存在的事实。它可以与任何质量检查共同存在。若用户要求外部扩展，RAG 内容必须标为补充来源，不能静默覆盖原笔记。

### 4.2 MemoryBear `memorybear`

MemoryBear 提供用户历史偏好、相关旧笔记和已生成产品。它在提示构造阶段生效，不应拖慢不使用记忆的普通页面。V3 的具体实现见第六章。

### 4.3 RAG 外部检索 `rag_grounding`

RAG 面向外部或用户知识库检索，补充新事实；MemoryBear 面向用户长期历史和偏好。二者可以并存，但来源权威级别不同。V3 的真实 RAG 能力依赖可用检索后端；没有真实向量或网络检索时必须标注降级，不能声称拥有外部实时知识。

## 5. 质量控制手段

质量控制在概念上位于生成后阶段，因此兼容规则只比较质量手段之间，不与算法、Skill、MemoryBear 或 RAG 建立跨阶段冲突。

### 5.1 多维质量评分 `quality_scoring`

质量评分汇总完整性、可读性、专业度、可变现性等指标，生成结构化报告。评分用于解释和排序，不应单独决定事实正确。确定性规则适合检查标题、长度、空段和格式；语义评分依赖模型时必须记录模型和失败回退。分数需有明确范围，缺失指标不能默认为满分。

### 5.2 少样本示例 `few_shot`

少样本示例通过一到两个高质量样例稳定格式和风格。它在技术注册中归入质量能力，但作用发生在生成提示阶段。示例必须与产品类型匹配，不能把示例事实混入用户正文。过多示例会挤占上下文并导致模仿过度，因此应限制数量和长度。

### 5.3 反幻觉校验 `hallucination_check`

反幻觉校验比较输出主张与源笔记、允许的记忆和检索证据，标记无法支持的句子、数字和因果关系。它不能证明所有剩余内容为真，只能降低明显无依据陈述。校验结果应保留具体问题而非只有总分。自动修改时应优先删除或降格表达，不应凭空补证据。

### 5.4 SEO 优化 `seo_optimization`

SEO 优化关注标题、关键词、摘要、层级和可检索性，适合文章等公开内容。它不能改变产品事实和用户立场。对不面向搜索引擎的产品，例如内部行动清单，SEO 权重应降低。关键词堆砌、重复标题和机械模板属于失败输出。

### 5.5 温度调度 `temperature_scheduling`

温度调度在规划、正文和精炼阶段使用不同采样温度：规划偏确定，正文适度开放，精炼更保守。它提高过程稳定性，但实际可用性取决于模型供应商是否支持温度参数。供应商忽略参数时，系统不能伪报调度生效。

### 5.6 连贯性验证 `coherence_validation`

连贯性验证检查章节顺序、指代、术语、过渡和重复。长文应同时检查局部相邻段和全局目录。只按关键词重合会错过逻辑矛盾，因此结果应视为风险提示。自动修订必须保护代码块、表格、Mermaid 和图片锚点。

### 5.7 自动重组 `auto_restructuring`

自动重组修复超长段落、错误标题层级和碎片化短段。规则处理应尽量确定性，避免再次调用模型。它只能调整结构，不能重新解释事实。表格、代码块和引用是不可拆分边界，错误切分会破坏渲染。

### 5.8 受众角色注入 `audience_role_injection`

该能力计划根据受众知识水平、行业和目标调整表达。V3 注册为未实现，不在正常选择中展示。未来实现需区分用户明确配置和算法推断，推断结果不能作为敏感用户画像长期保存。

### 5.9 竞品差异化 `competitor_differentiation`

该能力计划读取合法竞品资料并提出差异化角度。V3 未实装。它需要真实来源、时间戳、引用和合规边界；没有检索证据时不能生成看似精确的竞品结论。它不再与源笔记约束定义为冲突，因为二者处于不同职责阶段，可以用源笔记确定自身事实、用外部资料辅助定位。

## 6. V3 MemoryBear 实现

### 6.1 为什么 V3 替换官方运行栈

V2 跟踪完整官方仓库，包含 API、Web、迁移、任务队列和大量基础设施，体积和部署复杂度高。V3 使用用户提供的轻量 Python 引擎，目标是在本地演示环境保留关键认知机制，同时避免要求 Redis、Celery、额外数据库和独立服务。V3 不声称复刻官方每个控制器和工作流，而是忠实翻译 Learn2Earn 实际消费的记忆语义。

### 6.2 轻量引擎的真实能力

引擎使用 Python 标准库和 SQLite，提供 `MemoryStore`、`ActivationManager`、工作记忆 LRU、短期与长期存储、知识图谱三元组、剪枝、反思、QUICK/DEEP 路由、召回上下文和统计。数据库启用 WAL；写入由锁保护；召回后提升激活度；访问次数和激活度达到条件时，短期记忆可晋升长期记忆。

V3 对原包增加两个关键参数：调用方可提供稳定 `memory_id`，并可指定 `working`、`short_term` 或 `long_term` 存储层。稳定 ID 让同一笔记反复生成时执行替换而非无限插入，解决持久化膨胀和重复召回。

### 6.3 官方五类语义映射

官方语义包括感知、工作、情景、显性和隐性记忆。轻量存储只有工作、短期和长期三个物理层，因此适配器使用标签保存语义：本次请求作为感知输入但不长期持久化；当前笔记进入工作记忆；历史笔记作为情景记忆进入短期层；已生成产品作为经过验证的显性记忆进入长期层；从产品类型和标签频次推导的偏好作为隐性记忆进入长期层。

物理层少于语义层并不意味着丢失语义，只要标签、来源和生命周期仍可区分。适配器在返回元数据中始终给出五类键，供任务溯源和测试验证。当前笔记会从历史召回结果排除，防止“自己召回自己”制造虚假长期记忆。

### 6.4 用户隔离

每个用户 ID 经 SHA-256 派生稳定文件名，数据库位于 `storage/memory-bear-v3`。路径不包含明文用户 ID，且不同用户永远不共享数据库文件。业务查询本身也按用户过滤。测试会创建两个用户并断言生成两个数据库，防止跨用户记忆泄漏。

### 6.5 幂等写入与来源追踪

记忆 ID 由类型和业务 ID生成，例如当前工作笔记、历史笔记、产品和派生偏好分别使用不同命名空间。即使业务 ID 相同，不同类型也不会碰撞。`source` 保存 `note:<id>`、`product:<id>` 等标识。重复调用更新同一条记录，不增加总数。测试连续构建上下文并断言统计稳定。

### 6.6 激活、遗忘和晋升

激活度按指数衰减，时间越长且未访问，值越低；重要性会减缓衰减。召回命中会提升激活度并增加访问次数。达到访问次数和激活阈值的短期项可晋升长期层。低激活项在数量超过阈值时可被剪枝。该机制用于控制记忆规模，不等同于删除业务笔记；MemoryBear 数据库是派生索引，业务数据仍在主库。

### 6.7 QUICK 与 DEEP 路由

QUICK 适合低延迟关键词召回，优先工作和短期层；DEEP 检索全部层并结合知识图谱关系。V3 产品生成使用 DEEP，因为生成是后台任务，允许稍高延迟换取历史覆盖。普通策略页面完全不调用 MemoryBear，所以策略页慢不能归因于记忆检索。

### 6.8 知识图谱与反思

轻量知识图谱从文本抽取简单三元组，支持关系扩展。反思引擎执行事实合并、冲突处理、模式抽象和摘要回写。它是启发式实现，不应被描述为完整语义图谱或通用推理器。对中文、代码和复杂关系的抽取准确率有限，生成结果仍需源笔记和质量校验约束。

### 6.9 与 RAG 的关系

MemoryBear 是用户历史，RAG 是外部或知识库检索。MemoryBear 结果带用户偏好和已验证产物，优先级通常更高；RAG 可补充时效性事实，但需要引用和来源。二者均通过有限字符预算注入，避免上下文无限增长。V3 不固定所有笔记为 8:2，而是按场景和可用历史决定权重；元数据应记录实际来源数量。

### 6.10 性能分析

MemoryBear 成本主要发生在后台生成：打开用户 SQLite、幂等同步相关记忆、执行关键词或图谱召回。性能优化优先级是减少重复同步、限制文本长度、稳定 ID、建立索引、限制召回条数和按用户分库。不能为了快而移除隔离、来源或五类语义。

策略偏好页的请求链没有 MemoryBear 调用。该页慢主要可能来自一次取回全部 Skill、每个 Skill 重复计算产品映射和浏览器渲染大量选项。正确优化是缓存静态映射、分页搜索和展开时加载，而不是削弱 MemoryBear。

### 6.11 安全与失败降级

Skill 指令只读不执行；MemoryBear 内容仅来自当前用户数据。数据库目录创建失败应让任务明确失败，不应静默切到共享文件。引擎异常不能删除业务数据。召回为空时返回明确的无相关历史文本。任何模型输出都不能覆盖记忆库中的原始来源。

## 7. Skill 注入算法

Skill 是带 `SKILL.md` 的用户工作规范。系统安全解压 ZIP，阻止路径穿越，限制文件数量和提示字符数。安装时按 Skill 名称去重，列表只返回名称、摘要、类别、启用状态、指令字符数和产品编号标签，不泄露完整私有指令。生成后台按当前用户、ID 和启用状态重新加载指令，防止前端伪造其他用户 Skill。

多个 Skill 按选择顺序拼接并受总字符预算约束。算法和 Skill 共用生成阶段兼容规则，因为两者都可能规定生成流程。质量手段只在自身组内比较。兼容规则不展示完整矩阵，只在实际选中已登记冲突时显示双方名称和原因。未知组合不应无依据报警。

产品编号映射固定为 0-13：文章、PPT、SOP、提示模板、课程大纲、访谈问答、工作流、产品介绍、测验、思维导图、行动清单、闪卡、脚本和 LLM Skill。编号是 UI 紧凑标签，真实存储仍使用稳定产品类型键，不能用数组位置替代业务键。

## 8. 兼容规则

V3 只有两个隐藏规则组。生成组把算法与 Skill 视为同类节点，支持算法-算法、算法-Skill 和 Skill-Skill 配对；质量组只包含真实质量手段。规则行包含左右 ID、显示名称、状态和原因。前端将任务级策略和每个产品独立策略分别检查，重复配对只提示一次。

后端仍执行结构校验和已登记算法冲突校验，防止绕过前端。错误提示必须具体，例如“单次直出 + 分层规划：执行模型冲突”，而不是笼统的“生成失败”。没有证据的组合默认不冲突，后续只有经过测试或明确规范才能登记新冲突。

## 9. 可观测性与溯源

生成任务记录状态、进度、当前步骤、科目、笔记和错误。产品元数据记录任务 ID、Skill ID 与名称、算法、质量手段、MemoryBear 提供者和层统计、兼容警告及每产品有效策略。该元数据用于解释和重新生成，不应包含 API Key、完整私有 Skill 指令或模型隐藏推理。

## 10. 测试策略

单元测试覆盖激活衰减、召回、存储、剪枝、反思、稳定 ID、五类元数据、用户隔离、兼容配对和前端冲突选择。后端全量测试保护任务、数据库、科目计数、编辑器和上传历史缺陷；前端 Node 测试保护代码块修复、策略选择、产品溯源和 Skill 页面。Vite 构建验证生产编译。

自动化通过不等于真实 LLM 质量验收。发布前仍需人工使用真实笔记生成至少一个长文产品，确认任务成功、产品可见、MemoryBear 没有跨笔记泄漏、代码块和图片正常、冲突提示可读。测试不得删除用户已有科目和笔记。

## 11. 已知限制与 V4 方向

V3 轻量 MemoryBear 是针对 Learn2Earn 使用面的忠实翻译，不是官方基础设施的逐文件移植。语义抽取和知识图谱偏启发式；未实装算法继续隐藏；质量评分不能替代事实审查；RAG 是否真实取决于检索后端。

V4 应在不改变上述契约的前提下优化 Skill 列表：服务端缓存产品映射，列表支持分页和搜索，策略页首屏不取全量 Skill，用户展开 Skill 区域后才按需加载，并在所有 Skill 矩形框显示 0-13 标签。MemoryBear 优化应集中在生成后台的增量同步和索引，不应成为策略页性能问题的替罪对象。

## 附录 A：关键代码索引

- `backend/app/services/generation_task_service.py`：任务编排、上下文注入、每产品策略和溯源。
- `backend/app/services/agentic_product_generator.py`：规划、正文生成和模型精炼。
- `backend/app/services/quality_enhancer.py`：质量手段注册和质量报告。
- `backend/app/services/content_polisher.py`：确定性内容清洗与结构修复。
- `backend/app/services/strategy_compat.py`：算法、质量、兼容规则和结构校验。
- `backend/app/services/memorybear_python_adapter.py`：五类语义映射、用户分库和幂等同步。
- `vendor/memory_bear_py/memory_bear/engine.py`：轻量 MemoryBear 核心引擎。
- `backend/app/services/skill_service.py`：Skill 安装、映射和提示拼接。
- `frontend/src/utils/generationStrategies.js`：客户端选择冲突检测。

## 附录 B：发布验收清单

1. 标签指向门禁通过的提交，发布标签未移动。
2. V1/V2/V3 启动器分别切换正确分支。
3. 后端、前端和引擎测试通过，生产构建成功。
4. 用户数据文件没有进入提交，也没有被测试清理。
5. 未实现算法未出现在可选 UI。
6. 冲突矩阵不展示，仅实际冲突配对提示。
7. MemoryBear 数据按用户隔离，重复生成不增加重复记忆。
8. 发布说明记录无 remote 导致的远程发布缺口。


## 附录 C：MemoryBear 与 RAG 基础理论原文

> 下文作为设计背景并入 V3 白皮书。若历史描述与 V3 当前实现、注册表或正文冲突，以正文和 V3 代码为准。

# MemoryBear 与 RAG 混合检索架构

> 适用版本：F04 `strategy_compat` 引入后（与《自由组合策略原理》互为姊妹篇）
> 目标：说明 Learn2Earn 的「长期记忆」是怎么设计的——为什么 MemoryBear 是**权威记忆来源**，而 RAG 退化为**外部知识补丁**；二者如何共存、如何被策略路由、如何注入生成管线。

---

## 1. 一句话结论

Learn2Earn 把"记忆"拆成两条互补通道：

- **MemoryBear（权威记忆来源）**：处理**用户自己的、已验证过的知识资产**——历史笔记、历史产品、用户偏好。它是"自己脑子里的东西"，优先级最高。
- **RAG（外部知识补丁）**：处理**外部、需实时检索的常识 / 百科 / 文档**（如"什么是 X""API 文档"）。它是"临时查的参考资料"，优先级低、仅作补充。

两条通道在 `techniques` 维度上以独立的开关存在（`memorybear` 与 `rag_grounding`），由**场景路由器**动态决定权重。**本仓库当前实装了 MemoryBear 全链路，RAG 仅保留接口与路由占位，未接入真实向量库**——这是有意为之：参赛演示场景下，用户自己的学习资产远比外部检索更有说服力。

```
        ┌──────────────────────────┐      ┌──────────────────────────┐
        │   MemoryBear 长期记忆       │      │   RAG 外部知识检索        │
        │  （权威记忆来源 / 高权重）  │      │  （外部知识补丁 / 低权重） │
        │                            │      │                            │
        │  历史笔记 / 历史产品 / 偏好  │      │  定义 / 原理 / 教程 / API  │
        └────────────┬───────────────┘      └─────────────┬──────────────┘
                     │                                     │
                     └──────────────┬──────────────────────┘
                                    ▼
                         route_scene() 场景路由器
                         （MemoryBear 0.8 / RAG 0.2 等）
                                    ▼
                    build_memory_context() 五层组装 + 3D 反熵增
                                    ▼
          prompt 注入：## MemoryBear 长期记忆（权威记忆来源）
```

---

## 2. MemoryBear 的五层记忆体系

模块 `backend/app/services/memorybear.py` 实现了一套受《Super Memory 技术调研》启发的分层记忆模型。每一层回答一个问题：**"这条记忆属于什么性质？该给它多少注意力？"**

| 层（layer） | 含义 | 数据来源 | 路由上限 |
|---|---|---|---|
| `perception` 感知 | 原始感官输入（本次未实装） | — | 0 |
| `working` 工作 | 当前正在处理的笔记主题（结构化元数据） | 当前 note 的标题/科目/阶段/标签 | 1 |
| `episodic` 情景 | 其他历史笔记（与当前主题相关者） | `notes`（排除当前） | 6 |
| `explicit` 显性 | 历史已生成的产品 | `products` | 4 |
| `implicit` 隐性 | 从行为推断出的用户偏好 | `derive_implicit_memory()` | 1 |

**关键设计决策**：工作记忆**只放结构化元数据，不放笔记正文**。正文由生成器的 `_build_source_memory()` → `source_brief` **单一负责注入**。这样能避免"同一篇笔记正文被 MemoryBear 与 source_brief 双重注入导致产品内容重复"——这是早期版本的一个真实 bug，已通过职责分离根治。

---

## 3. 三维激活度：相关性 × 近因 × 重要性

记忆不是"存了就有用"，而是"相关才激活"。MemoryBear 用三维加权打分，决定一条记忆最终是否进 prompt、排第几位。

### 3.1 近因（recency）—— 艾宾浩斯遗忘曲线

`ebbinghaus_recency(age_days)` 用**分段衰减**而非连续指数，模拟"刚学完最牢、一周后快速下滑、三个月后基本定型"：

```
0–1d  = 1.0   (刚记，强)
1–7d  = 0.7   (一周内)
7–30d = 0.4   (一月内)
30–90d= 0.2   (一季内)
>90d  = 0.1   (久远的)
```

### 3.2 重要性（importance）—— 行为信号打分

`importance_score(item)` 从 dict 抽取三类信号，经 `tanh` 压缩到 0~1 后加权：

- 编辑次数 `edit_count`（×0.5，5 次编辑趋近 1）
- 标签数 `tag_count`（×0.2，6 个标签趋近 1）
- 产品引用数 `product_ref_count`（×0.3，3 次引用趋近 1）

```python
def score(self) -> float:
    e = math.tanh(self.edit_count / 5.0)
    t = math.tanh(self.tag_count / 6.0)
    p = math.tanh(self.product_ref_count / 3.0)
    return round(0.5 * e + 0.2 * t + 0.3 * p, 4)
```

### 3.3 相关性（relevance）—— 与当前主题的 token 重叠

`relevance = |query_tokens ∩ item_tokens| / |query_tokens|`。

**遗忘无关噪音机制**：当 `relevance == 0`（与当前主题毫无交集）时，激活度被打到 `0.1 × recency × (0.3 + 0.7×importance)`——极低，保证"再重要也别来打扰当前主题"。这对应人类"需要时想得起来、不需要时不占用注意力"的特性。

### 3.4 三维加权汇总

```python
WEIGHTS = {"relevance": 0.5, "recency": 0.3, "importance": 0.2}
ACTIVATION_THRESHOLD = 0.08

def compute_activation(relevance, recency, importance) -> float:
    return 0.5*relevance + 0.3*recency + 0.2*importance
```

- 相关性权重最高（0.5）：记忆首先得"对题"。
- 低于 `ACTIVATION_THRESHOLD=0.08` 的记忆在 `_score_item` 阶段直接丢弃，不进后续路由。

---

## 4. 3D 反熵增引擎：事实合并 → 冲突解决 → 模式抽象

记忆会随时间"熵增"（碎片化、互相矛盾、淹没重点）。`run_entropy_engine()` 是压缩记忆、对抗熵增的核心。

### 4.1 事实合并 `fact_merge`

按**标题 token 重叠度（Jaccard）≥ 0.5** 把同主题的多条情景记忆聚合成组（并查集实现）。用标题而非全文算重叠，避免正文稀释主题相似度。

```python
overlap = len(a & b) / min(len(a), len(b))
if overlap >= 0.5:  # 50% 标题主题重叠 → 合并
    union(i, j)
```

### 4.2 冲突解决 `conflict_detect`

检测"标题前缀相同但内容差异大"的明显矛盾：对同组记忆算 token 对称差 / 并集，比例 > 0.5 视为冲突，返回人类可读的告警文本。

```python
sym = len(ta ^ tb); union = len(ta | tb)
if union and sym / union > 0.5:
    conflicts.append(f"{a.title!r} 与 {b.title!r} 内容存在差异")
```

### 4.3 模式抽象 `pattern_abstract`

从高频情景标题中抽取"≥2 条笔记共有的 token"，得到共同主题关键词（最多 5 个），用于给 LLM 提示"用户反复在学什么"。

### 4.4 报告 `EntropyReductionReport`

```python
@dataclass
class EntropyReductionReport:
    merged_groups: int = 0         # 合并后组数
    conflicts_detected: int = 0    # 检出冲突数
    patterns_abstracted: int = 0   # 抽象出模式数
    notes: list[str] = ...         # 人类可读摘要
```

---

## 5. 记忆路由器与场景路由器

### 5.1 记忆路由器 `route_memory`

按层限额（`MemoryRouterConfig.max_per_layer`）+ 总字符上限（`max_total_chars=10000`）裁剪。先按层内激活度排序取 top-N，再按激活度全局排序，最后做字符预算裁剪，保证 prompt 不爆。

### 5.2 场景路由器 `route_scene` —— MemoryBear vs RAG 的权重开关

这是"混合检索"的指挥中枢。启发式规则：

| 触发条件 | MemoryBear 权重 | RAG 权重 | 原因 |
|---|---|---|---|
| 历史笔记 ≥ 2 或 已有产品 | 0.8 | 0.2 | 历史记忆充足，用户自己的资产主导 |
| query 含外部关键词（定义/原理/教程/API…） | 0.3 | 0.7 | 明显在查外部知识，RAG 主导 |
| 其他 | 0.5 | 0.5 | 平衡混合 |

```python
@dataclass
class SceneRouterDecision:
    memorybear_weight: float
    rag_weight: float
    reason: str
```

> 注意：本仓库 RAG 分支当前是**占位**。即使路由判定 RAG=0.7，也只是把"RAG 权重"写进 `scene_router.meta` 供前端展示；真正的内容仍由 MemoryBear + `source_brief` 提供。后续接入真实向量库时，只需在 `route_scene` 返回高 RAG 权重的分支里补一段 KB 检索，架构无需改动。

---

## 6. 与质量增强技术（techniques）的关系

`techniques` 维度上有三个与"记忆/检索"相关的开关，它们**彼此独立、正交叠加**：

| technique | 性质 | 在管线中的位置 |
|---|---|---|
| `memorybear` | 长期记忆（权威来源） | `generation_task_service`：若包含 `memorybear`，调用 `build_memory_context()` 拼到 prompt 头部 |
| `source_grounding` | 源笔记约束（反幻觉锚点） | `agentic_product_generator._build_source_memory()` → `source_brief`，把**当前笔记正文**作为强约束注入 |
| `rag_grounding` | RAG 原文检索（外部补丁） | 已在 `DEFAULT_STRATEGIES` 注册为可选 technique，但本仓库未实装真实检索 |

**三者分工不冲突**：

- `source_grounding` = "**锁死原文**"（当前这篇笔记不能胡编）—— 反幻觉的地基。
- `memorybear` = "**带上历史**"（你以前学过/做过什么、你的偏好）—— 让产品有连续性与个人味。
- `rag_grounding` = "**补外部常识**"（这概念的定义/原理）—— 仅在用户明显在查外部知识时加权。

代码注入点（`generation_task_service.py`）：

```python
if "memorybear" in techniques:
    memory_context, memory_meta = build_memory_context(
        note, subject, table("notes", user).list(), table("products", user).list()
    )
    prompt = f"{prompt}\n\n## MemoryBear 长期记忆（权威记忆来源，优先遵循用户历史偏好与已验证知识）\n{memory_context}"
```

注入位置刻意放在 prompt **头部**并标注"权威记忆来源"，使 LLM 倾向于**优先遵循用户历史**而非凭空发挥——这是 MemoryBear 对抗幻觉的第二道保险（第一道是 `source_grounding` 锁死原文）。

---

## 7. 对外接口

`backend/app/routers/memorybear.py` 暴露：

- `POST /api/memorybear/context` —— 给定 note 返回 `build_memory_context()` 的 `context` + `meta`（各层统计、反熵增报告、场景路由决策）。
- `POST /api/memorybear/stats` —— `memorybear_stats()` 聚合各层条目数、重要性分布、冲突点。
- `POST /api/memorybear/route` —— 仅返回 `SceneRouterDecision`（权重 + 原因），供前端做可视化。

这些接口让前端可以实时展示"当前产品生成参考了你的哪些历史记忆、MemoryBear 与 RAG 的占比、是否检出冲突"，是参赛演示时体现"AI 真的记住了你"的关键卖点。

---

## 8. 设计取舍小结

| 决策 | 选择 | 理由 |
|---|---|---|
| 记忆主体 | MemoryBear 主导，RAG 补丁化 | 用户自有资产比外部检索更有说服力、更安全 |
| 工作记忆内容 | 仅元数据，正文交 `source_brief` | 避免同一笔记正文双重注入导致重复 |
| 近因曲线 | 分段衰减而非连续指数 | 与艾宾浩斯实证曲线一致，可解释 |
| 相关性门控 | `relevance==0` 强制低激活 | 实现"遗忘无关噪音" |
| RAG 实装 | 暂留接口与路由占位 | 演示场景不需要真实 KB，架构已预留扩展点 |
| 注入位置 | MemoryBear 置于 prompt 头部 | 引导 LLM 优先遵循用户历史 |

**一句话**：MemoryBear 负责"你是谁、你学过什么"，`source_grounding` 负责"这篇笔记说了什么"，`rag_grounding` 预留"外面的世界是什么样"。三者正交、可自由组合，由场景路由器在每次生成时动态调和——这正是《自由组合策略原理》中"三维正交"理念在记忆子系统的落地。

## 附录 D：自由组合策略基础理论原文

> 下文解释策略正交与组合边界。V3 已将可视矩阵收敛为两个隐藏规则组，相关现状以正文第八章为准。

# 自由组合策略原理：技能 × 算法 × 质量技术

> 适用版本：F04 `strategy_compat` 引入后
> 目标：说明为什么「任意技能 + 任意算法 + 任意质量技术」可以自由组合，系统如何在不阻塞用户的前提下保证安全。

---

## 1. 一句话结论

在 Learn2Earn 中，**技能（skill）、生成算法（algorithm）、质量增强技术（quality technique）三者是完全正交的三个维度**。
它们各自独立存储、独立校验、独立生效；系统只做「结构性合法性校验」，**对任何组合都放行**，仅对未知 / 未实现 / 缺 LLM / 未知 skill 给出**非阻塞的警告（warning）**。

因此用户可以自由组合，例如：

- `LLM Skill + reflexion（未实现）+ memorybear + hallucination_check`
- `无 skill + single_pass（未实现）+ seo_optimization`
- `多个 skill + chunked_parallel（未实现）+ source_grounding`

即使其中某些算法尚未实现，生成流程也不会被拒绝，而是降级为可用算法并提示用户。

---

## 2. 数据模型：三者彼此独立

生成任务的底层模型 `GenerationTask`（`backend/app/models.py`）把三者拆成三个独立的 JSON 列：

```python
skill_ids  = Column(JSON, default=[])   # 用户从技能仓库勾选的 skill 列表
algorithms = Column(JSON, default=[])   # 生成算法列表（如 hierarchical_planning）
techniques = Column(JSON, default=[])   # 质量增强技术列表（如 memorybear / source_grounding）
```

- 因为是独立的 JSON 列，**没有任何外键约束把它们绑死**——所以天生支持「多对多」自由组合。
- 生成主入口 `AgenticProductGenerator.generate(algorithms, techniques)` 直接接收自由列表，
  缺省值为 `["hierarchical_planning", "iterative_refinement"]`，但用户传什么就接受什么。

```
        ┌──────────────┐      ┌──────────────┐      ┌──────────────────┐
        │  skill_ids   │      │  algorithms  │      │    techniques    │
        │  (技能仓库)   │      │  (生成算法)   │      │  (质量增强技术)   │
        └──────┬───────┘      └──────┬───────┘      └────────┬─────────┘
               │                     │                       │
               └──────────┬──────────┴───────────┬──────────┘
                          ▼                      ▼
                  validate_combination()    AgenticProductGenerator.generate()
                          │                      │
                          ▼                      ▼
                   errors / warnings      LLM 生成 + 质量增强管线
                   （仅 warning 非阻塞）   （逐 technique 应用）
```

---

## 3. 校验层 `strategy_compat`：只报错，不阻塞

核心模块 `backend/app/services/strategy_compat.py` 提供：

### 3.1 算法注册表 `GENERATION_ALGORITHMS`

每个算法声明两个属性：

| 算法 | 已实现(impl) | 依赖 LLM(needs_llm) |
|------|--------------|---------------------|
| `hierarchical_planning` | ✅ | ✅ |
| `iterative_refinement`  | ✅ | ✅ |
| `single_pass`           | ❌ | ✅ |
| `chunked_parallel`      | ❌ | ✅ |
| `reflexion`             | ❌ | ✅ |

> 未实现的算法不是「非法」，而是「暂未接入」——系统会保留它、告警、并在实际生成时降级，
> 而不是拒绝整个任务。这是「开放矩阵」的关键设计。

质量技术注册表来自 `quality_enhancer.QUALITY_TECHNIQUES`（共 10 项，部分 `implemented=False`），
例如 `source_grounding / rag_grounding / memorybear / quality_scoring / hallucination_check /
seo_optimization / example_driven` 等。

### 3.2 `validate_combination(...)` 的分层策略

```python
validate_combination(skill_ids, algorithms, techniques,
                     *, available_skill_ids=None, llm_ready=True)
# -> StrategyCompatResult(errors, warnings, normalized)
```

- **ERROR（硬错误，阻断保存）**：仅两种情况
  1. 参数不是 list（类型错误）；
  2. `algorithms` 为空（没有算法就无法生成）。
- **WARNING（软警告，不阻断）**：
  - 算法/技术在注册表中未知；
  - 算法/技术标记为 `impl=False`（未实现，将降级）；
  - 算法 `needs_llm=True` 但当前 `llm_ready=False`（本地无 LLM，将降级）；
  - `skill_ids` 中存在不在 `available_skill_ids` 中的未知 skill。

`normalized` 为去重、去空后的干净组合，供下游直接使用。

### 3.3 为什么这样设计

| 维度 | 传统做法（硬编码矩阵） | 本系统（开放矩阵） |
|------|----------------------|-------------------|
| 新增算法 | 要改校验白名单 | 注册表加一行即可 |
| 未知组合 | 直接拒绝 | 放行 + 告警 |
| 未实现算法 | 报错 | 降级 + 告警 |
| 用户自由度 | 低 | 高（任意组合） |

开放矩阵让产品可以「先放开、后完善」：算法可以先声明、先被选择，实现再逐步补齐，
不会卡住用户的生成流程。

---

## 4. 前端如何拿到目录：`GET /api/ai/strategies`

`backend/app/routers/ai.py` 暴露：

```http
GET /api/ai/strategies
```

返回 `list_strategies()` 的结果：

```json
{
  "algorithms": [ {"id":"hierarchical_planning","name":"分层规划","impl":true,"needs_llm":true}, ... ],
  "techniques":  [ {"id":"memorybear","name":"MemoryBear 长期记忆","impl":true}, ... ],
  "note": "所有算法与质量技术均可自由组合；未实现项会在生成时降级并给出提示。"
}
```

前端据此渲染「算法」与「质量技术」的可勾选列表，并在提交时把用户组合回传后端做
`validate_combination` 校验，仅当存在 ERROR 时才拦截。

---

## 5. 每类产品的默认组合 `DEFAULT_STRATEGIES`

`backend/app/routers/tasks.py` 中的 `DEFAULT_STRATEGIES` 以 `PRODUCT_TYPES` 为键，
为每类剩余产品给出缺省 `algorithms` / `techniques` / `recommended_skill_keywords`：

- `article / course_outline / sop` 默认额外启用 `chunked_generation`（分块生成）；
- 其余类型默认 `hierarchical_planning + iterative_refinement`；
- 质量技术默认开启 `source_grounding, rag_grounding, memorybear, quality_scoring, hallucination_check, seo_optimization`。

用户创建任务时若不选，就用默认值；若自选，则走 `validate_combination` 的开放校验。

---

## 6. 小结

- **自由组合 ≠ 无约束**：约束只存在于「结构性合法性」（类型正确、至少有一个算法）。
- **自由组合 = 开放矩阵**：任何 skill × 任何 algorithm × 任何 technique 都允许，
  未知/未实现/缺 LLM/未知 skill 只产生 warning，绝不阻塞。
- 这样既能让用户充分探索「把学习过程变成赚钱产品」的多种玩法，
  又能让工程侧按节奏渐进补齐算法实现，而不打断既有用户。
