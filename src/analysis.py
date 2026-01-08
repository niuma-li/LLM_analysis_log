import json
import pandas as pd
from tqdm import tqdm
import os
from src.llm_service import OllamaService

class LogAnalyzer:
    def __init__(self, output_dir="outputs"):
        self.llm = OllamaService()
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def _build_prompt_semantic(self, log_content):
        """任务 1: 语义分类"""
        return f"""你是一个Linux操作系统日志分析专家。请分析以下日志的语义，根据分析结果选择合适的类别：
"{log_content}"


类别解释如下：
Authentication & Security (认证与安全):涉及用户登录（SSH/FTP）、权限验证、PAM 模块、SELinux 审计等事件。
Hardware & Device Drivers (硬件与设备驱动):涉及 CPU、PCI 总线、USB 设备、磁盘及其他外设的物理检测与驱动加载。
Memory Management (内存管理):涉及物理内存（RAM）的分配、虚拟内存映射、缓存（Cache）统计及内存区域（Zone）管理。
Network & Connectivity (网络与连接):涉及网络接口（Interface）状态、协议栈初始化、IP 地址分配及底层网络通讯记录。
System Services & Daemons (系统服务与守护进程):涉及后台服务（如 crond, cupsd, syslogd, sshd）的启动、停止及运行状态报告。
Power Management (电源管理):涉及 ACPI（高级配置与电源接口）、APM 及 BIOS 电源管理表的解析与交互。
Kernel Boot & General System (内核引导与通用系统状态):涉及 Linux 内核版本信息、启动命令行参数、文件系统配额（VFS）及通用生命周期事件。

请直接输出 JSON，格式如：{{"SemanticClass": "类别名称"}}
不要包含任何解释或 Markdown 标记。"""

    def _build_prompt_category(self, log_content):
        """任务 2: 异常类型判断"""
        return f"""你是一个擅长推理分析的Linux操作系统日志分析专家。请分析以下日志是否属于异常日志并给出理由，根据你的理由选择最合适的类别：
"{log_content}"

请根据逻辑判断：
- 如果是用户无法通过身份验证、权限不足或非法的访问尝试，输出 "Authentication & Security Failures"
- 如果是硬件过时、BIOS 配置错误、资源表无效或内核子系统初始化失败，输出 "Hardware & Kernel Config Errors"
- 如果是运行时的服务不可达、连接非正常断开或响应超时，通常影响服务的可用性，输出 "Service Communication & Timeout Exceptions"
- 如果是正常日志或不属于以上异常，必须输出 "Other"

请直接输出 JSON，格式如：{{"Normal":"True or False","Reason":”理由“"EventCategory": "类别名称"}}
不要包含任何解释或 Markdown 标记。"""

    def analyze(self, logs):
        """
        遍历日志列表，分别为任务 1 和任务 2 调用 LLM
        """
        results = []
        print(f"开始分析 {len(logs)} 条日志 (使用 Qwen2.5:3b)...")

        for log in tqdm(logs, desc="LLM Analyzing"):
            log_text = log['CleanedContent']
            
            # --- 第一次调用：获取 SemanticClass ---
            prompt_s = self._build_prompt_semantic(log_text)
            resp_s = self.llm.call_llm(prompt_s, json_mode=True)
            semantic_class = "Kernel Boot & General System" # 默认值
            if resp_s:
                try:
                    data_s = json.loads(resp_s)
                    semantic_class = data_s.get("SemanticClass", semantic_class)
                except json.JSONDecodeError:
                    pass

            # --- 第二次调用：获取 EventCategory ---
            prompt_c = self._build_prompt_category(log_text)
            resp_c = self.llm.call_llm(prompt_c, json_mode=True)
            event_category = "Other" # 默认值
            if resp_c:
                try:
                    data_c = json.loads(resp_c)
                    event_category = data_c.get("EventCategory", event_category)
                except json.JSONDecodeError:
                    pass

            # 合并结果（保持输出格式不变）
            results.append({
                "LineId": log['LineId'],
                "Content": log['Content'], 
                "SemanticClass": semantic_class,
                "EventCategory": event_category
            })

        # 保存为 CSV
        output_path = os.path.join(self.output_dir, "System_Prediction.csv")
        df = pd.DataFrame(results)
        df.to_csv(output_path, index=False)
        print(f"分析完成，预测结果已保存至: {output_path}")
        return df