# LLM_analysis_log
UCAS OS大作业
------------------------------------------------------------------------------------------------
##数据集构建
对公开数据集loghub根据RFC 5424 (Syslog Protocol) 定义的 Facility 标准以及 NIST SP 800-92 (计算机安全日志管理指南)，将提供的 118 个日志模板归纳为以下 7 个核心语义类别和3个异常类别。 
##模型
选用qwen2.5:3b轻量化模型，采用ollama本地部署。
##项目结构
Log_LLM_Project/
│
├── dataset/                    # [输入] 原始 CSV
│   ├── Linux_2k.log            
|   ├── Linux_2k.log_struct.csv
|   ├── Linux_2k.log_template.csv
|   ├── Linux_answer2.csv
│   └── 
│
├── src/
│   ├── analysis.py             # 日志分析(语义类别和异常识别)
│   ├── evaluate.py             # 结果评估
│   ├── llm_service.py          # LLM模块
│   ├── preprocess.py           # 数据预处理
│   └── rca.py                  # 根因分析
│
└── main.py                     # 程序入口
