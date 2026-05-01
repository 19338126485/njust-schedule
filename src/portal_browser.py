"""
最终方案：通过智慧理工门户进入课表

南理工门户特殊情况：
- 点击"教务系统"会在**新标签页**打开强智系统
- DrissionPage 4.x: get_tabs() 获取所有标签页，每个标签页是独立的页面对象
- 找到含bkjw的标签页后，用该标签页对象直接操作

正确流程：
1. 启动浏览器，访问门户
2. IDS登录
3. 点击"教务系统"，等待新标签页打开
4. 扫描标签页，找到含bkjw的，使用该标签页对象操作
5. 在强智主页点击"课表"
6. 等待导航到课表页，获取HTML
"""

import os
import time
from typing import Optional


def _safe_import_drission():
    """安全导入DrissionPage"""
    try:
        from DrissionPage import ChromiumPage
        return ChromiumPage
    except ImportError:
        print("[Portal] 缺少 DrissionPage")
        return None


PORTAL_URL = "https://ehall.njust.edu.cn/new/index.html"


def find_and_click(page_obj, text_keywords, desc=""):
    """在页面上查找包含指定文本的元素并点击"""
    for keyword in text_keywords:
        selectors = [
            f"text:{keyword}",
            f'xpath://a[contains(text(),"{keyword}")]',
            f'xpath://span[contains(text(),"{keyword}")]',
            f'xpath://div[contains(text(),"{keyword}")]',
            f'xpath://li[contains(text(),"{keyword}")]',
        ]
        for sel in selectors:
            try:
                ele = page_obj.ele(sel, timeout=1)
                if ele:
                    print(f"[Portal] {desc}找到: '{keyword}'")
                    ele.click()
                    return True
            except:
                continue
    return False


def _poll_url_change(page, expected_substrings, timeout_sec=30, check_interval=2):
    """轮询等待URL变化到包含指定子串的页面"""
    waited = 0
    while waited < timeout_sec:
        current = page.url
        for substr in expected_substrings:
            if substr in current:
                return True, current
        time.sleep(check_interval)
        waited += check_interval
    return False, page.url


def _get_tab_by_url(browser_page, url_substrings):
    """
    在所有标签页中查找URL包含指定子串的标签页对象
    DrissionPage 4.x: get_tabs() 返回标签页对象列表
    每个标签页对象有 .url, .html, .ele() 等方法
    """
    try:
        tabs = browser_page.get_tabs()
        if not tabs:
            return None
        for i, tab in enumerate(tabs):
            try:
                tab_url = tab.url
                for substr in url_substrings:
                    if substr in tab_url:
                        print(f"[Portal] 在标签页#{i}发现匹配URL: {tab_url}")
                        return tab
            except:
                continue
    except Exception as e:
        print(f"[Portal] 标签页查找失败: {e}")
    return None


def get_schedule_via_portal(student_id: str, password: str) -> Optional[str]:
    """通过智慧理工门户获取课表HTML"""
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
                print(f"[Portal] 找到Edge浏览器: {path}")
                break

        if co is None:
            co = ChromiumOptions()

        # browser_page 是浏览器实例，管理所有标签页
        browser_page = ChromiumPage(addr_or_opts=co)
        # active_page 是当前操作的标签页对象
        active_page = browser_page

        # ===== Step 1: 访问门户 =====
        print("[Portal] 正在访问智慧理工门户...")
        active_page.get(PORTAL_URL)
        time.sleep(3)

        current_url = active_page.url
        print(f"[Portal] 当前URL: {current_url}")

        # ===== Step 2: IDS登录 =====
        if "authserver/login" in current_url:
            print("[Portal] 需要IDS登录，正在填入账号密码...")

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
                print("[Portal] 无法定位IDS登录框")
                input("[Portal] 请手动完成IDS登录，按回车继续: ")
            else:
                username.input(student_id)
                pwd.input(password)
                print("[Portal] IDS账号密码已填入")

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
                    input("[Portal] 请手动点击IDS登录，按回车继续: ")

            if "captcha" in active_page.html.lower() or "验证码" in active_page.html:
                input("[Portal] IDS需要验证码，请在浏览器中完成并按回车: ")

            ok, url = _poll_url_change(active_page, ["ehall", "portal"], timeout_sec=20)
            print(f"[Portal] IDS登录后URL: {url}")

        # ===== Step 3: 点击"教务系统" =====
        print("[Portal] 正在查找并点击'教务系统'...")
        time.sleep(2)

        clicked = find_and_click(active_page, ["本科教务", "教务系统", "教务管理"], "主入口")

        if not clicked:
            print("[Portal] 未自动找到教务入口，请手动点击")
            input("[Portal] 请在浏览器中点击'教务系统'，按回车继续: ")
        else:
            print("[Portal] 已点击'教务系统'，等待跳转...")

        # ===== Step 4: 等待并切换到强智系统标签页 =====
        # 方法A: 当前标签页导航
        ok, url = _poll_url_change(active_page, ["bkjw.njust.edu.cn"], timeout_sec=15)
        if ok:
            print(f"[Portal] 当前标签页已导航到强智: {url}")
        else:
            # 方法B: 扫描所有标签页，找到含bkjw的
            print("[Portal] 当前标签页未导航，扫描所有标签页...")
            time.sleep(3)

            qz_tab = _get_tab_by_url(browser_page, ["bkjw.njust.edu.cn"])
            if qz_tab:
                print("[Portal] 发现强智系统标签页，切换操作对象...")
                try:
                    qz_tab.set.activate()  # 激活该标签页（让浏览器显示它）
                    time.sleep(2)
                except Exception as e:
                    print(f"[Portal] 激活标签页失败: {e}")
                # 后续所有操作改用 qz_tab
                active_page = qz_tab
                print(f"[Portal] 切换后URL: {active_page.url}")
            else:
                print("[Portal] 未检测到强智系统标签页")
                print("    请在浏览器中确保已进入强智系统主页")
                print("    （URL应包含 bkjw.njust.edu.cn）")
                input("    完成后按回车继续: ")

        # 确认当前在强智系统
        if "bkjw.njust.edu.cn" not in active_page.url:
            print("[Portal] 似乎不在强智系统，当前URL: " + active_page.url)
            print("    请手动在浏览器中导航到强智系统")
            input("    完成后按回车继续: ")

        print(f"[Portal] 强智系统当前URL: {active_page.url}")
        time.sleep(3)

        # ===== Step 5: 在强智系统主页点击"课表" =====
        print("[Portal] 正在强智系统中查找'课表'入口...")

        clicked2 = find_and_click(
            active_page,
            ["课表", "课表查询", "学生课表", "我的课表", "课程表", "个人课表"],
            "课表入口"
        )

        if not clicked2:
            print("[Portal] 未自动找到课表入口")
            print("    请在浏览器中手动点击'课表查询'或'我的课表'")
            input("    完成后按回车继续: ")
        else:
            print("[Portal] 已点击课表入口，等待跳转...")

        # ===== Step 6: 等待导航到课表页 =====
        ok, url = _poll_url_change(active_page, ["xskb"], timeout_sec=20)
        if ok:
            print(f"[Portal] 已到达课表页: {url}")
        else:
            print(f"[Portal] 等待后URL: {url}")
            # 再次检查是否有新标签页打开课表
            schedule_tab = _get_tab_by_url(browser_page, ["xskb"])
            if schedule_tab:
                print("[Portal] 发现课表页新标签页，切换中...")
                try:
                    schedule_tab.set.activate()
                    time.sleep(2)
                except Exception as e:
                    print(f"[Portal] 激活课表标签页失败: {e}")
                active_page = schedule_tab

        # 最终确认
        final_url = active_page.url
        html = active_page.html
        print(f"[Portal] 最终URL: {final_url}")

        # 检查是否真的是课表页
        is_login = (
            "Verifyservlet" in html
            or 'name="USERNAME"' in html
            or 'name="PASSWORD"' in html
            or "请先登录系统" in html
            or "authserver/login" in final_url
        )

        is_schedule = (
            "xskb" in final_url
            or "课表" in html
            or "星期" in html
            or "节次" in html
            or ("bkjw" in final_url and not is_login)
        )

        if is_schedule and not is_login:
            print("[Portal] 成功获取课表HTML")
            try:
                browser_page.quit()
            except:
                pass
            return html
        else:
            print("[Portal] 未确认到达课表页")
            if is_login:
                print("    页面仍是登录页")
            try:
                browser_page.quit()
            except:
                pass
            return html

    except Exception as e:
        print(f"[Portal] 浏览器自动化异常: {e}")
        import traceback
        traceback.print_exc()
        return None
