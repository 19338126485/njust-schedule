"""
验证码图片处理工具

提供多种方式查看验证码：
1. 保存为图片文件（默认）
2. base64编码输出到终端（如果图片无法打开）
3. 生成临时HTML页面查看（备选）
"""

import os
import base64
import tempfile
from typing import Optional


def detect_image_format(data: bytes) -> str:
    """通过magic bytes检测图片格式"""
    if data[:2] == b'\xff\xd8':
        return "JPEG"
    if data[:4] == b'\x89PNG':
        return "PNG"
    if data[:3] == b'GIF':
        return "GIF"
    if data[:2] == b'BM':
        return "BMP"
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return "WEBP"
    return "UNKNOWN"


def save_captcha_image(data: bytes, base_path: str) -> str:
    """
    保存验证码图片，自动检测格式并使用正确扩展名
    
    Args:
        data: 图片二进制数据
        base_path: 基础路径（不含扩展名）
        
    Returns:
        实际保存的文件路径
    """
    fmt = detect_image_format(data)
    
    if fmt == "JPEG":
        ext = ".jpg"
    elif fmt == "PNG":
        ext = ".png"
    elif fmt == "GIF":
        ext = ".gif"
    elif fmt == "BMP":
        ext = ".bmp"
    elif fmt == "WEBP":
        ext = ".webp"
    else:
        # 无法识别格式，保存为原始数据+HTML查看器
        ext = ".bin"
    
    path = base_path + ext
    
    with open(path, "wb") as f:
        f.write(data)
    
    print(f"[Captcha] 图片格式: {fmt}, 大小: {len(data)} bytes")
    print(f"[Captcha] 已保存到: {path}")
    
    return path


def print_captcha_base64(data: bytes) -> None:
    """
    将验证码图片以base64形式打印到终端
    用户可以在浏览器中打开 data:image/... 查看
    """
    fmt = detect_image_format(data)
    mime = "image/jpeg"
    if fmt == "PNG":
        mime = "image/png"
    elif fmt == "GIF":
        mime = "image/gif"
    
    b64 = base64.b64encode(data).decode()
    
    print(f"\n[Captcha] 如果图片无法打开，可复制以下链接到浏览器地址栏查看:")
    print(f"data:{mime};base64,{b64[:80]}... (共 {len(b64)} 字符)")
    print(f"\n[Captcha] 或运行以下命令生成临时HTML文件:")
    
    # 生成包含完整图片的HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>验证码</title></head>
    <body style="text-align:center; padding:50px;">
        <h2>请输入下方验证码:</h2>
        <img src="data:{mime};base64,{b64}" style="border:2px solid #333;">
        <br><br>
        <p>图片格式: {fmt} | 大小: {len(data)} bytes</p>
    </body>
    </html>
    """
    
    # 保存到临时目录
    fd, html_path = tempfile.mkstemp(suffix=".html", prefix="captcha_")
    os.write(fd, html.encode())
    os.close(fd)
    
    print(f"    start {html_path}")
    print(f"\n[Captcha] 图片已嵌入HTML文件: {html_path}")


def get_user_captcha(data: bytes, base_path: str = "captcha") -> str:
    """
    完整的验证码处理流程：保存图片、打印备选查看方式、提示用户输入
    
    Returns:
        用户输入的验证码字符串
    """
    # 保存图片
    path = save_captcha_image(data, base_path)
    
    # 额外提供base64/HTML查看方式
    print_captcha_base64(data)
    
    # 提示用户输入
    code = input("\n[IDS] 请输入验证码（看不清直接回车重试）: ").strip()
    return code
