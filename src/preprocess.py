import re
import pandas as pd
import os

class LogPreprocessor:
    def __init__(self, dataset_dir="dataset"):
        self.dataset_dir = dataset_dir

    def mask_content(self, content):
        """
        数据清洗与脱敏：将具体参数替换为通用占位符
        """
        if not isinstance(content, str):
            return ""
        
        # 1. 替换 IP 地址
        content = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '<IP>', content)
        # 2. 替换 十六进制数字
        content = re.sub(r'0x[0-9a-fA-F]+', '<HEX>', content)
        # 3. 替换 纯数字
        content = re.sub(r'\b\d+\b', '<NUM>', content)
        # 4. 替换 路径
        content = re.sub(r'\/[\w\/\.-]+', '<PATH>', content)
        
        return content

    def parse_log_line(self, line, line_id):
        """
        解析原始 Linux Log 格式: Month Date Time Host Component[PID]: Content
        """
        log_pattern = re.compile(r'^([A-Z][a-z]{2}\s+\d+\s\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^:]+):\s+(.*)$')
        match = log_pattern.match(line.strip())
        
        if match:
            timestamp = match.group(1)
            component_raw = match.group(3)
            content = match.group(4)
            component = re.split(r'\[|:', component_raw)[0]
            
            return {
                "LineId": line_id,
                "Timestamp": timestamp,
                "Component": component,
                "Content": content,
                "CleanedContent": self.mask_content(content)
            }
        else:
            return {
                "LineId": line_id,
                "Timestamp": "Unknown",
                "Component": "Unknown",
                "Content": line.strip(),
                "CleanedContent": self.mask_content(line.strip())
            }

    def load_logs(self, filename="Linux_2k.log"):
        """
        读取日志文件（支持 .log 和 .csv）并转换为标准化列表
        """
        file_path = os.path.join(self.dataset_dir, filename)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件未找到: {file_path}")

        print(f"正在处理文件: {filename} ...")
        structured_logs = []

        # 获取文件后缀
        _, file_extension = os.path.splitext(filename)

        if file_extension.lower() == '.csv':
            # 处理 CSV 文件
            df = pd.read_csv(file_path)
            for _, row in df.iterrows():
                # 拼接 Timestamp: Month Date Time
                timestamp = f"{row['Month']} {row['Date']:02d} {row['Time']}"
                
                structured_logs.append({
                    "LineId": int(row['LineId']),
                    "Timestamp": timestamp,
                    "Component": str(row['Component']),
                    "Content": str(row['Content']),
                    "CleanedContent": self.mask_content(str(row['Content']))
                })
        else:
            # 处理标准 .log 文件
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for idx, line in enumerate(f):
                    if not line.strip(): continue
                    log_obj = self.parse_log_line(line, line_id=idx + 1)
                    structured_logs.append(log_obj)
                
        print(f"预处理完成，共处理 {len(structured_logs)} 条日志。")
        return structured_logs

if __name__ == "__main__":
    # 使用示例
    processor = LogPreprocessor(dataset_dir=".") 
    
    # 测试 CSV 加载 (根据你提供的样例)
    # logs = processor.load_logs("Linux_2k.csv")
    # if logs: print(logs[0])