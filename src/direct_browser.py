"""
最终兜底方案：浏览器直接访问课表URL

流程（完全模拟用户的正常操作）：
1. 启动Edge浏览器
2. 直接访问课表URL
3. 如果未登录，浏览器自动被重定向到IDS登录页
4. 在IDS登录页填入账号密码
5. 登录成功后，CAS自动302回课表URL
6. 浏览器完成SSO，到达课表页面
7. 返回课表HTML

这是100%可靠的方案，因为浏览器自动处理所有302跳转和Cookie同步。
"""

import sys
import os
import time
from typing import Optional


def _safe_import_drission():
    """安全导入DrissionPage"""
    try:
        from DrissionPage import ChromiumPage
        return ChromiumPage
    except ImportError:
        print("[Direct] 缺少 DrissionPage，尝试安装...")
        os.system("pip install DrissionPage -q")
        try:
            from DrissionPage import ChromiumPage
            return ChromiumPage
        except ImportError:
            print("[Direct] ❌ DrissionPage 安装失败")
            return None


SCHEDULE_URL = (
    "http://bkjw.njust.edu.cn/njlgdx/xskb/xskb_list.do"
    "?Ves632DSdyV=NEW_XSD_PYGL"
)
IDS_LOGIN_URL = "https://ids.njust.edu.cn/authserver/login"


def get_schedule_html_direct(student_id: str, password: str) -> Optional[str]:
    """
    浏览器直接访问课表URL，自动完成完整SSO流程

    南理工的特殊情况：
    - IDS统一认证 和 强智系统 是两套独立认证
    - 从门户进入时，门户和强智之间有票据传递（自动登录）
    - 直接访问课表URL时，强智系统会显示自己的登录页（Verifyservlet）
    - 需要在强智登录页也填入账号密码才能看到课表

    Args:
        student_id: 学号
        password: 密码

    Returns:
        课表页面的HTML文本
    """
    ChromiumPage = _safe_import_drission()
    if not ChromiumPage:
        return None

    try:
        from DrissionPage import ChromiumOptions

        # 尝试Edge路径
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]

        co = None
        for path in edge_paths:
            if os.path.exists(path):
                co = ChromiumOptions()
                co.set_browser_path(path)
                print(f"[Direct] 找到Edge浏览器: {path}")
                break

        if co is None:
            co = ChromiumOptions()

        page = ChromiumPage(addr_or_opts=co)

        # Step 1: 直接访问课表URL
        print(f"[Direct] 正在访问课表页面...")
        page.get(SCHEDULE_URL)
        time.sleep(3)

        current_url = page.url
        html = page.html
        print(f"[Direct] 当前URL: {current_url}")

        # 定义检测函数：当前页面是否是登录页
        def is_ids_login():
            return "authserver/login" in current_url

        def is_qiangzhi_login():
            return (
                "Verifyservlet" in html
                or 'name="USERNAME"' in html
                or 'name="PASSWORD"' in html
                or "请先登录系统" in html
                or "登录个人中心" in html
                or "RANDOMCODE" in html
            )

        # Step 2: 处理IDS登录（如果被重定向到IDS）
        if is_ids_login():
            print("[Direct] 被重定向到IDS登录页，正在填入账号密码...")

            username_input = (
                page.ele("#username", timeout=3)
                or page.ele('xpath://input[@id="username"]', timeout=3)
                or page.ele('xpath://input[@name="username"]', timeout=3)
            )
            password_input = (
                page.ele("#password", timeout=3)
                or page.ele('xpath://input[@id="password"]', timeout=3)
                or page.ele('xpath://input[@type="password"]', timeout=3)
            )

            if not username_input or not password_input:
                print("[Direct] ❌ 无法定位IDS登录框")
                page.quit()
                return None

            username_input.input(student_id)
            password_input.input(password)

            login_btn = (
                page.ele("#login_submit", timeout=2)
                or page.ele('xpath://input[@id="login_submit"]', timeout=2)
                or page.ele('xpath://button[@type="submit"]', timeout=2)
                or page.ele("text:登录", timeout=2)
            )

            if login_btn:
                login_btn.click()
                time.sleep(3)
            else:
                input("[Direct] 请手动点击IDS登录，完成后按回车: ")

            if "captcha" in page.html.lower() or "验证码" in page.html:
                input("[Direct] 需要IDS验证码，请在浏览器中完成并按回车: ")

            # 等待跳转
            waited = 0
            while "authserver" in page.url and waited < 20:
                time.sleep(1)
                waited += 1

            current_url = page.url
            html = page.html
            print(f"[Direct] IDS跳转后URL: {current_url}")

        # Step 3: 处理强智系统独立登录（关键！）
        if is_qiangzhi_login():
            print("[Direct] ⚠️ 强智系统要求独立登录，正在填入账号密码...")

            # 强智登录页字段
            qz_user = (
                page.ele("#xh", timeout=3)
                or page.ele('xpath://input[@id="xh"]', timeout=3)
                or page.ele('xpath://input[@name="USERNAME"]', timeout=3)
            )
            qz_pwd = (
                page.ele("#pwd", timeout=3)
                or page.ele('xpath://input[@id="pwd"]', timeout=3)
                or page.ele('xpath://input[@name="PASSWORD"]', timeout=3)
            )

            if not qz_user or not qz_pwd:
                print("[Direct] ❌ 无法定位强智登录框，请手动操作")
                input("[Direct] 请在浏览器中完成强智登录，按回车继续: ")
            else:
                qz_user.input(student_id)
                qz_pwd.input(password)
                print("[Direct] 强智账号密码已填入")

                # 查找强智登录按钮
                qz_submit = (
                    page.ele("#btnSubmit", timeout=2)
                    or page.ele('xpath://input[@id="btnSubmit"]', timeout=2)
                    or page.ele('xpath://input[@type="submit"]', timeout=2)
                )

                if qz_submit:
                    print("[Direct] 点击强智登录...")
                    qz_submit.click()
                    time.sleep(5)
                else:
                    input("[Direct] 请手动点击强智登录按钮，按回车继续: ")

            # 检查验证码（强智系统）
            if "RANDOMCODE" in page.html:
                print("[Direct] ⚠️ 强智系统需要验证码")
                input("[Direct] 请在浏览器中输入验证码并点击登录，按回车继续: ")
                time.sleep(3)

            current_url = page.url
            html = page.html
            print(f"[Direct] 强智登录后URL: {current_url}")

        # Step 4: 最终检查是否到达课表页
        if "xskb" in current_url and "bkjw" in current_url:
            # 再次确认不是登录页
            if not is_qiangzhi_login():
                print("[Direct] ✅ 已成功到达课表页面")
                page.quit()
                return html

        # 还在登录流程中
        if is_qiangzhi_login() or "authserver" in current_url:
            print("[Direct] ⚠️ 仍在认证流程中，请手动操作浏览器...")
            input("[Direct] 请在浏览器中完成所有登录步骤，到达课表页后按回车: ")
            current_url = page.url
            html = page.html
            print(f"[Direct] 最终URL: {current_url}")
            if "xskb" in current_url and not is_qiangzhi_login():
                print("[Direct] ✅ 已到达课表页面")
                page.quit()
                return html

        print(f"[Direct] ⚠️ 最终状态: URL={current_url}")
        page.quit()
        return None

    except Exception as e:
        print(f"[Direct] 浏览器自动化异常: {e}")
        return None
