import re
import pandas as pd
import os

class LogPreprocessor:
    def __init__(self, dataset_dir="dataset"):
        self.dataset_dir = dataset_dir
        # 原有 Linux 正则
        self.linux_pattern = re.compile(r'^([A-Z][a-z]{2}\s+\d+\s\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^:]+):\s+(.*)$')
        # 新增 Android Logcat 正则: Date Time PID TID Level Component: Content
        # 示例: 03-17 16:13:38.811  1702  2395 D WindowManager: print...
        self.android_pattern = re.compile(r'^(\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+(\d+)\s+([A-Z])\s+([^:]+):\s+(.*)$')

    def mask_content(self, content):
        """数据清洗与脱敏"""
        if not isinstance(content, str):
            return ""
        content = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '<IP>', content)
        content = re.sub(r'0x[0-9a-fA-F]+', '<HEX>', content)
        content = re.sub(r'\b\d+\b', '<NUM>', content)
        content = re.sub(r'\/[\w\/\.-]+', '<PATH>', content)
        return content

    def parse_log_line(self, line, line_id):
        """解析原始 Log 格式，支持 Linux 和 Android"""
        line = line.strip()
        
        # 尝试匹配 Android 格式
        android_match = self.android_pattern.match(line)
        if android_match:
            ts, pid, tid, level, comp, cont = android_match.groups()
            return {
                "LineId": line_id,
                "Timestamp": ts,
                "Pid": pid,
                "Tid": tid,
                "Level": level,
                "Component": comp,
                "Content": cont,
                "CleanedContent": self.mask_content(cont)
            }

        # 尝试匹配 Linux 格式
        linux_match = self.linux_pattern.match(line)
        if linux_match:
            ts, host, comp, cont = linux_match.groups()
            return {
                "LineId": line_id,
                "Timestamp": ts,
                "Host": host,
                "Component": comp,
                "Content": cont,
                "CleanedContent": self.mask_content(cont)
            }

        # 如果都匹配不上，确保基础字段存在
        return {
            "LineId": line_id,
            "Timestamp": "Unknown",
            "Content": line,
            "CleanedContent": self.mask_content(line)
        }

    def load_logs(self, filename):
        file_path = os.path.join(self.dataset_dir, filename)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件未找到: {file_path}")

        print(f"正在处理文件: {filename} ...")
        structured_logs = []
        _, file_extension = os.path.splitext(filename)

        if file_extension.lower() == '.csv':
            df = pd.read_csv(file_path)
            # 将列名统一转为小写或检查存在性以提高兼容性
            cols = df.columns.tolist()
            
            for _, row in df.iterrows():
                # 动态构建 Timestamp
                if 'Month' in row and 'Date' in row:
                    # Linux 格式 CSV
                    timestamp = f"{row['Month']} {row['Date']:02d} {row['Time']}"
                else:
                    # Android 格式 CSV (直接使用 Date 列)
                    timestamp = f"{row.get('Date', 'Unknown')} {row.get('Time', 'Unknown')}"
                
                # 构建基础字典
                log_entry = {
                    "LineId": int(row['LineId']),
                    "Timestamp": timestamp,
                    "Component": str(row.get('Component', 'Unknown')),
                    "Content": str(row['Content']),
                    "CleanedContent": self.mask_content(str(row['Content']))
                }
                
                # 保留 Android 特有的 Level, Pid, Tid (如果存在)
                for extra in ['Level', 'Pid', 'Tid']:
                    if extra in row:
                        log_entry[extra] = row[extra]
                        
                structured_logs.append(log_entry)
        else:
            # 处理 .log 文件
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for idx, line in enumerate(f):
                    if not line.strip(): continue
                    log_obj = self.parse_log_line(line, line_id=idx + 1)
                    structured_logs.append(log_obj)
                
        print(f"预处理完成，共处理 {len(structured_logs)} 条日志。")
        return structured_logs

if __name__ == "__main__":
    # processor = LogPreprocessor(dataset_dir=".") # 假设当前目录下

    # print(logs[0])
    processor = LogPreprocessor(dataset_dir="dataset") 
        # 测试 Android CSV
    # logs = processor.load_logs("Android_2k.log_structured.csv")
    # logs = processor.load_logs("Linux_2k.log_structured.csv")
    # 测试 CSV 加载 (根据你提供的样例)
    logs = processor.load_logs("Android_2k.log")
    # logs = processor.load_logs("Linux_2k.log")
    print(logs[0]['Content'])
    print(logs[0]['Component'])
    print("==============================")
    print(logs[1]['Content'])
    print(logs[1]['Component'])
