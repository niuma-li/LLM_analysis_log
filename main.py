import os
import sys
import random  # 引入随机库

# 确保能找到 src 模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.preprocess_v2 import LogPreprocessor
from src.analysis import LogAnalyzer
from src.rca import RootCauseAnalyzer
from src.evaluate import Evaluator
# ================= 配置区 =================
# 是否开启随机采样？
ENABLE_SAMPLING = False
# 采样数量 (n)
SAMPLE_N = 50

def main():
    print("==========================================")
    print("   AI 系统日志智能分析与异常检测系统")
    print("==========================================")

    # 1. 数据预处理
    print("\n[Step 1] 数据预处理...")
    preprocessor = LogPreprocessor(dataset_dir="dataset")
    # 假设你的日志文件名叫 Linux_2k.log
    sysType = "Linux"
    logs = preprocessor.load_logs(filename="Linux_2k.log")
    # logs = preprocessor.load_logs(filename="Linux_2k.log_structured.csv")  # 结构化日志

    # 假设你的日志文件名叫 Android_2k.log
    # sysType = "Android"
    # logs = preprocessor.load_logs(filename="Android_2k.log")
    # logs = preprocessor.load_logs(filename="Android_2k.log_structured.csv")  # 结构化日志
    total_logs = len(logs)
    print(f"原始日志总数: {total_logs}")
    # for log in logs[:5]:
    #     print(log)

      # ---------------- 随机采样逻辑开始 ----------------
    target_line_ids = None  # 用于存储采样的 LineId 列表
    if ENABLE_SAMPLING and SAMPLE_N < total_logs:
        print(f"\n[Feature] 启用随机采样，抽取 {SAMPLE_N} 条记录...")
        
        # 1. 生成随机 LineId 数组 (范围 1 到 total_logs，不重复)
        # random.sample 用于无放回抽样
        target_line_ids = sorted(random.sample(range(1, total_logs + 1), SAMPLE_N))
        
        print(f"抽中的 LineId 数组 (前10个): {target_line_ids[:10]} ...")
        
        # 2. 根据 LineId 过滤 logs 列表
        # 注意：logs 列表通常下标是 0 到 len-1，而 LineId 是 1 到 len
        # 假设 logs[i] 的 LineId 就是 i+1 (如果在预处理中是按顺序生成的)
        # 更稳健的方法是遍历匹配：
        logs = [log for log in logs if log['LineId'] in target_line_ids]
        
        print(f"采样完成，当前待分析日志数: {len(logs)}")
    # ---------------- 随机采样逻辑结束 ----------------



    # 2. 核心分析 (LLM 推理)
    print("\n[Step 2] 启动 LLM 进行日志语义解析与异常检测...")
    # 为了测试快速运行，可以只取前 20 条进行测试
    # logs = logs[:20] 
    analyzer = LogAnalyzer(output_dir="outputs")
    analyzer.analyze(logs,sysType)
    
    # 3. 根因分析
    print("\n[Step 3] 执行异常根因分析 (RCA)...")
    rca = RootCauseAnalyzer(output_dir="outputs")
    rca.run_rca()

    # 4. 评估打分
    print("\n[Step 4] 评估结果 (对比标准答案)...")
    # evaluator = Evaluator(dataset_dir="dataset", output_dir="outputs",answer_file="Linux_answer2.csv")
    evaluator = Evaluator(dataset_dir="dataset", output_dir="outputs",sysType = sysType)
    # evaluator.evaluate()
    evaluator.evaluate(target_line_ids=target_line_ids)

    print("\n==========================================")
    print("   所有任务执行完毕。请查看 outputs/ 目录。")
    print("==========================================")

if __name__ == "__main__":
    main()

