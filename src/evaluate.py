import pandas as pd
import os
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

class Evaluator:
    def __init__(self, dataset_dir="dataset", output_dir="outputs", answer_file="Linux_answer2.csv"):
        self.dataset_dir = dataset_dir
        self.output_dir = output_dir
        self.answer_file = answer_file
        # 定义中间桥梁文件名称
        self.bridge_file = "Linux_2k.log_structured.csv" 

    def evaluate(self, target_line_ids=None):
        """
        target_line_ids: 数组或列表，指定要评估的 LineId。如果是 None 则评估全部。
        """
        # 1. 路径准备
        answer_path = os.path.join(self.dataset_dir, self.answer_file)
        bridge_path = os.path.join(self.dataset_dir, self.bridge_file)
        pred_path = os.path.join(self.output_dir, "System_Prediction.csv")

        # 检查文件是否存在
        for p in [answer_path, bridge_path, pred_path]:
            if not os.path.exists(p):
                print(f"[错误] 找不到文件: {p}")
                return

        # 2. 安全读取数据 (解决你之前遇到的 ParserError 和 编码问题)
        def safe_read(path, is_answer=False):
            read_params = {
                'on_bad_lines': 'warn', 
                'engine': 'python',      # Python引擎处理复杂引号和逗号更稳健
                'quotechar': '"'
            }
            try:
                df = pd.read_csv(path, encoding='utf-8', **read_params)
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding='gbk', **read_params)
            
            # 清洗列名
            df.columns = df.columns.str.strip()
            return df

        df_answer = safe_read(answer_path, is_answer=True)
        df_bridge = safe_read(bridge_path)
        df_pred = safe_read(pred_path)

        # 3. 数据过滤 (新增逻辑：如果指定了 target_line_ids)
        if target_line_ids is not None:
            # 确保输入是列表格式
            if not isinstance(target_line_ids, list):
                target_line_ids = list(target_line_ids)
            
            # 仅保留指定的 LineId 样本
            df_pred = df_pred[df_pred['LineId'].isin(target_line_ids)]
            
            if df_pred.empty:
                print(f"[警告] 指定的 target_line_ids 在预测文件中未找到任何匹配。")
                return
            print(f"[信息] 已筛选指定样本，评估数量: {len(df_pred)}")

        # 4. 数据对齐 (核心逻辑)
        try:
            # 第一步：通过 bridge 文件给预测结果加上 EventId
            df_pred_with_id = pd.merge(
                df_pred, 
                df_bridge[['LineId', 'EventId']], 
                on="LineId"
            )

            # 第二步：通过 EventId 关联标准答案中的类别
            # 仅取答案中需要的列，防止合并产生冗余
            df_merged = pd.merge(
                df_pred_with_id, 
                df_answer[['EventId', 'SemanticClass', 'EventCategory']], 
                on="EventId", 
                suffixes=('_pred', '_true')
            )
        except KeyError as e:
            print(f"[错误] 文件中缺少必要的列: {e}")
            return

        if df_merged.empty:
            print("[错误] 数据合并后为空，请检查对齐字段（LineId/EventId）。")
            return

        # 5. 执行对比逻辑
        print(f"------ 评测结果 (样本数: {len(df_merged)}) ------")
        
        # 统一格式：转为字符串并去除空格，防止匹配失败
        for col in ['SemanticClass_true', 'SemanticClass_pred', 'EventCategory_true', 'EventCategory_pred']:
            df_merged[col] = df_merged[col].astype(str).str.strip()

        # 1. 语义分类准确率
        acc_semantic = accuracy_score(df_merged['SemanticClass_true'], df_merged['SemanticClass_pred'])
        print(f"1. 语义分类准确率 (Accuracy): {acc_semantic:.2%}")

        # 2. 异常检测指标
        y_true = df_merged['EventCategory_true']
        y_pred = df_merged['EventCategory_pred']
        
        acc_anomaly = accuracy_score(y_true, y_pred)
        print(f"2. 异常检测整体准确率 (Accuracy): {acc_anomaly:.2%}")
        
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average='macro', zero_division=0
        )
        print(f"3. 异常检测 Macro-F1: {f1:.2f}")

        # 6. 得分计算逻辑 (基于比例)
        score = 0
        if acc_semantic >= 0.80: score += 30
        else: score += (acc_semantic / 0.80) * 30
        
        if acc_anomaly >= 0.75: score += 25
        else: score += (acc_anomaly / 0.75) * 25
        
        print(f"------ 预估得分: {score:.1f} / 55.0 ------")
        
        # 保存对比细节
        detail_path = os.path.join(self.output_dir, "Evaluation_Details_Filtered.csv")
        df_merged.to_csv(detail_path, index=False)
        print(f"[提示] 详细分析已保存至: {detail_path}")