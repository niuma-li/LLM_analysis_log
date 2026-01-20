import pandas as pd
import os
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

class Evaluator:
    def __init__(self, dataset_dir="dataset", output_dir="outputs",sysType = "sysType", answer_file="Linux_answer.csv"):
        self.dataset_dir = dataset_dir
        self.output_dir = output_dir
        # 定义中间桥梁文件名称 (根据你的实际情况取消注释/修改)
        if sysType == "Linux":
            self.bridge_file = "Linux_2k.log_structured.csv"
            self.answer_file = "Linux_answer.csv"
        else:
        # self.bridge_file = "Linux_2k.log_structured.csv" 
            self.bridge_file = "Android_2k.log_structured.csv"
            self.answer_file = "Android_answer.csv" 

    def _safe_read(self, path):
        """内部方法：安全读取 CSV，处理编码和坏行"""
        read_params = {
            'on_bad_lines': 'warn', 
            'engine': 'python',
            'quotechar': '"',
            'dtype': str  # 默认全读为字符串，防止ID被当成数字处理导致匹配问题
        }
        try:
            df = pd.read_csv(path, encoding='utf-8', **read_params)
        except UnicodeDecodeError:
            df = pd.read_csv(path, encoding='gbk', **read_params)
        
        # 清洗列名：去除列名中的前后空格
        df.columns = df.columns.str.strip()
        return df

    def _clean_series(self, series):
        """内部方法：标准化序列，转字符串并去除前后空格"""
        return series.astype(str).str.strip()

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

        # 2. 读取数据
        df_answer = self._safe_read(answer_path)
        df_bridge = self._safe_read(bridge_path)
        df_pred = self._safe_read(pred_path)
            
        # 3. 关键优化：在合并前清洗 ID 列，防止因空格导致 Merge 失败
        # 统一将关联键处理为 "字符串且无空格"
        df_pred['LineId'] = self._clean_series(df_pred['LineId'])
        df_bridge['LineId'] = self._clean_series(df_bridge['LineId'])
        df_bridge['EventId'] = self._clean_series(df_bridge['EventId'])
        df_answer['EventId'] = self._clean_series(df_answer['EventId'])

        # 4. 数据过滤
        if target_line_ids is not None:
            if not isinstance(target_line_ids, list):
                target_line_ids = list(target_line_ids)
            
            # 确保输入的 IDs 也是清洗过的字符串格式，以便匹配
            target_line_ids = [str(x).strip() for x in target_line_ids]
            
            df_pred = df_pred[df_pred['LineId'].isin(target_line_ids)]
            
            if df_pred.empty:
                print(f"[警告] 指定的 target_line_ids 在预测文件中未找到任何匹配。")
                return
            print(f"[信息] 已筛选指定样本，评估数量: {len(df_pred)}")

        # 5. 数据对齐
        try:
            # 第一步：Pred -> Bridge (LineId)
            df_pred_with_id = pd.merge(
                df_pred, 
                df_bridge[['LineId', 'EventId']], 
                on="LineId",
                how='inner' # 使用 inner 确保只有匹配上的才参与评估
            )

            # 第二步：Result -> Answer (EventId)
            df_merged = pd.merge(
                df_pred_with_id, 
                df_answer[['EventId', 'SemanticClass', 'EventCategory']], 
                on="EventId", 
                suffixes=('_pred', '_true'),
                how='inner'
            )
        except KeyError as e:
            print(f"[错误] 文件中缺少必要的列: {e}")
            return

        if df_merged.empty:
            print("[错误] 数据合并后为空。请检查 LineId 或 EventId 是否匹配（已自动去除空格）。")
            return

        # 6. 执行对比逻辑（核心优化点）
        print(f"------ 评测结果 (样本数: {len(df_merged)}) ------")
        
        # 定义需要对比的列对
        cols_to_compare = [
            ('SemanticClass_true', 'SemanticClass_pred'),
            ('EventCategory_true', 'EventCategory_pred')
        ]

        # 统一清洗这些列：转字符串 -> 去除首尾空格
        # 注意：这里我们处理了 'nan' 的情况，将其视为空字符串或保持 'nan' 字符串均可，只要统一即可
        for true_col, pred_col in cols_to_compare:
            df_merged[true_col] = self._clean_series(df_merged[true_col])
            df_merged[pred_col] = self._clean_series(df_merged[pred_col])

        # 7. 计算指标
        
        # 指标 1: 语义分类
        y_sem_true = df_merged['SemanticClass_true']
        y_sem_pred = df_merged['SemanticClass_pred']
        acc_semantic = accuracy_score(y_sem_true, y_sem_pred)
        print(f"1. 语义分类准确率 (Accuracy): {acc_semantic:.2%}")

        # 指标 2: 异常检测
        y_cat_true = df_merged['EventCategory_true']
        y_cat_pred = df_merged['EventCategory_pred']
        
        acc_anomaly = accuracy_score(y_cat_true, y_cat_pred)
        print(f"2. 异常检测整体准确率 (Accuracy): {acc_anomaly:.2%}")
        
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_cat_true, y_cat_pred, average='macro', zero_division=0
        )
        print(f"3. 异常检测 Macro-F1: {f1:.2f}")

        # 8. 得分计算逻辑
        score = 0
        # 语义分 (满分30)
        if acc_semantic >= 0.80: 
            score += 30
        else: 
            score += (acc_semantic / 0.80) * 30
        
        # 异常检测分 (满分25)
        if acc_anomaly >= 0.75: 
            score += 25
        else: 
            score += (acc_anomaly / 0.75) * 25
        
        print(f"------ 预估得分: {score:.1f} / 55.0 ------")
        
        # 保存对比细节
        detail_path = os.path.join(self.output_dir, "Evaluation_Details_Filtered.csv")
        # 添加一列标记是否正确，方便查看
        df_merged['is_semantic_correct'] = (df_merged['SemanticClass_true'] == df_merged['SemanticClass_pred'])
        df_merged['is_anomaly_correct'] = (df_merged['EventCategory_true'] == df_merged['EventCategory_pred'])
        
        df_merged.to_csv(detail_path, index=False)
        print(f"[提示] 详细分析已保存至: {detail_path}")

# 使用示例
if __name__ == "__main__":
    # 实例化
    evaluator = Evaluator()
    
    # 运行评估 (None 表示评估所有)
    evaluator.evaluate(target_line_ids=None)
