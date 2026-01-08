import requests
import json

class OllamaService:
    def __init__(self, model_name="qwen2.5:3b", base_url="http://localhost:11434"):
        self.model_name = model_name
        self.api_url = f"{base_url}/api/chat"  # 【核心修改】改为 chat 接口

    def call_llm(self, prompt, system_prompt="", json_mode=True):
        """
        使用 Chat 接口调用 Ollama，模拟对话框体验
        """
        headers = {"Content-Type": "application/json"}
        
        # 构建消息历史
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.1,  # 保持低温，但不是绝对 0
                "top_p": 0.9,       # 增加一点点多样性采样
            }
        }

        # 【重要策略】
        # 对于 3B 小模型，建议先不强制开启 format='json'。
        # 让模型自然输出 JSON，我们在 Python 里解析。
        # 强制模式容易导致模型变笨。
        # if json_mode:
        #      payload["format"] = "json"

        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            # Chat 接口的返回结构与 Generate 不同
            return result.get("message", {}).get("content", "")

        except requests.exceptions.RequestException as e:
            print(f"[Error] LLM 调用失败: {e}")
            return None

if __name__ == "__main__":
    # 测试代码
    llm = OllamaService()
    print("正在测试 /api/chat 接口...")
    res = llm.call_llm("你好，请输出一个 JSON 格式的自我介绍", system_prompt="你是一个助手", json_mode=True)
    print("测试响应:", res)