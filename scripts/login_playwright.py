#!/usr/bin/env python3
"""
淘宝登录 - Playwright 完整流程
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def login():
    auth_file = Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 有界面
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()
        
        print("打开淘宝登录页...")
        await page.goto("https://login.taobao.com")
        
        print("请完成登录（扫码或密码）...")
        print("登录成功后，按 Enter 键保存状态...")
        
        input()  # 等待用户按回车
        
        # 保存状态
        storage = await context.storage_state()
        auth_file.parent.mkdir(parents=True, exist_ok=True)
        with open(auth_file, 'w') as f:
            json.dump(storage, f, indent=2)
        
        print(f"✅ 登录态已保存到: {auth_file}")
        print(f"   Cookies: {len(storage.get('cookies', []))} 个")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(login())
