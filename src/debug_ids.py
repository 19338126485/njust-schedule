#!/usr/bin/env python3
"""
IDS登录页诊断脚本

运行: python src/debug_ids.py

功能：只抓取IDS登录页，分析其HTML结构，输出关键信息：
- 表单字段
- 加密相关脚本
- 页面结构特征

这可以帮助我们确认南理工IDS是否与标准金智系统不同。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import re

IDS_URL = "https://ids.njust.edu.cn/authserver/login"

print("=" * 60)
print("IDS登录页诊断")
print("=" * 60)

session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    ),
})

print(f"\n[GET] {IDS_URL}")
resp = session.get(IDS_URL, timeout=15)
print(f"状态码: {resp.status_code}")
print(f"Content-Type: {resp.headers.get('Content-Type', 'unknown')}")
print(f"内容长度: {len(resp.text)} bytes")

html = resp.text

# 提取所有 input 字段
print("\n" + "=" * 60)
print("表单 input 字段:")
print("=" * 60)
inputs = re.findall(r'<input[^>]*>', html, re.IGNORECASE)
for inp in inputs:
    # 提取 name, id, value, type
    name = re.search(r'name="([^"]*)"', inp)
    id_attr = re.search(r'id="([^"]*)"', inp)
    value = re.search(r'value="([^"]*)"', inp)
    type_attr = re.search(r'type="([^"]*)"', inp)
    
    parts = []
    if type_attr:
        parts.append(f"type={type_attr.group(1)}")
    if name:
        parts.append(f"name={name.group(1)}")
    if id_attr:
        parts.append(f"id={id_attr.group(1)}")
    if value:
        val = value.group(1)
        if len(val) > 30:
            val = val[:30] + "..."
        parts.append(f"value={val}")
    
    if parts:
        print(f"  <input {' | '.join(parts)}>")

# 查找所有 script 标签
print("\n" + "=" * 60)
print("外部 JavaScript 文件:")
print("=" * 60)
scripts = re.findall(r'<script[^>]*src="([^"]*)"[^>]*>', html, re.IGNORECASE)
for src in scripts:
    print(f"  {src}")
    # 高亮包含 encrypt 的
    if "encrypt" in src.lower():
        print(f"    ^^^ 包含 'encrypt' 关键字")

# 查找内嵌 script
print("\n" + "=" * 60)
print("内嵌 JavaScript (包含 'salt'/'encrypt' 的片段):")
print("=" * 60)
inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
for i, script in enumerate(inline_scripts):
    if "salt" in script.lower() or "encrypt" in script.lower() or "aes" in script.lower():
        # 打印包含这些关键字的前后几行
        lines = script.split('\n')
        for j, line in enumerate(lines):
            lower = line.lower()
            if "salt" in lower or "encrypt" in lower or "aes" in lower:
                print(f"  [script#{i} line{j}]: {line.strip()[:100]}")

# 检查是否有验证码相关元素
print("\n" + "=" * 60)
print("验证码相关:")
print("=" * 60)
if "captcha" in html.lower():
    print("  页面HTML中包含 'captcha' 关键字")
if "验证码" in html:
    print("  页面HTML中包含 '验证码' 关键字")

# 尝试访问 needCaptcha 接口
try:
    captcha_check = session.get(
        "https://ids.njust.edu.cn/authserver/needCaptcha.html?username=test",
        timeout=10
    )
    print(f"  needCaptcha 接口返回: '{captcha_check.text.strip()}'")
except Exception as e:
    print(f"  needCaptcha 接口请求失败: {e}")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
print("\n如果上面的 output 显示:")
print("• 有 'pwdDefaultEncryptSalt' 相关字段 → 标准金智系统，IDS模拟登录应该可行")
print("• 没有 salt 字段，但有其他加密相关JS → 可能需要调整加密逻辑")
print("• 完全没有加密相关元素 → 可能密码是明文提交的（或者页面结构完全不同）")
print("\n把这份输出贴给我，我根据实际页面结构调整代码。")
