"""
考试安排查询：通过智慧理工门户获取考试信息

流程：
1. 门户登录（IDS认证）
2. 点击"教务系统" → 新标签页打开强智系统
3. 扫描标签页，切换到强智系统
4. 在强智主页点击"考试报名"
5. 等待导航到考试报名页面
6. 点击"查询"
7. 获取考试安排HTML
"""

import os
import time
from typing import Optional

from .portal_browser import (
    _safe_import_drission,
    _poll_url_change,
    _get_tab_by_url,
    find_and_click,
    PORTAL_URL,
)


def get_exams_via_portal(student_id: str, password: str) -> Optional[str]:
    """通过智慧理工门户获取考试安排HTML"""
    ChromiumPage = _safe_import_drission()
    if not ChromiumPage:
        return None

    try:
        from DrissionPage import ChromiumOptions

        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]

        co = None
        for path in edge_paths:
            if os.path.exists(path):
                co = ChromiumOptions()
                co.set_browser_path(path)
                print(f"[Exam] 找到Edge浏览器: {path}")
                break
        if co is None:
            co = ChromiumOptions()

        # browser_page 管理所有标签页
        browser_page = ChromiumPage(addr_or_opts=co)
        active_page = browser_page

        # ===== Step 1: 访问门户 =====
        print("[Exam] 正在访问智慧理工门户...")
        active_page.get(PORTAL_URL)
        time.sleep(3)

        current_url = active_page.url
        print(f"[Exam] 当前URL: {current_url}")

        # ===== Step 2: IDS登录 =====
        if "authserver/login" in current_url:
            print("[Exam] 需要IDS登录，正在填入账号密码...")

            username = (
                active_page.ele("#username", timeout=3)
                or active_page.ele('xpath://input[@id="username"]', timeout=3)
                or active_page.ele('xpath://input[@name="username"]', timeout=3)
            )
            pwd = (
                active_page.ele("#password", timeout=3)
                or active_page.ele('xpath://input[@id="password"]', timeout=3)
                or active_page.ele('xpath://input[@type="password"]', timeout=3)
            )

            if not username or not pwd:
                print("[Exam] 无法定位IDS登录框")
                input("[Exam] 请手动完成IDS登录，按回车继续: ")
            else:
                username.input(student_id)
                pwd.input(password)
                print("[Exam] IDS账号密码已填入")

                login_btn = (
                    active_page.ele("#login_submit", timeout=2)
                    or active_page.ele('xpath://input[@id="login_submit"]', timeout=2)
                    or active_page.ele('xpath://button[@type="submit"]', timeout=2)
                    or active_page.ele("text:登录", timeout=2)
                )

                if login_btn:
                    login_btn.click()
                    time.sleep(3)
                else:
                    input("[Exam] 请手动点击IDS登录，按回车继续: ")

                if "captcha" in active_page.html.lower() or "验证码" in active_page.html:
                    input("[Exam] IDS需要验证码，请在浏览器中完成并按回车: ")

                ok, url = _poll_url_change(active_page, ["ehall", "portal"], timeout_sec=20)
                print(f"[Exam] IDS登录后URL: {url}")

        # ===== Step 3: 点击"教务系统" =====
        print("[Exam] 正在查找并点击'教务系统'...")
        time.sleep(2)

        clicked = find_and_click(active_page, ["本科教务", "教务系统", "教务管理"], "主入口")

        if not clicked:
            print("[Exam] 未自动找到教务入口，请手动点击")
            input("[Exam] 请在浏览器中点击'教务系统'，按回车继续: ")
        else:
            print("[Exam] 已点击'教务系统'，等待跳转...")

        # ===== Step 4: 切换到强智系统标签页 =====
        ok, url = _poll_url_change(active_page, ["bkjw.njust.edu.cn"], timeout_sec=15)
        if ok:
            print(f"[Exam] 当前标签页已导航到强智: {url}")
        else:
            print("[Exam] 当前标签页未导航，扫描所有标签页...")
            time.sleep(3)

            qz_tab = _get_tab_by_url(browser_page, ["bkjw.njust.edu.cn"])
            if qz_tab:
                print("[Exam] 发现强智系统标签页，切换操作对象...")
                try:
                    qz_tab.set.activate()
                    time.sleep(2)
                except Exception as e:
                    print(f"[Exam] 激活标签页失败: {e}")
                active_page = qz_tab
                print(f"[Exam] 切换后URL: {active_page.url}")
            else:
                print("[Exam] 未检测到强智系统标签页")
                print("    请在浏览器中确保已进入强智系统主页")
                input("    完成后按回车继续: ")

        # 确认当前在强智系统
        if "bkjw.njust.edu.cn" not in active_page.url:
            print(f"[Exam] 似乎不在强智系统，当前URL: {active_page.url}")
            print("    请手动在浏览器中导航到强智系统")
            input("    完成后按回车继续: ")

        print(f"[Exam] 强智系统当前URL: {active_page.url}")
        time.sleep(3)

        # ===== Step 5: 在强智主页点击"考试报名" =====
        print("[Exam] 正在强智系统中查找'考试报名'入口...")

        clicked2 = find_and_click(
            active_page,
            ["考试报名", "考试安排", "考务管理", "考试查询", "我的考试"],
            "考试入口"
        )

        if not clicked2:
            print("[Exam] 未自动找到考试入口")
            print("    请在浏览器中手动点击'考试报名'或'考试安排'")
            input("    完成后按回车继续: ")
        else:
            print("[Exam] 已点击考试入口，等待跳转...")

        # 等待导航到考试页面
        ok, url = _poll_url_change(
            active_page,
            ["ksap", "ksbm", "kaowu", "exam", "xskscx", "ksrw"],
            timeout_sec=20
        )
        if ok:
            print(f"[Exam] 已到达考试页面: {url}")
        else:
            print(f"[Exam] 等待后URL: {url}")
            exam_tab = _get_tab_by_url(browser_page, ["ksap", "ksbm", "kaowu", "exam"])
            if exam_tab:
                print("[Exam] 发现考试页新标签页，切换中...")
                try:
                    exam_tab.set.activate()
                    time.sleep(2)
                except Exception as e:
                    print(f"[Exam] 激活考试标签页失败: {e}")
                active_page = exam_tab

        # ===== Step 6: 点击"查询"按钮 =====
        print("[Exam] 正在查找'查询'按钮...")
        time.sleep(2)

        # 尝试多种可能的查询按钮选择器
        query_selectors = [
            "text:查询",
            'xpath://input[@value="查询"]',
            'xpath://button[contains(text(),"查询")]',
            'xpath://a[contains(text(),"查询")]',
            'xpath://span[contains(text(),"查询")]',
            "#queryBtn",
            "#searchBtn",
            "#btnSearch",
            'xpath://input[@type="submit"]',
        ]

        query_clicked = False
        for sel in query_selectors:
            try:
                btn = active_page.ele(sel, timeout=1)
                if btn:
                    print(f"[Exam] 找到查询按钮: {sel}")
                    btn.click()
                    query_clicked = True
                    time.sleep(3)
                    break
            except:
                continue

        if not query_clicked:
            print("[Exam] 未自动找到查询按钮")
            print("    请在浏览器中手动点击'查询'按钮")
            input("    完成后按回车继续: ")
        else:
            print("[Exam] 已点击查询，等待结果...")

        # 等待数据加载
        time.sleep(3)

        # ===== Step 7: 获取最终HTML =====
        final_url = active_page.url
        html = active_page.html
        print(f"[Exam] 最终URL: {final_url}")

        # 检查是否有考试数据
        has_data = (
            "考试时间" in html
            or "考试地点" in html
            or "座位号" in html
            or "考场" in html
            or "table" in html.lower()
        )

        if has_data:
            print("[Exam] 成功获取考试安排HTML")
        else:
            print("[Exam] 页面似乎不含考试数据，保存供分析")

        # 保存HTML到文件
        save_path = os.path.expanduser("~/Desktop/njust_exams_page.html")
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[Exam] HTML已保存: {save_path} ({len(html)} bytes)")

        try:
            browser_page.quit()
        except:
            pass
        return html

    except Exception as e:
        print(f"[Exam] 浏览器自动化异常: {e}")
        import traceback
        traceback.print_exc()
        return None
