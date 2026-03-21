#!/usr/bin/env python3
"""
测试飞书机器人发送消息
"""
import json
import requests

# 配置
APP_ID = "cli_a933ae5b17b9dcd4"
APP_SECRET = "pRrUlxBcvBNC4woA2abEHd3fVOyObxaT"
CHAT_ID = "oc_04717cb2f786e5e9a2869f84840924d8"

def get_access_token(app_id, app_secret):
    """获取 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": app_id, "app_secret": app_secret}
    
    resp = requests.post(url, json=payload, timeout=30)
    result = resp.json()
    
    if result.get("code") == 0:
        return result["tenant_access_token"]
    else:
        print(f"获取token失败: {result}")
        return None

def send_message(token, chat_id, text):
    """发送文本消息到群聊"""
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    return resp.json()

if __name__ == "__main__":
    print("测试飞书机器人发送消息...")
    print(f"App ID: {APP_ID}")
    print(f"Chat ID: {CHAT_ID}")
    print()
    
    # 获取token
    token = get_access_token(APP_ID, APP_SECRET)
    if not token:
        print("❌ 获取 token 失败")
        exit(1)
    
    print(f"✅ 获取 token 成功: {token[:20]}...")
    
    # 发送消息
    result = send_message(token, CHAT_ID, "🧪 测试消息：价格监控机器人能正常发消息了！")
    
    if result.get("code") == 0:
        print("✅ 消息发送成功！")
    else:
        print(f"❌ 消息发送失败: {result}")
        print(f"错误码: {result.get('code')}")
        print(f"错误信息: {result.get('msg')}")
