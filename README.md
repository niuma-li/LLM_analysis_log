# LLM_analysis_log
UCAS OS大作业
------------------------------------------------------------------------------------------------
## 数据集构建
对公开数据集loghub根据RFC 5424 (Syslog Protocol) 定义的 Facility 标准以及 NIST SP 800-92 (计算机安全日志管理指南)，将提供的 118 个日志模板归纳为以下 7 个核心语义类别和3个异常类别。 
## 模型
选用qwen2.5:3b轻量化模型，采用ollama本地部署。  
## 运行方式
ollama serve 
python main.py

## 简介
这是一个非常典型的**AIOps（智能运维）**实验项目。我们需要设计一个模块化、高内聚低耦合的系统架构。

系统架构设计方案如下：

---

### 系统总体架构图 (概念)

系统分为四个核心层级：
1.  **数据接入与预处理层 (Data Ingestion & Preprocessing)**
2.  **大模型推理服务层 (LLM Inference Service)**
3.  **核心业务逻辑层 (Core Logic: Analysis & Detection)**
4.  **评估与展示层 (Evaluation & Visualization)**

---

### 详细模块设计

#### 1. 数据预处理模块 (Data Preprocessing Module)
**任务**：负责读取不同格式的日志文件，清洗噪声，统一数据结构，为后续分析做准备。

*   **输入**：
    *   `.log` 文件（原始Linux Syslog，非结构化文本）
    *   `.csv` 文件（已结构化，包含 LineId, Month, Date, Time, Level, Component, PID, Content...）
*   **处理流程**：
    1.  **格式适配**：
        *   针对 `.csv`：直接读取 Pandas DataFrame。
        *   针对 `.log`：使用 Regex（正则表达式）解析出 时间戳、日志级别、组件名、PID、日志内容，将其转换为与 CSV 相同的结构。
    2.  **数据清洗**：
        *   去除非 ASCII 字符。
        *   掩码处理（Masking）：将 IP 地址、具体数字、文件路径替换为通用占位符（如 `<IP>`, `<NUM>`, `<PATH>`），以便提取 `EventTemplate`。
    3.  **标准化**：统一输出为 JSON 对象列表或标准 DataFrame。
*   **输出**：
    *   `Standardized_Logs` (包含字段: Timestamp, Level, Component, Content, CleanedContent)

#### 2. 轻量级大模型服务模块 (LLM Service Module)
**任务**：加载量化后的轻量级模型（Qwen-tiny 或 ChatGLM-6B-int4），提供基础的语义理解接口。此模块不处理具体业务，只负责“文本进，文本/向量出”。

*   **输入**：
    *   Prompt（提示词）
    *   待分析的日志文本
*   **功能**：
    1.  **模型加载**：本地加载 HuggingFace 模型权重。
    2.  **推理接口**：提供 `generate_response(prompt)` 函数。
*   **输出**：
    *   LLM 生成的文本结果（用于分类、关键词提取、RCA）。

#### 3. 日志语义解析模块 (Semantic Parsing Module)
**任务**：调用 LLM 对标准化后的日志进行深度解析，提取关键信息并填补 `Linux_answer.csv` 中所需的字段。

*   **输入**：
    *   `Standardized_Logs` (来自模块 1)
*   **处理流程**：
    1.  **EventTemplate 提取**：利用聚类算法（如 Drain）或 LLM 少样本学习（Few-shot）生成日志模板。
    2.  **关键词提取**：构造 Prompt 让 LLM 提取日志中的实体（如 "CPU", "SegFault", "Network"）。
    3.  **语义分类 (SemanticClass)**：构造 Prompt 让 LLM 将日志归类（例如：ConfigError, NetworkIssue, ResourceExhaustion）。
    4.  **零样本识别**：对于未见过的日志，利用 LLM 的泛化能力自动打标。
*   **输出**：
    *   `Parsed_Logs` (新增字段: Keywords, EventTemplate, SemanticClass, EventCategory)
    *   *注：此输出结构对应 `Linux_anwser.csv` 的要求。*

#### 4. 异常检测与预测模块 (Anomaly Detection & Prediction Module)
**任务**：结合规则和 LLM 语义判断日志是否异常，并预测未来风险（针对附件题）。

*   **输入**：
    *   `Parsed_Logs` (含语义标签)
*   **处理流程**：
    1.  **规则匹配 (Rule-based)**：
        *   检测 `Level` 字段是否为 ERROR/FATAL。
        *   检测关键词（如 "Failed", "Refused"）。
    2.  **语义异常检测 (LLM-based)**：
        *   将日志输入 LLM，询问：“这条日志是否表示系统处于不健康状态？(Yes/No)”
        *   计算语义向量距离（如果模型支持 Embedding），检测偏离正常模式的日志。
    3.  **故障预测 (Bonus Task)**：
        *   基于滑动窗口（Sliding Window），输入过去 N 条日志的 `EventCategory` 序列，让 LLM 预测下一条可能发生的错误类型。
*   **输出**：
    *   `Anomaly_Report` (包含: LogID, IsAnomaly, AnomalyType, ConfidenceScore)
    *   `Prediction_Result` (下一时刻可能的故障类型)

#### 5. 根因分析模块 (Root Cause Analysis Module)
**任务**：针对被检测为“异常”的日志，生成人类可读的解释。

*   **输入**：
    *   异常日志内容
    *   该日志前后的上下文日志（Context Window）
*   **处理流程**：
    *   构造 Prompt：“基于以下系统日志上下文，分析发生错误的根本原因，并给出修复建议。”
    *   调用模块 2 获取答案。
*   **输出**：
    *   `RCA_Report` (Markdown 格式的分析文本)

#### 6. 评估模块 (Evaluation Module) —— 实验专用
**任务**：计算实验得分，对比模型输出与标准答案。

*   **输入**：
    *   系统生成的分类结果 (`SemanticClass`, `EventCategory`)
    *   检测到的异常列表
    *   `Linux_anwser.csv` (标准答案/真值)
*   **处理流程**：
    *   计算语义分类准确率 (Accuracy)。
    *   计算异常检测的精确率 (Precision), 召回率 (Recall), F1-Score。
*   **输出**：
    *   `Experiment_Report` (包含各阶段准确率指标)

---

### 数据流向示例 (Data Pipeline)

假设一条原始日志：
`Dec 21 10:22:01 server sshd[1234]: Failed password for invalid user admin from 192.168.1.1`

1.  **模块 1 (预处理)**:
    *   提取: Time=`Dec 21 10:22:01`, Component=`sshd`, Content=`Failed password for invalid user admin from 192.168.1.1`
    *   清洗: Content_Cleaned=`Failed password for invalid user admin from <IP>`

2.  **模块 3 (语义解析)**:
    *   LLM Input: "提取关键词并分类: Failed password..."
    *   Result: Keywords=`[Failed password, invalid user]`, SemanticClass=`Authentication`, EventCategory=`Security`
    *   生成 EventTemplate: `Failed password for invalid user * from *`

3.  **模块 4 (异常检测)**:
    *   规则: 命中关键词 "Failed"。
    *   LLM: 判定为 "Security Breach Attempt"。
    *   结果: IsAnomaly=True, Type=PermissionError。

4.  **模块 5 (根因分析)**:
    *   LLM Input: "为什么出现此错误？"
    *   Output: "根本原因是外部IP尝试使用无效账户'admin'进行暴力破解。"

