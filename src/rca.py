import pandas as pd
import os
from src.llm_service import OllamaService

class RootCauseAnalyzer:
    def __init__(self, output_dir="outputs"):
        self.llm = OllamaService()
        self.output_dir = output_dir

    def run_rca(self, prediction_csv="System_Prediction.csv"):
        """
        读取预测结果，针对异常日志生成根因分析报告
        """
        file_path = os.path.join(self.output_dir, prediction_csv)
        if not os.path.exists(file_path):
            print("未找到预测结果文件，跳过 RCA。")
            return

        df = pd.read_csv(file_path)
        
        # 筛选出 EventCategory 不是 "Other" 的异常日志
        anomalies = df[df['EventCategory'] != 'Other']
        
        if anomalies.empty:
            print("未检测到异常日志，无需进行根因分析。")
            return

        print(f"检测到 {len(anomalies)} 条异常日志，开始生成根因分析报告...")
        
        report_lines = ["# 系统日志根因分析报告 (Root Cause Analysis)\n"]
        
        # 为了演示，只分析前 5 条异常，避免等待时间过长
        target_logs = anomalies.head(5) 

        for _, row in target_logs.iterrows():
            log_content = row['Content']
            category = row['EventCategory']
            
            prompt = f"""
这是一条被检测为 "{category}" 的系统异常日志：
"{log_content}"

请简要分析：
1. 可能的根本原因 (Root Cause)
2. 推荐的排查或修复步骤
请以纯文本列表形式回答，不要 markdown 代码块。
"""
            analysis = self.llm.call_llm(prompt, json_mode=False)
            
            report_item = f"## Log ID: {row['LineId']}\n" \
                          f"**日志内容**: `{log_content}`\n" \
                          f"**异常类型**: {category}\n" \
                          f"**分析结果**: \n{analysis}\n" \
                          f"---\n"
            report_lines.append(report_item)
            print(f"已分析 Log ID {row['LineId']}")

        # 保存报告
        report_path = os.path.join(self.output_dir, "RCA_Report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.writelines(report_lines)
        
        print(f"根因分析报告已生成: {report_path}")