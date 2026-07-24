# Knowledge, Skills & Workflows Design

**Language:** [中文](#中文) | [English](#english)

---

<a id="中文"></a>

## 中文

### 1. 功能概览

在完成 Agents、Tools、MCPs 的设计之后，我们现在增加三个核心功能模块：

| 功能 | 目标 | 交互方式 |
|------|------|--------|
| **Knowledge** | 文档知识库集成 | 用户上传 → Agent 绑定 → 优先匹配文档 |
| **Skills** | 可复用操作脚本库 | 用户上传 → Agent 调用 → Anthropic 标准格式 |
| **Workflows** | 智能流程编排 | Agent 协作 → 同项目绑定 → 多步骤执行 |

---

### 2. Knowledge（知识库管理）

#### 2.1 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                  Knowledge System                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Upload → Parse → Chunk → Embed → Vector Store         │
│    ↓        ↓       ↓       ↓        ↓                  │
│  File    Extract  Split  Embedding  Storage            │
│ (PDF,    Info    into   (e.g.,      (e.g.,            │
│  DOCX,   &Meta   Chunks  OpenAI)    Postgres +        │
│  MD,     data           Embeddings)  pgvector)         │
│  TXT)                                                   │
│                                                         │
│  ┌──────────────────────────────────────────┐          │
│  │   RAG Pipeline (Retrieval-Augmented)     │          │
│  │   Query → Similarity Search → Top-K     │          │
│  │   Results Feed to LLM Context           │          │
│  └──────────────────────────────────────────┘          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### 2.2 数据模型

**Database Schema:**

```python
# Knowledge 资源
class KnowledgeResource(Resource):
    """知识库资源"""
    # 继承自 Resource
    # kind = ResourceKind.KNOWLEDGE
    
    # 知识库特定字段
    storage_type: str  # "local" | "s3" | "gcs"
    document_count: int  # 包含的文档数
    total_tokens: int  # 总 token 数（用于成本计算）
    embedding_model: str  # "openai:text-embedding-3-small" | "local:all-minilm"
    chunk_size: int = 512  # 分块大小
    chunk_overlap: int = 50  # 分块重叠
    similarity_threshold: float = 0.7  # 相似度阈值
    top_k: int = 3  # 返回 Top-K 相似文档
    config: Dict[str, Any]  # 其他配置

# 文档
class Document(Base):
    """单个文档"""
    __tablename__ = "documents"
    
    id: str = Column(String, primary_key=True, default=uuid4)
    knowledge_id: str = Column(String, ForeignKey("registry.id"))
    project_id: str = Column(String, ForeignKey("projects.id"))
    
    filename: str  # 原始文件名
    file_type: str  # "pdf" | "docx" | "md" | "txt"
    file_path: str  # 存储路径
    file_size: int  # 字节数
    
    upload_time: datetime
    created_by: str
    
    # 处理状态
    status: str  # "pending" | "processing" | "ready" | "failed"
    error_message: Optional[str]
    
    # 元数据
    metadata: Dict[str, Any]  # 例如 title、author、creation_date 等

# 文档分块
class DocumentChunk(Base):
    """文档分块（用于向量化）"""
    __tablename__ = "document_chunks"
    
    id: str = Column(String, primary_key=True, default=uuid4)
    document_id: str = Column(String, ForeignKey("documents.id"))
    knowledge_id: str = Column(String, ForeignKey("registry.id"))
    
    chunk_index: int  # 分块序号
    content: str  # 文本内容
    tokens: int  # token 数
    
    # 向量嵌入
    embedding: Vector(1536)  # 或其他维度，使用 pgvector
    
    # 元数据
    source_metadata: Dict[str, Any]  # 例如页码、位置等

# Agent 与 Knowledge 的绑定
class AgentKnowledgeBinding(Base):
    """Agent 绑定的知识库"""
    __tablename__ = "agent_knowledge_bindings"
    
    id: str = Column(String, primary_key=True, default=uuid4)
    agent_id: str = Column(String, ForeignKey("registry.id"))
    knowledge_id: str = Column(String, ForeignKey("registry.id"))
    project_id: str = Column(String, ForeignKey("projects.id"))
    
    # 优先级（越高越优先）
    priority: int = Column(Integer, default=0)
    
    # 绑定配置
    enabled: bool = Column(Boolean, default=True)
    similarity_threshold: Optional[float]  # 覆盖知识库默认阈值
    top_k: Optional[int]  # 覆盖知识库默认 top_k
    
    created_at: datetime
    updated_at: datetime
```

#### 2.3 交互流程

**用户流程（Frontend）：**
```
1. 在 Resources → Knowledge 创建新知识库
   └─ 输入：名称、描述、embedding 模型、分块参数
   
2. 上传文档
   └─ 支持类型：PDF、DOCX、MD、TXT
   └─ 上传后进入处理队列
   
3. 查看文档列表 & 处理状态
   └─ 显示已上传、处理中、已完成、失败的文档
   └─ 支持删除、重新处理
   
4. 将知识库绑定到 Agent
   └─ Agent 编辑 → Knowledge 选项卡
   └─ 搜索 & 选择知识库
   └─ 配置优先级、相似度阈值等
```

**系统流程（Backend）：**
```
1. 文档上传处理
   ├─ 接收文件 → 校验 → 存储
   ├─ 触发异步任务：ParseDocumentTask
   │
2. 异步解析文档
   ├─ 提取文本内容 & 元数据
   ├─ 分块处理（按 chunk_size & chunk_overlap）
   ├─ Token 计数
   │
3. 异步嵌入向量
   ├─ 遍历所有 chunk
   ├─ 调用 embedding 模型（OpenAI API 或本地模型）
   ├─ 存储 embedding 到 pgvector
   ├─ 更新 document 状态为 "ready"
   │
4. 运行时检索
   ├─ Agent 收到用户提问
   ├─ 对问题进行向量化
   ├─ 查询所有绑定知识库的 chunks
   ├─ 按相似度和优先级排序
   ├─ 提取 Top-K 结果
   ├─ 注入到 LLM 上下文（RAG）
   ├─ LLM 优先基于文档回答
   └─ 如文档无关答案，则调用大模型通用知识
```

#### 2.4 API 端点

```
POST   /api/v1/resources              # 创建 Knowledge 资源
POST   /api/v1/knowledge/{id}/documents/upload    # 上传文档
GET    /api/v1/knowledge/{id}/documents          # 列表文档
DELETE /api/v1/knowledge/{id}/documents/{doc_id} # 删除文档
POST   /api/v1/knowledge/{id}/reprocess          # 重新处理文档

# Agent 绑定知识库
POST   /api/v1/agents/{id}/knowledge             # 绑定
DELETE /api/v1/agents/{id}/knowledge/{knowledge_id}  # 取消绑定
GET    /api/v1/agents/{id}/knowledge             # 列表

# 查询接口
POST   /api/v1/knowledge/{id}/query               # 手动查询知识库
```

#### 2.5 实现要点

- **向量存储**：使用 PostgreSQL + pgvector 扩展
- **Embedding 模型**：支持 OpenAI text-embedding-3-small（3072维）和本地开源模型（如 all-MiniLM）
- **异步处理**：使用 Celery 或 asyncio 处理大文件和 embedding
- **缓存**：缓存 embedding 结果，避免重复计算
- **成本控制**：统计 token 数，可选向用户展示

#### 2.6 高级特性和优化

**混合搜索**：结合 BM25 全文搜索和向量搜索，提高检索质量
- 精确关键词匹配 + 语义理解
- 加权融合两种结果

**增量更新**：文档版本控制、增量嵌入
- 只对新增/修改的 chunk 重新计算 embedding
- 自动通知绑定的 Agent
- 支持版本回滚

**权限管理**：精细化的知识库访问控制
- 限制哪些 Agent 可以访问哪些文档
- 支持部分 chunk 级别的权限限制

**成本监控**：实时显示 embedding 成本、缓存命中率
- 按 Agent / 项目分配成本
- 批量嵌入优化，减少 API 调用

**相关性反馈**：收集用户反馈优化 RAG
- 用户标记搜索结果相关性
- A/B 测试不同参数组合

**元数据和分类**：支持分类、标签、重要性等级、过期日期、所有者管理

---

### 3. Skills（可复用脚本库）

#### 3.1 架构设计

```
┌──────────────────────────────────────────────────────────────┐
│                    Skills System                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Skill 文件夹结构：                                          │
│  my-skill/                                                   │
│  ├── skill.yaml              # 元数据定义                   │
│  ├── README.md              # 文档                          │
│  ├── src/                                                    │
│  │   ├── main.py           # 主要逻辑                      │
│  │   ├── utils.py          # 工具函数                      │
│  │   └── ...                                               │
│  ├── config/                                                │
│  │   └── default.json      # 配置示例                      │
│  └── tests/                 # 单元测试                      │
│      └── test_main.py                                       │
│                                                              │
│  Skill 定义遵循 Anthropic 标准：                             │
│  - 统一的配置格式                                          │
│  - 清晰的输入/输出 schema                                   │
│  - 错误处理约定                                            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### 3.2 数据模型

```python
# Skill 资源
class SkillResource(Resource):
    """技能资源"""
    # 继承自 Resource
    # kind = ResourceKind.SKILL
    
    # Skill 特定字段
    storage_type: str  # "local" | "git" | "s3"
    repo_url: Optional[str]  # Git repo 地址（如果是 git 来源）
    repo_branch: str = "main"  # Git 分支
    
    # Skill 元数据
    author: str
    version: str  # semantic versioning: 1.0.0
    capabilities: List[str]  # 例如 ["data_processing", "api_integration"]
    requirements: Dict[str, str]  # 依赖，例如 {"python": ">=3.9", "numpy": ">=1.20"}
    
    # 入口点
    entrypoint: str  # "main:execute" 表示调用 src/main.py 的 execute 函数
    
    # 配置 schema
    input_schema: Dict[str, Any]  # JSON Schema
    output_schema: Dict[str, Any]  # JSON Schema
    
    # 配置
    config: Dict[str, Any]
    
    # 状态
    status: str  # "active" | "inactive" | "deprecated"
    last_modified: datetime

# Agent 与 Skill 的绑定
class AgentSkillBinding(Base):
    """Agent 绑定的 Skill"""
    __tablename__ = "agent_skill_bindings"
    
    id: str = Column(String, primary_key=True, default=uuid4)
    agent_id: str = Column(String, ForeignKey("registry.id"))
    skill_id: str = Column(String, ForeignKey("registry.id"))
    project_id: str = Column(String, ForeignKey("projects.id"))
    
    # 优先级与可用性
    enabled: bool = Column(Boolean, default=True)
    priority: int = Column(Integer, default=0)
    
    # Skill 实例配置（覆盖模板）
    instance_config: Dict[str, Any]
    
    created_at: datetime
    updated_at: datetime
```

**skill.yaml 示例：**
```yaml
name: data-analyzer
version: 1.0.0
description: 数据分析和可视化 Skill
author: HyperAgents Team

capabilities:
  - data_processing
  - statistical_analysis
  - visualization

requirements:
  python: ">=3.9"
  pandas: ">=1.5.0"
  matplotlib: ">=3.5.0"

entrypoint: "main:execute"

input_schema:
  type: object
  properties:
    data:
      type: array
      description: "输入数据"
    operation:
      type: string
      enum: ["summary", "correlation", "visualization"]
      description: "操作类型"
    config:
      type: object
      description: "操作配置"
  required: ["data", "operation"]

output_schema:
  type: object
  properties:
    result:
      type: object
      description: "分析结果"
    metadata:
      type: object
      description: "元数据（执行时间等）"
  required: ["result"]
```

#### 3.3 交互流程

**用户流程（Frontend）：**
```
1. 在 Resources → Skills 创建新 Skill
   └─ 上传文件夹 或 输入 Git 仓库地址
   └─ 系统自动解析 skill.yaml
   └─ 验证入口点和 schema
   
2. 查看 Skill 详情
   ├─ README（文档）
   ├─ 配置项列表
   ├─ 入口参数说明（schema）
   ├─ 版本历史
   └─ 可用的 Agent 绑定
   
3. 测试 Skill
   └─ 提供测试输入 → 执行 → 查看输出
   
4. 将 Skill 绑定到 Agent
   └─ Agent 编辑 → Skills 选项卡
   └─ 搜索 & 选择 Skill
   └─ 配置实例参数（覆盖模板）
```

**系统流程（Backend）：**
```
1. Skill 上传与解析
   ├─ 接收文件夹 & 解压
   ├─ 解析 skill.yaml
   ├─ 验证必要字段和 schema
   ├─ 记录到数据库
   │
2. Skill 执行（由 Agent 触发）
   ├─ 加载 Skill 代码
   ├─ 准备运行环境（虚拟环境 or 沙箱）
   ├─ 校验输入参数
   ├─ 执行入口函数
   ├─ 捕获输出和异常
   └─ 返回结果 or 错误信息
   
3. Skill 版本管理
   ├─ 支持多版本并行
   ├─ Agent 可以选择特定版本
   ├─ 自动保留历史版本
```

#### 3.4 API 端点

```
POST   /api/v1/resources                   # 创建 Skill 资源
GET    /api/v1/skills/{id}                 # 获取 Skill 详情
PUT    /api/v1/skills/{id}                 # 更新 Skill
DELETE /api/v1/skills/{id}                 # 删除 Skill
POST   /api/v1/skills/{id}/test            # 测试 Skill

# Agent 绑定 Skill
POST   /api/v1/agents/{id}/skills          # 绑定
DELETE /api/v1/agents/{id}/skills/{skill_id}  # 取消绑定
GET    /api/v1/agents/{id}/skills          # 列表
```

#### 3.5 实现要点

- **标准化格式**：严格遵循 Anthropic skill 定义（参考 [Anthropic Skills](https://github.com/anthropics/anthropic-sdk-python)）
- **沙箱执行**：使用 Docker 容器或 Python 虚拟环境隔离 Skill 执行
- **资源限制**：限制 CPU、内存、执行时间
- **版本控制**：支持语义化版本，允许多版本共存
- **依赖管理**：自动解析和安装 requirements
- **错误处理**：统一的异常捕获和日志

#### 3.6 高级特性和优化

**Skill 市场生态**：构建 Skill Hub（类似 npm）
- 社区共享和评分系统
- 依赖关系图展示
- 热门排序（基于下载量、评分、更新时间）
- 安全扫描和验证

**性能优化**：
- Skill 预热：启动时预加载常用 Skill
- 编译缓存：缓存已编译字节码
- 并行执行：独立 Skill 支持并行运行
- 性能监控：记录耗时、内存、成功率

**高级沙箱安全**：
- CPU / 内存 / 超时限制
- 网络隔离（白名单 / 黑名单）
- 文件系统隔离（只读路径 / 可写路径）
- 系统调用限制

**依赖冲突检测**：自动分析多 Agent 的 Skill 依赖
- 版本兼容性检查
- 冲突自动提示和解决方案

**增强的错误处理**：
- 完整错误堆栈跟踪
- 执行上下文保留（Agent 配置、输入参数）
- 调试模式支持

**执行指标和日志**：
- 耗时、内存峰值、CPU 使用率
- 成功率统计

---

### 4. Workflows（工作流编排）

#### 4.1 架构设计

```
┌─────────────────────────────────────────────────────────┐
│           Workflows (Agent to Agent)                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  工作流执行流程：                                       │
│                                                         │
│  ┌──────────────┐                                       │
│  │  Input/Trigger                                       │
│  └────────┬─────┘                                       │
│           │                                             │
│           ▼                                             │
│  ┌──────────────────────┐                              │
│  │  Agent A (Expert-1)  │◄─── Knowledge A             │
│  │  Skills: A1, A2      │◄─── Skills: A1, A2          │
│  │  MCPs: API-1         │◄─── MCPs: API-1             │
│  └──────┬───────────────┘                              │
│         │ Output: JSON                                 │
│         │                                              │
│  ┌──────▼────────────────────────┐                    │
│  │  Routing Decision             │                    │
│  │  (Based on Agent Output Tags) │                    │
│  └──────┬──────────────┬──────────┘                    │
│         │ Path-1       │ Path-2                        │
│         │              │                              │
│    ┌────▼────┐    ┌────▼────┐                         │
│    │ Agent B  │    │ Agent C  │                        │
│    │(Expert-2)│    │(Expert-3)│                        │
│    └────┬─────┘    └────┬─────┘                        │
│         │                │                             │
│    ┌────▼────────────────▼─────┐                      │
│    │ Merge Results             │                      │
│    │ & Generate Final Answer   │                      │
│    └────────┬──────────────────┘                       │
│             │                                          │
│             ▼                                          │
│         Output/Response                               │
│                                                       │
└─────────────────────────────────────────────────────────┘

工作流特点：
- 多 Agent 协作
- 同一项目内的 Agent
- 条件路由（基于 output tags）
- 并行或串行执行
- 最终结果聚合
```

#### 4.2 数据模型

```python
# Workflow 资源
class WorkflowResource(Resource):
    """工作流资源"""
    # 继承自 Resource
    # kind = ResourceKind.WORKFLOW
    
    project_id: str  # 必须在同一项目内
    
    # 工作流配置
    definition: Dict[str, Any]  # 工作流定义（DAG 或 YAML）
    
    # 约束
    allowed_agents: List[str]  # 工作流允许使用的 Agent ID 列表
    
    # 状态
    status: str  # "draft" | "active" | "paused"
    version: str  # 版本号
    
    # 运行配置
    timeout_seconds: int = 300  # 工作流总超时
    max_iterations: int = 10  # 最大迭代次数
    
    config: Dict[str, Any]

# 工作流执行记录
class WorkflowRun(Base):
    """工作流执行记录"""
    __tablename__ = "workflow_runs"
    
    id: str = Column(String, primary_key=True, default=uuid4)
    workflow_id: str = Column(String, ForeignKey("registry.id"))
    project_id: str = Column(String, ForeignKey("projects.id"))
    
    # 触发信息
    triggered_by: str  # user ID or system
    trigger_type: str  # "manual" | "scheduled" | "event"
    
    # 输入
    input_data: Dict[str, Any]
    
    # 执行过程
    steps: List[Dict[str, Any]]  # 每一步的执行记录
    status: str  # "pending" | "running" | "completed" | "failed"
    
    # 结果
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    
    # 时间戳
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]

# 工作流步骤记录
class WorkflowStepExecution(Base):
    """工作流单个步骤的执行"""
    __tablename__ = "workflow_step_executions"
    
    id: str = Column(String, primary_key=True, default=uuid4)
    workflow_run_id: str = Column(String, ForeignKey("workflow_runs.id"))
    
    step_name: str
    agent_id: str
    
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    
    status: str  # "pending" | "running" | "completed" | "failed"
    error_message: Optional[str]
    
    started_at: datetime
    completed_at: Optional[datetime]
```

**Workflow 定义格式（YAML）：**

```yaml
name: customer-support-workflow
version: 1.0.0
description: 客户支持多轮服务工作流

# 所需 Agent（同项目内）
required_agents:
  - classifier  # 分类 Agent
  - resolver    # 解决 Agent
  - escalator   # 升级 Agent

# 工作流步骤（DAG）
steps:
  - id: step_1
    name: classify_issue
    agent: classifier
    input:
      source: "{{ input.customer_question }}"
    output_format:
      issue_type: string
      priority: enum[low, medium, high]
      tags: array
    routing:
      - condition: "priority == 'high'"
        next: step_3_escalate
      - condition: "issue_type == 'technical'"
        next: step_2_resolve_technical
      - default: step_2_resolve_general

  - id: step_2_resolve_technical
    name: resolve_technical_issue
    agent: resolver
    input:
      context: "{{ step_1.output }}"
      question: "{{ input.customer_question }}"
    on_error: step_3_escalate  # 如果失败，升级

  - id: step_2_resolve_general
    name: resolve_general_issue
    agent: resolver
    input:
      context: "{{ step_1.output }}"
      question: "{{ input.customer_question }}"

  - id: step_3_escalate
    name: escalate_to_human
    agent: escalator
    input:
      context: "{{ step_1.output }}"
      issue_details: "{{ input.customer_question }}"

# 最终输出聚合
output:
  type: object
  properties:
    resolution: "{{ step_2_resolve_technical.output || step_2_resolve_general.output }}"
    escalation_ticket: "{{ step_3_escalate.output }}"
    summary: "Resolved via {{ step_1.output.issue_type }} path"

# 约束
constraints:
  timeout_seconds: 300
  max_retries: 2
  all_agents_same_project: true
```

#### 4.3 交互流程

**用户流程（Frontend）：**
```
1. 在 Resources → Workflows 创建新工作流
   ├─ 选择项目
   ├─ 可视化 DAG 编辑器 或 YAML 编辑
   ├─ 选择多个 Agent（同项目）
   ├─ 配置路由规则
   └─ 保存草稿 or 发布
   
2. 工作流可视化
   ├─ 展示 Agent 节点和连接
   ├─ 显示条件路由
   ├─ 标注入出参数
   
3. 测试工作流
   └─ 提供测试输入 → 执行 → 查看每步输出
   
4. 运行工作流
   ├─ 手动运行
   ├─ 查看实时执行进度
   └─ 查看历史运行记录
```

**系统流程（Backend）：**
```
1. 工作流初始化
   ├─ 加载工作流定义
   ├─ 验证所有 Agent 在同一项目
   ├─ 初始化执行上下文
   
2. 工作流执行引擎（支持 DAG 执行）
   ├─ 拓扑排序步骤
   ├─ 按依赖关系执行
   ├─ 支持并行执行相互独立的步骤
   │
3. 单步执行
   ├─ 准备输入（模板变量替换）
   ├─ 调用目标 Agent（异步）
   ├─ 等待 Agent 完成
   ├─ 捕获输出
   ├─ 条件路由判断
   │
4. 错误处理 & 重试
   ├─ 捕获 Agent 异常
   ├─ 按配置重试
   ├─ on_error 路由
   │
5. 结果聚合
   ├─ 合并各步骤输出
   ├─ 执行 output 模板
   ├─ 返回最终结果
```

#### 4.4 API 端点

```
POST   /api/v1/resources                    # 创建 Workflow 资源
GET    /api/v1/workflows/{id}               # 获取 Workflow 详情
PUT    /api/v1/workflows/{id}               # 更新 Workflow
DELETE /api/v1/workflows/{id}               # 删除 Workflow
POST   /api/v1/workflows/{id}/test          # 测试 Workflow

# 执行工作流
POST   /api/v1/workflows/{id}/run           # 执行工作流
GET    /api/v1/workflows/{id}/runs          # 获取历史运行
GET    /api/v1/workflows/{id}/runs/{run_id} # 获取单次运行详情
```

#### 4.5 实现要点

- **DAG 执行引擎**：使用 Celery + Airflow 思想实现
- **模板变量**：支持 `{{ step_name.output.field }}` 和 `{{ input.field }}` 的模板替换
- **条件路由**：使用简单的表达式语言（如 CEL 或 JsonLogic）
- **并行执行**：识别不依赖的步骤，并行调用多个 Agent
- **异常处理**：支持 on_error 路由和重试策略
- **超时控制**：单步和全局超时设置
- **可观测性**：详细的执行日志和中间结果存储

#### 4.6 高级特性和优化

**人类在环（Human in the Loop）**：
- 审批节点：支持人工干预和决策
- 超时自动升级：如无人审批可升级给更高权限用户
- 审批字段配置：灵活指定需要审批的信息

**工作流版本控制**：
- 支持多版本并行运行
- 灰度发布和蓝绿部署
- 一键回滚到历史版本

**A/B 测试**：对比测试两个工作流版本
- 流量分配策略
- 关键指标对比：成功率、耗时、用户满意度
- 自动赢家判定

**复杂条件表达式**：
- 支持多条件逻辑（AND / OR / NOT）
- 比较操作符：>= / <= / == / != / in / not in
- 更灵活的路由决策

**循环和递归**：
- 条件循环支持
- 最大迭代次数限制（防止无限循环）
- 动态退出条件

**工作流监控和告警**：
- 实时监控：成功率、耗时、Agent 响应时间
- 自定义告警规则
- 多渠道通知：Email / Slack / Webhook

**审计日志**：完整的执行审计跟踪
- 每个步骤的决策记录
- 执行者、IP 地址等
- 合规性审计支持

**断点调试**：
- 条件断点：在特定条件下暂停
- 手工审核点：人工审核后继续
- 执行上下文保留：供后续调试

**工作流模板库**：
- 预建常用模板
- 模板参数化：快速定制
- 克隆和修改

---

### 5. 实现路线图

#### Phase 1: Knowledge（第1阶段 - 2周）
- [ ] 数据库设计和迁移
- [ ] 文档上传和解析
- [ ] 向量嵌入（使用 OpenAI）
- [ ] RAG 集成到 Agent
- [ ] 前端 UI 开发

#### Phase 2: Skills（第2阶段 - 1.5周）
- [ ] 标准化 Skill 格式
- [ ] Skill 解析和验证
- [ ] 沙箱执行环境
- [ ] Agent 绑定 Skill
- [ ] 前端 UI 开发

#### Phase 3: Workflows（第3阶段 - 2周）
- [ ] DAG 执行引擎
- [ ] 模板变量系统
- [ ] 条件路由
- [ ] Agent 调度
- [ ] 前端可视化编辑器

---

### 6. 技术栈建议

| 组件 | 推荐方案 | 备选 |
|------|---------|------|
| **向量库** | PostgreSQL + pgvector | Milvus, Qdrant |
| **Embedding 模型** | OpenAI text-embedding-3-small | all-MiniLM-L6-v2 |
| **Skill 执行** | Docker Container | Python venv |
| **工作流引擎** | 自定义 DAG + Celery | Airflow |
| **前端编辑** | Vue + Vis.js (DAG) | React Flow |

---

<a id="english"></a>

## English

### 1. Feature Overview

After completing the design of Agents, Tools, and MCPs, we now introduce three core functional modules:

| Feature | Goal | Interaction |
|---------|------|------------|
| **Knowledge** | Document knowledge base integration | Users upload → Agents bind → Prioritize documents |
| **Skills** | Reusable script library | Users upload → Agents invoke → Anthropic format |
| **Workflows** | Intelligent process orchestration | Agent cooperation → Same-project binding → Multi-step execution |

### 2. Knowledge (Knowledge Base Management)

#### 2.1 Architecture Design

- **Upload Pipeline**: File → Parse → Chunk → Embed → Vector Store
- **RAG Pipeline**: Query → Vector Search → Top-K → Feed to LLM Context
- **Storage**: PostgreSQL with pgvector extension
- **Embedding Model**: OpenAI text-embedding-3-small or local alternatives

#### 2.2 Key Features

- **Document Types**: PDF, DOCX, MD, TXT
- **Chunking**: Configurable chunk size and overlap
- **Similarity Search**: Top-K retrieval with threshold filtering
- **Agent Binding**: Multiple knowledge bases per Agent with priority levels
- **Async Processing**: Background tasks for parsing and embedding

### 3. Skills (Reusable Script Library)

#### 3.1 Architecture Design

```
Skill Folder Structure:
my-skill/
├── skill.yaml           # Metadata
├── README.md           # Documentation
├── src/
│   ├── main.py        # Entry point
│   └── utils.py
├── config/
│   └── default.json
└── tests/
```

#### 3.2 Key Features

- **Anthropic Standard**: Follows Anthropic skill definition format
- **Schema Validation**: Input/output JSON schema validation
- **Sandboxed Execution**: Docker or venv isolation
- **Version Control**: Semantic versioning support
- **Dependency Management**: Automatic pip install from requirements

### 4. Workflows (Agent to Agent Orchestration)

#### 4.1 Architecture Design

- **DAG Execution**: Topologically sorted step execution
- **Conditional Routing**: Route based on agent output
- **Parallel Execution**: Independent steps run concurrently
- **Result Aggregation**: Merge outputs into final answer
- **Same-Project Constraint**: All agents must be in same project

#### 4.2 Key Features

- **Template Variables**: `{{ step_name.output.field }}`
- **Error Handling**: Retry policies and error routing
- **Timeout Control**: Per-step and global limits
- **Observable Execution**: Detailed logs and intermediate results

#### 4.3 Example Workflow

Customer Support Flow:
1. **Classify** (Agent A) → Determine issue type and priority
2. **Route**: If high priority → escalate; if technical → resolve-technical; else → resolve-general
3. **Resolve** (Agent B/C) → Provide solution
4. **Aggregate**: Combine results into final response

---

### 5. Implementation Roadmap

- **Phase 1 (2 weeks)**: Knowledge base with RAG
- **Phase 2 (1.5 weeks)**: Skills framework
- **Phase 3 (2 weeks)**: Workflow orchestration engine

---

### 6. Technology Stack

| Component | Recommended | Alternative |
|-----------|------------|-----------|
| Vector DB | PostgreSQL + pgvector | Milvus |
| Embedding | OpenAI text-embedding-3-small | all-MiniLM-L6-v2 |
| Skill Execution | Docker | Python venv |
| Workflow Engine | Custom DAG + Celery | Airflow |
| Frontend Editor | Vue + Vis.js | React Flow |

---

### 7. 系统级建议和最佳实践

#### 7.1 权限和安全模型

**RBAC（基于角色的访问控制）**：
- **角色定义**：Admin / Operator / Viewer / Custom
- **粒度**：项目级、资源级、操作级
- **应用范围**：Knowledge / Skills / Workflows 都支持权限控制

**跨资源权限关联**：
- Agent 可以绑定哪些 Knowledge / Skills / MCPs
- 用户可以修改 / 删除哪些资源
- Workflow 中的 Agent 来自同一项目的权限验证

#### 7.2 成本管理和监控

**成本分类**：
```
1. LLM API 成本：LLM 服务调用
2. Embedding 成本：Knowledge 向量化
3. Skill 执行成本：计算资源（CPU / 内存）
4. Workflow 成本：多 Agent 协调的综合成本
```

**成本监控仪表板**：
- 按项目 / Agent / 资源类型的成本统计
- 实时成本预警
- 历史成本趋势分析
- 成本分配和结算

#### 7.3 性能和可观测性

**关键指标（KPI）**：
- Knowledge：平均检索时间、相关性得分、缓存命中率
- Skills：平均执行时间、成功率、资源使用率
- Workflows：平均流程时间、步骤成功率、Agent 响应时间

**追踪和日志**：
- 分布式追踪（OpenTelemetry）
- 结构化日志（JSON）
- 中央日志管理（ELK Stack 或类似）

**错误追踪和告警**：
- Sentry / 自定义错误追踪
- 实时告警系统
- 自动化问题诊断

#### 7.4 数据一致性和备份

**事务一致性**：
- Knowledge 文档更新的原子性
- Workflow 执行的事务隔离
- 确保中间结果不会丢失

**备份和恢复**：
- 定期备份数据库和 embedding 向量
- 支持时间点恢复（PITR）
- 灾难恢复计划（RTO / RPO）

#### 7.5 测试和质量保证

**单元测试**：
- Knowledge RAG 模块的单元测试
- Skill 沙箱执行的测试
- Workflow DAG 验证的测试

**集成测试**：
- Agent + Knowledge 的 RAG 流程
- Agent + Skill 的执行流程
- 多 Agent 协作 Workflow 的完整流程

**性能测试**：
- 大规模文档（Knowledge）的检索性能
- Skill 沙箱启动/关闭时间
- Workflow 并发执行能力

**用户验收测试（UAT）**：
- 端到端流程测试
- 边界情况测试
- 用户体验测试

#### 7.6 升级和兼容性

**版本兼容性**：
- Knowledge 文档版本向前兼容
- Skill 版本的语义化版本管理
- Workflow 定义版本升级路径

**平滑升级**：
- 在线升级（无停机）
- 灰度发布
- 自动回滚机制

#### 7.7 合规性和审计

**审计日志**：
- 记录所有重要操作（创建 / 修改 / 删除 / 执行）
- 操作者信息（用户 ID / IP 地址）
- 操作时间戳和详情

**数据隐私**：
- 敏感信息（Knowledge 文档、Skill 输出）的加密存储
- 访问日志
- 用户数据出口功能

**合规性报告**：
- 可生成审计报告
- 符合 GDPR / 行业规范

---

#### 7.8 开发者体验

**SDK 和 CLI**：
- Python / JavaScript SDK
- CLI 工具（快速上传 Knowledge / Skills）
- 本地开发和测试工具

**文档和示例**：
- 详细的 API 文档
- 最佳实践指南
- 常见场景示例代码

**社区**：
- Knowledge / Skills 市场
- 用户论坛
- GitHub 模板库

---

### 8. 优先级和风险管理

#### 优先级排序（P0 → P2）

**P0（必须有）**：
- [ ] Knowledge 基础 RAG 功能
- [ ] Skills 沙箱执行
- [ ] Workflows DAG 引擎

**P1（应该有）**：
- [ ] 混合搜索和相关性反馈
- [ ] Skill 市场和生态
- [ ] Workflow 版本控制和 A/B 测试
- [ ] 权限和审计日志

**P2（最好有）**：
- [ ] Human in the Loop
- [ ] 循环和递归支持
- [ ] 断点调试
- [ ] 模板库

#### 风险和缓解措施

| 风险 | 影响 | 可能性 | 缓解措施 |
|------|------|--------|---------|
| Embedding API 成本超支 | 高 | 中 | 成本监控告警、批量 API、本地模型选项 |
| Knowledge 数据泄露 | 高 | 低 | 加密存储、访问控制、审计日志 |
| Skill 沙箱突破 | 高 | 低 | 多层隔离、资源限制、安全审查 |
| Workflow 无限循环 | 中 | 中 | 迭代次数限制、超时控制、暂停功能 |
| 向量检索性能下降 | 中 | 中 | 缓存、批量优化、监控和告警 |

---

## 相关文档

- [Agent Framework Redesign](./agent-framework-redesign.zh-en.md)
- [Architecture Overview](../reference/architecture-roadmap.zh-en.md)
