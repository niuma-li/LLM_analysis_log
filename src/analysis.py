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

    def _build_prompt_semantic_Linux(self, log_content,Component,sysType):
        """任务 1: 语义分类"""
        return f"""你是一个{sysType}操作系统日志分析专家。请分析以下日志的语义，根据分析结果选择合适的类别：
"{Component} {log_content}"


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
    
    def _build_prompt_semantic_Android(self, log_content,Component,sysType):
        """任务 1: 语义分类"""
        return f"""你是一个{sysType}操作系统日志分析专家。请仔细阅读以下日志内容，并根据严格的定义将其分类到一个最准确的语义类别中。

日志内容：
"{Component}{log_content}"

请严格遵循以下分类定义和**消歧规则**（优先级由高到低）：

1. **Authentication & Security** (认证与安全):
   - **核心定义**：涉及权限控制、身份验证、签名、锁屏安全或操作拦截。
   - **关键特征**：permission, denied, blocked, allowed, UID/PID check, signature, keyguard, password, pin, "shouldBlockLocation", "Real_GET_TASKS", "AppOps".
   - **消歧规则**：如果日志是关于“检查是否允许某事做某事”（如 `shouldBlockLocation` 或 `does not hold REAL_GET_TASKS`），即使由 SystemServer 打印，必须归为此类。

2. **Power Management** (电源管理):
   - **核心定义**：涉及电池、充电、系统休眠/唤醒、屏幕亮度调节（Brightness）及核心唤醒锁。
   - **关键特征**：WakeLock, "acquire lock" (仅限电源锁), "release lock" (仅限电源锁), battery, charge, suspend, "screen on", "screen off", "Animating brightness", "HBM brightness".
   - **消歧规则**：
     - 注意：`View Lock` 或 `WindowManager Lock` **属于 System Services**，不属于电源管理。
     - 仅当锁的 tag 涉及 `WakeLocks`、`PowerManagerService` 或 `RILJ_ACK_WL` 时才归为此类。

3. **Network & Connectivity** (网络与连接):
   - **核心定义**：涉及移动网络、Wi-Fi、蓝牙及相关Intent广播。
   - **关键特征**：Telephony, CellInfo, RIL, Wifi, Bluetooth, SignalStrength, APN, data connection, SimPin.
   - **消歧规则**：涉及 Intent 为 `CHOOSE_SUB` (订阅选择) 的日志归为此类。

4. **Hardware & Device Drivers** (硬件与设备驱动):
   - **核心定义**：涉及物理硬件的底层交互（音频流、灯光控制、物理按键值）。
   - **关键特征**：Audio (StreamVolume, Speaker), Light/LED (setLightsOn), Sensor, Vibration, Keycode (物理按键值).
   - **消歧规则**：
     - **严禁**将图形界面的绘制、裁剪（Clipping）、触摸坐标分发（Input Dispatching）归为此类。
     - `updateLightsLocked` 归为 Hardware，因为涉及物理灯光控制。

5. **Kernel Boot & General System** (内核引导与通用系统状态):
   - **核心定义**：涉及系统时钟、启动/关机流程、文件系统。
   - **关键特征**：Boot, shutdown, kernel version, "time tick", "time update", "TIME_TICK alarm".
   - **消歧规则**：所有涉及 `TimeTick` 或 `handleTimeUpdate` 的日志均归为此类。

6. **Memory Management** (内存管理):
   - **核心定义**：涉及内存分配、回收和OOM。
   - **关键特征**：OOM, GC, heap, alloc, free, memory leak, lowmemorykiller.
   - **消歧规则**：不要将 UI 的 "Translation"（位移）或 "Clip"（裁剪）误判为内存操作。

7. **System Services & Daemons** (系统服务与守护进程):
   - **核心定义**：涉及窗口管理（WMS）、Activity管理（AMS）、UI绘制逻辑、通知管理（NMS）及进程生命周期。
   - **关键特征**：
     - **窗口/UI**：Surface, Clipping, Overlap, Translation, Dimmed, "setSystemUiVisibility", "notifyUiVisibilityChanged", "destroySurface".
     - **输入/触摸**：onTouchEvent, interceptKey, "InputMethod".
     - **通知/面板**：Notification, "closeQs" (Quick Settings), "cancelAutohide", "animateCollapsePanels".
     - **进程**：Start proc, Died, ActivityRecord.
   - **消歧规则**：这是**兜底类别**。凡是涉及屏幕内容**如何显示**（而非屏幕是否亮起）、窗口如何叠加、触摸事件如何分发，统统归为此类。

**思维链步骤**：
1. 提取日志中的核心动词和名词。
2. 检查是否存在“安全/权限”相关词汇，若有优先归为 Authentication & Security。
3. 检查是否涉及“Surface”、“Clipping”、“Window”、“Notification”或“Touch”，若有**必须**归为 System Services & Daemons，排除 Hardware 误判。
4. 检查是否涉及“Lock”，区分是 Power WakeLock 还是 View Lock。
5. 确定最终类别。

请输出 JSON 格式，不要包含任何Markdown标记或额外文本，不要翻译类别名称：
{{"analysis": "简要分析关键词与上下文...", "SemanticClass": "Category Name"}}"""

    def _build_prompt_category(self, log_content,sysType):
        """任务 2: 异常类型判断"""
        return f"""你是一个擅长推理分析的{sysType}操作系统日志分析专家。请分析以下日志是否属于异常日志并给出理由，根据你的理由选择最合适的类别：
"{log_content}"

请根据逻辑判断：
- 如果是用户无法通过身份验证、权限不足或非法的访问尝试，输出 "Authentication & Security Failures"
- 如果是硬件过时、BIOS 配置错误、资源表无效或内核子系统初始化失败，输出 "Hardware & Kernel Config Errors"
- 如果是运行时的服务不可达、连接非正常断开或响应超时，通常影响服务的可用性，输出 "Service Communication & Timeout Exceptions"
- 如果是正常日志或不属于以上异常，必须输出 "Other"

请直接输出 JSON，格式如：{{"Normal":"True or False","Reason":”理由“"EventCategory": "类别名称"}}
不要包含任何解释或 Markdown 标记。"""

    def analyze(self, logs,sysType):
        """
        遍历日志列表，分别为任务 1 和任务 2 调用 LLM
        """
        results = []
        print(f"开始分析 {len(logs)} 条日志 (使用 Qwen2.5:3b)...")

        for log in tqdm(logs, desc="LLM Analyzing"):
            log_text = log['CleanedContent']
            if sysType== "Android":
                Component=log['Component']
                prompt_s = self._build_prompt_semantic_Android(log_text,Component,sysType)
            else:
                Component=""
                prompt_s = self._build_prompt_semantic_Linux(log_text,Component,sysType)
            
            # --- 第一次调用：获取 SemanticClass ---
            
            resp_s = self.llm.call_llm(prompt_s, json_mode=True)
            semantic_class = "Kernel Boot & General System" # 默认值
            if resp_s:
                try:
                    data_s = json.loads(resp_s)
                    semantic_class = data_s.get("SemanticClass", semantic_class)
                except json.JSONDecodeError:
                    pass

            # --- 第二次调用：获取 EventCategory ---
            prompt_c = self._build_prompt_category(log_text,sysType)
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
