#!/usr/bin/env python3
"""
飞书长连接客户端 - 用于接收群消息
"""
import os
import sys
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import *
except ImportError:
    print("请先安装: pip3 install lark-oapi")
    sys.exit(1)

# 配置 - 从 config.json 读取
CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'config.json')

def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

config = load_config()
APP_ID = config.get('app_id', '')
APP_SECRET = config.get('app_secret', '')

# 处理收到的消息
def do_p2_im_message_receive_v1(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    """处理收到的消息 v2.0"""
    print(f'[收到消息] {lark.JSON.marshal(data, indent=4)}')
    
    # 提取消息内容
    message = data.event.message
    chat_id = message.chat_id
    content = json.loads(message.content)
    text = content.get('text', '')
    
    print(f"群ID: {chat_id}")
    print(f"消息内容: {text}")
    
    # TODO: 在这里添加你的处理逻辑
    # 比如：如果有人@机器人说"查价格"，就调用价格查询

def main():
    if not APP_ID or not APP_SECRET:
        print("错误: 请在 config.json 中配置 app_id 和 app_secret")
        print(f"配置文件路径: {CONFIG_FILE}")
        sys.exit(1)
    
    # 创建事件处理器
    event_handler = lark.EventDispatcherHandler.builder("", "") \
        .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1) \
        .build()
    
    # 创建长连接客户端
    cli = lark.ws.Client(
        APP_ID, 
        APP_SECRET,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO
    )
    
    print(f"正在启动长连接客户端...")
    print(f"App ID: {APP_ID[:10]}...")
    print("连接成功后，控制台会显示 'connected to wss://...'")
    print("按 Ctrl+C 停止\n")
    
    # 启动客户端（会阻塞）
    cli.start()

if __name__ == "__main__":
    main()
