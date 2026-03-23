#!/usr/bin/env python3
"""
淘宝价格监控机器人 - 群消息监听服务
监听飞书群聊中 @淘宝价格监控 的消息并触发监控脚本
"""

import time
import json
import subprocess
import re
import requests
from datetime import datetime
from pathlib import Path

# 配置
APP_ID = "cli_a933ae5b17b9dcd4"
APP_SECRET = "pRrUlxBcvBNC4woA2abEHd3fVOyObxaT"
CHAT_ID = "oc_04717cb2f786e5e9a2869f84840924d8"
BASE_DIR = Path("~/.openclaw/workspace/skills/taobao-monitor").expanduser()

class TaobaoMonitorBot:
    def __init__(self):
        self.access_token = None
        self.token_expire = 0
        self.last_message_id = None
        self.bot_user_id = None  # 机器人的user_id，用于过滤自己的消息
        
    def _get_access_token(self) -> str:
        """获取 tenant_access_token"""
        if self.access_token and time.time() < self.token_expire:
            return self.access_token
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
        
        try:
            resp = requests.post(url, json=payload, timeout=30)
            data = resp.json()
            if data.get("code") == 0:
                self.access_token = data["tenant_access_token"]
                self.token_expire = time.time() + data["expire"] - 300
                return self.access_token
        except Exception as e:
            print(f"[Error] 获取token失败: {e}")
        return None
    
    def _get_bot_info(self):
        """获取机器人自己的user_id"""
        token = self._get_access_token()
        if not token:
            return
        
        url = "https://open.feishu.cn/open-apis/bot/v3/info"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            data = resp.json()
            if data.get("code") == 0:
                self.bot_user_id = data.get("bot", {}).get("open_id")
                print(f"[Info] 机器人ID: {self.bot_user_id}")
        except Exception as e:
            print(f"[Error] 获取bot信息失败: {e}")
    
    def _get_messages(self, limit=20):
        """获取群消息"""
        token = self._get_access_token()
        if not token:
            return []
        
        url = f"https://open.feishu.cn/open-apis/im/v1/messages?container_id={CHAT_ID}&container_id_type=chat&page_size={limit}"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            data = resp.json()
            if data.get("code") == 0:
                return data.get("data", {}).get("items", [])
        except Exception as e:
            print(f"[Error] 获取消息失败: {e}")
        return []
    
    def _send_message(self, content: str):
        """发送消息到群聊"""
        token = self._get_access_token()
        if not token:
            return False
        
        url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "receive_id": CHAT_ID,
            "msg_type": "text",
            "content": json.dumps({"text": content})
        }
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            result = resp.json()
            return result.get("code") == 0
        except Exception as e:
            print(f"[Error] 发送消息失败: {e}")
            return False
    
    def _is_mentioned(self, message: dict) -> bool:
        """检查消息是否@了机器人"""
        mentions = message.get("mentions", [])
        for mention in mentions:
            if mention.get("key", "").startswith("@_user_"):
                # 检查是否是@机器人
                return True
        return False
    
    def _extract_command(self, message: dict) -> str:
        """提取命令文本"""
        content = message.get("body", {}).get("content", "")
        # 移除@机器人的部分
        text = re.sub(r'@_user_\w+', '', content).strip()
        return text.lower()
    
    def _run_monitor(self):
        """运行价格监控脚本"""
        self._send_message("🤖 收到！开始运行价格监控...\n⏳ 预计需要 8-12 分钟，请稍候")
        
        try:
            # 运行监控脚本
            result = subprocess.run(
                ["python3", "monitor_mac_headed.py"],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                timeout=900  # 15分钟超时
            )
            
            output = result.stdout
            
            # 提取价格汇总部分
            report = self._parse_report(output)
            
            # 发送报告
            self._send_message(report)
            
        except subprocess.TimeoutExpired:
            self._send_message("⚠️ 监控超时，请检查浏览器状态")
        except Exception as e:
            self._send_message(f"❌ 运行出错: {e}")
    
    def _parse_report(self, output: str) -> str:
        """解析脚本输出，生成飞书报告"""
        lines = output.split('\n')
        report_lines = []
        
        # 查找价格汇总部分
        in_summary = False
        for line in lines:
            # 开始标记
            if '价格汇总' in line or '==' in line and '价格' in line:
                in_summary = True
            
            if in_summary:
                report_lines.append(line)
                
                # 结束标记
                if '结果已保存' in line or '成功:' in line:
                    break
        
        if report_lines:
            return "📊 价格监控报告\n" + '\n'.join(report_lines[:100])  # 限制长度
        else:
            # 简化报告
            return f"📊 价格监控完成\n\n```\n{output[-2000:]}\n```"  # 显示最后2000字符
    
    def _get_status(self):
        """获取监控状态"""
        try:
            # 读取配置
            config_path = BASE_DIR / "config.json"
            with open(config_path) as f:
                config = json.load(f)
            
            sku_count = len(config.get("sku_rules", {}))
            
            # 获取上次运行时间
            log_dir = BASE_DIR / "logs"
            latest_log = None
            if log_dir.exists():
                logs = sorted(log_dir.glob("prices_*.json"), reverse=True)
                if logs:
                    latest_log = logs[0]
                    time_str = latest_log.stem.split('_')[1] + ' ' + latest_log.stem.split('_')[2]
                    last_run = f"{time_str[:4]}-{time_str[4:6]}-{time_str[6:8]} {time_str[9:11]}:{time_str[11:13]}"
                else:
                    last_run = "无记录"
            else:
                last_run = "无记录"
            
            msg = f"""📋 淘宝价格监控状态

• 监控商品: {sku_count} 个
• 最后运行: {last_run}
• 定时任务: 09:00 / 21:00

指令:
@淘宝价格监控 查价格 - 立即运行监控
@淘宝价格监控 状态 - 查看当前状态"""
            
            self._send_message(msg)
            
        except Exception as e:
            self._send_message(f"❌ 获取状态失败: {e}")
    
    def run(self):
        """主循环"""
        print(f"[{datetime.now()}] 淘宝价格监控机器人启动")
        print(f"[{datetime.now()}] 监控群聊: {CHAT_ID}")
        
        # 获取机器人信息
        self._get_bot_info()
        
        # 发送启动通知
        self._send_message("🤖 淘宝价格监控机器人已上线！\n@我发送【查价格】开始监控")
        
        while True:
            try:
                messages = self._get_messages(limit=10)
                
                for msg in messages:
                    msg_id = msg.get("message_id")
                    
                    # 跳过已处理的消息
                    if msg_id == self.last_message_id:
                        break
                    
                    # 只处理新消息
                    if self.last_message_id is None:
                        self.last_message_id = msg_id
                        break
                    
                    # 检查是否是@机器人的消息
                    if self._is_mentioned(msg):
                        command = self._extract_command(msg)
                        sender = msg.get("sender", {}).get("sender_id", {}).get("open_id", "未知")
                        
                        print(f"[{datetime.now()}] 收到命令: {command} from {sender}")
                        
                        if "查价格" in command or "监控" in command or "运行" in command:
                            self._run_monitor()
                        elif "状态" in command or "status" in command:
                            self._get_status()
                        elif "帮助" in command or "help" in command:
                            self._send_message("""🤖 淘宝价格监控机器人

指令:
@淘宝价格监控 查价格 - 立即运行价格监控
@淘宝价格监控 状态 - 查看监控状态
@淘宝价格监控 帮助 - 显示帮助信息""")
                        else:
                            self._send_message("🤖 收到！未知指令\n发送【@淘宝价格监控 帮助】查看可用指令")
                    
                    # 更新最后消息ID
                    self.last_message_id = msg_id
                
                time.sleep(3)  # 每3秒检查一次
                
            except Exception as e:
                print(f"[{datetime.now()}] 错误: {e}")
                time.sleep(5)


if __name__ == "__main__":
    bot = TaobaoMonitorBot()
    bot.run()
