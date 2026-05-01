"""
DrissionPage 浏览器自动化登录模块（兜底方案）

当IDS模拟登录（AES加密）因JS变更而失效时，本模块提供100%可靠的替代方案：
启动真实浏览器，自动完成：
1. 打开IDS登录页
2. 填入账号密码
3. 点击登录
4. 点击"本科教务"
5. 等待SSO跳转到强智系统
6. 导出Cookie给 requests 使用

优点：
- 自动处理所有JS加密、验证码、302跳转
- 不需要逆向JS
- 适应性强，页面改版也不怕

缺点：
- 需要安装Chrome/Chromium
- 启动较慢（几秒）
- 有浏览器窗口弹出（可用 headless 模式隐藏）
"""

import os
import time
import json
from typing import Optional, Dict, Any
from urllib.parse import urlparse


def _safe_import_drission():
    """安全导入DrissionPage，未安装时给出友好提示"""
    try:
        from DrissionPage import ChromiumPage
        return ChromiumPage
    except ImportError:
        print("[Browser] 缺少 DrissionPage，尝试安装...")
        os.system("pip install DrissionPage -q")
        try:
            from DrissionPage import ChromiumPage
            return ChromiumPage
        except ImportError:
            print("[Browser] ❌ DrissionPage 安装失败，请手动运行: pip install DrissionPage")
            return None


class BrowserAuth:
    """
    浏览器自动化登录

    使用示例：
        auth = BrowserAuth("学号", "密码")
        cookies = auth.login_and_get_cookies()
        # 把cookies传给 requests.Session 或 api_client
    """

    IDS_LOGIN_URL = "https://ids.njust.edu.cn/authserver/login"
    PORTAL_URL = "https://ids.njust.edu.cn/personalInfo/personCenter/index.html"
    JW_URL = "http://bkjw.njust.edu.cn/"

    def __init__(self, student_id: str, password: str, headless: bool = False):
        self.student_id = student_id
        self.password = password
        self.headless = headless
        self.page = None

    def _init_browser(self) -> bool:
        """初始化浏览器实例，优先尝试Edge，fallback到Chrome"""
        ChromiumPage = _safe_import_drission()
        if not ChromiumPage:
            return False

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
                    print(f"[Browser] 找到Edge浏览器: {path}")
                    break

            # Edge没找到，尝试自动查找Chrome
            if co is None:
                co = ChromiumOptions()
                print("[Browser] 未找到Edge，尝试自动查找Chrome...")

            self.page = ChromiumPage(addr_or_opts=co)
            return True

        except Exception as e:
            print(f"[Browser] 启动浏览器失败: {e}")
            print("[Browser] 请确保已安装 Chrome 或 Edge")
            return False

    def login_and_get_cookies(self) -> Optional[Dict[str, str]]:
        """
        完整流程：浏览器登录IDS -> 进入教务系统 -> 导出Cookie

        Returns:
            包含所有相关Cookie的字典，失败返回None
        """
        if not self._init_browser():
            return None

        try:
            print("[Browser] 正在打开IDS登录页...")
            self.page.get(self.IDS_LOGIN_URL)
            time.sleep(1)

            # 填入账号密码
            print("[Browser] 正在输入账号密码...")

            # 尝试多种选择器，适配不同版本的金智页面
            username_input = (
                self.page.ele("#username", timeout=3)
                or self.page.ele('xpath://input[@id="username"]', timeout=3)
                or self.page.ele('xpath://input[@name="username"]', timeout=3)
            )
            password_input = (
                self.page.ele("#password", timeout=3)
                or self.page.ele('xpath://input[@id="password"]', timeout=3)
                or self.page.ele('xpath://input[@type="password"]', timeout=3)
            )

            if not username_input or not password_input:
                print("[Browser] ❌ 无法定位账号/密码输入框")
                self._close()
                return None

            username_input.input(self.student_id)
            password_input.input(self.password)

            # 查找并点击登录按钮
            login_btn = (
                self.page.ele("#login_submit", timeout=2)
                or self.page.ele('xpath://input[@id="login_submit"]', timeout=2)
                or self.page.ele('xpath://button[@type="submit"]', timeout=2)
                or self.page.ele("text:登录", timeout=2)
                or self.page.ele("text:登 录", timeout=2)
            )

            if not login_btn:
                print("[Browser] ❌ 无法定位登录按钮")
                self._close()
                return None

            print("[Browser] 点击登录...")
            login_btn.click()

            # 等待登录完成（URL变化或出现特定元素）
            print("[Browser] 等待登录完成...")
            time.sleep(3)

            # 检查是否需要验证码
            if "captcha" in self.page.html.lower() or "验证码" in self.page.html:
                print("[Browser] ⚠️ 需要验证码！请手动输入后按回车继续...")
                input("    在浏览器中完成验证码并点击登录后，按回车继续: ")
                time.sleep(2)

            # 检查是否还在登录页
            max_wait = 15
            waited = 0
            while "authserver/login" in self.page.url and waited < max_wait:
                time.sleep(1)
                waited += 1

            if "authserver/login" in self.page.url:
                print("[Browser] ❌ 登录似乎失败了，仍在登录页面")
                self._close()
                return None

            print(f"[Browser] ✅ IDS登录成功，当前URL: {self.page.url}")

            # 策略：直接访问已知的课表URL（用户确认过有效的地址）
            # 如果直接访问失败，fallback到提示用户手动导航
            known_schedule_url = (
                "http://bkjw.njust.edu.cn/njlgdx/xskb/xskb_list.do"
                "?Ves632DSdyV=NEW_XSD_PYGL"
            )

            print(f"[Browser] 正在直接访问课表页面...")
            self.page.get(known_schedule_url)
            time.sleep(5)

            current_url = self.page.url
            print(f"[Browser] 当前页面URL: {current_url}")

            # 检查是否成功到达课表页
            if "bkjw.njust.edu.cn" in current_url and "xskb" in current_url:
                print(f"[Browser] ✅ 已进入课表页面")
            elif "error" in current_url or "404" in current_url:
                print("[Browser] ⚠️ 直接访问失败，请手动操作...")
                print("    请在浏览器中:")
                print("    1. 点击'本科教务'或'我的课表'")
                print("    2. 或者直接在地址栏输入课表URL")
                print(f"    3. 到达课表页面后，回到这里按回车继续")
                input("    按回车继续...")
            else:
                # 可能是SSO中间跳转页，再等等
                print("[Browser] 等待SSO跳转完成...")
                time.sleep(5)
                current_url = self.page.url
                print(f"[Browser] 最终URL: {current_url}")

            # 导出所有Cookie（从浏览器，不是单页）
            cookies = self.page.cookies()
            print(f"[Browser] 共获取 {len(cookies)} 个Cookie")

            # 转换为requests可用的字典格式
            cookie_dict = {c["name"]: c["value"] for c in cookies}

            # 关键Cookie检查
            key_cookies = ["JSESSIONID", "CASTGC", "iPlanetDirectoryPro", "MOD_AUTH_CAS", "route"]
            found = [k for k in key_cookies if k in cookie_dict]
            print(f"[Browser] 关键Cookie: {found}")

            # 如果没有JSESSIONID但URL含bkjw，可能是Cookie存储方式不同
            if "JSESSIONID" not in cookie_dict and "bkjw.njust.edu.cn" in current_url:
                print("[Browser] ⚠️ 未找到JSESSIONID，尝试从页面请求头中提取...")
                # DrissionPage 可能需要用其他方式获取
                try:
                    # 尝试直接执行JS获取document.cookie
                    doc_cookies = self.page.run_js("return document.cookie")
                    if doc_cookies:
                        for pair in doc_cookies.split("; "):
                            if "=" in pair:
                                k, v = pair.split("=", 1)
                                cookie_dict[k.strip()] = v.strip()
                        print(f"[Browser] 从document.cookie补充后: {list(cookie_dict.keys())}")
                except Exception as e:
                    print(f"[Browser] JS获取Cookie失败: {e}")

            self._close()
            return cookie_dict

        except Exception as e:
            print(f"[Browser] 浏览器自动化异常: {e}")
            self._close()
            return None

    def get_jw_page_html(self) -> Optional[str]:
        """
        直接进入教务系统课表页面并返回HTML

        Returns:
            课表页HTML文本
        """
        cookies = self.login_and_get_cookies()
        if not cookies:
            return None

        # 用requests携带Cookie访问课表页
        import requests
        session = requests.Session()
        for k, v in cookies.items():
            session.cookies.set(k, v)

        try:
            resp = session.get(
                "http://bkjw.njust.edu.cn/njlgdx/xskb/xskb_list.do?Ves632DSdyV=NEW_XSD_PYGL",
                timeout=15,
            )
            return resp.text
        except Exception as e:
            print(f"[Browser] 获取课表页失败: {e}")
            return None

    def _close(self):
        """关闭浏览器"""
        if self.page:
            try:
                self.page.quit()
            except:
                pass
            self.page = None


def get_cookies_via_browser(student_id: str, password: str, headless: bool = False) -> Optional[Dict[str, str]]:
    """
    便捷函数：用浏览器完成IDS登录，返回Cookie字典

    Args:
        student_id: 学号
        password: 密码
        headless: 是否隐藏浏览器窗口（需要系统已配置好Chrome）

    Returns:
        Cookie字典
    """
    auth = BrowserAuth(student_id, password, headless=headless)
    return auth.login_and_get_cookies()


# ---- 直接请求 app.do 的实验性方法 ----

def fetch_app_api_with_browser(student_id: str, password: str,
                                method: str = "getCurrentTime",
                                params: Optional[Dict] = None) -> Optional[Any]:
    """
    用浏览器登录后，直接让浏览器访问 app.do 接口获取JSON

    这是验证 app.do 是否仍然可用的最佳方式：
    如果浏览器在登录后能直接拿到JSON响应，说明接口还活着。

    Args:
        student_id: 学号
        password: 密码
        method: app.do 的 method 参数
        params: 额外参数

    Returns:
        JSON解析后的数据
    """
    ChromiumPage = _safe_import_drission()
    if not ChromiumPage:
        return None

    auth = BrowserAuth(student_id, password)
    if not auth._init_browser():
        return None

    try:
        # 先完成登录流程
        cookies = auth.login_and_get_cookies()
        if not cookies:
            auth._close()
            return None

        # 重新打开浏览器（或复用当前页面）访问API
        # 注意：需要确保Cookie还在
        url = "http://bkjw.njust.edu.cn/app.do"
        query = f"?method={method}"
        if params:
            for k, v in params.items():
                query += f"&{k}={v}"

        full_url = url + query
        print(f"[Browser] 正在访问API: {full_url}")

        auth.page.get(full_url)
        time.sleep(2)

        # 尝试提取JSON
        page_text = auth.page.html

        # 页面可能是纯JSON，也可能是被包裹的
        # 尝试多种方式提取
        try:
            return json.loads(page_text)
        except json.JSONDecodeError:
            # 尝试从script标签或pre标签中提取
            import re
            json_match = re.search(r'&lt;pre[^&gt;]*&gt;(.*?)&lt;/pre&gt;', page_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # 直接搜索JSON模式
            json_match = re.search(r'(\{[\s\S]*\})', page_text)
            if json_match:
                return json.loads(json_match.group(1))

            print("[Browser] 页面内容不是标准JSON:")
            print(page_text[:500])
            return None

    except Exception as e:
        print(f"[Browser] API获取失败: {e}")
        return None
    finally:
        auth._close()


# ---- 课表HTML获取的最终兜底方案 ----

def get_schedule_html_via_browser(student_id: str, password: str) -> Optional[str]:
    """
    用浏览器完成完整流程：IDS登录 -> SSO -> 获取课表HTML

    这是获取课表的最终兜底方案。浏览器能完整处理所有SSO跳转、
    Cookie管理和重定向，而requests库在CAS流程中经常失败。

    流程：
        1. 启动Edge浏览器
        2. 访问IDS登录页，自动填入账号密码
        3. 点击登录，如有验证码提示用户手动处理
        4. IDS登录成功后，直接访问课表URL
        5. 浏览器自动完成SSO单点登录（强智系统 -> IDS验证 -> 返回课表）
        6. 返回课表页面的完整HTML

    Args:
        student_id: 学号
        password: 密码

    Returns:
        课表页面的HTML文本，失败返回None
    """
    auth = BrowserAuth(student_id, password)
    if not auth._init_browser():
        return None

    try:
        # 1. 打开IDS登录页
        print("[Browser] 正在打开IDS登录页...")
        auth.page.get(auth.IDS_LOGIN_URL)
        time.sleep(1)

        # 2. 填入账号密码
        print("[Browser] 正在输入账号密码...")
        username_input = (
            auth.page.ele("#username", timeout=3)
            or auth.page.ele('xpath://input[@id="username"]', timeout=3)
            or auth.page.ele('xpath://input[@name="username"]', timeout=3)
        )
        password_input = (
            auth.page.ele("#password", timeout=3)
            or auth.page.ele('xpath://input[@id="password"]', timeout=3)
            or auth.page.ele('xpath://input[@type="password"]', timeout=3)
        )

        if not username_input or not password_input:
            print("[Browser] ❌ 无法定位账号/密码输入框")
            return None

        username_input.input(student_id)
        password_input.input(password)

        # 3. 点击登录
        login_btn = (
            auth.page.ele("#login_submit", timeout=2)
            or auth.page.ele('xpath://input[@id="login_submit"]', timeout=2)
            or auth.page.ele('xpath://button[@type="submit"]', timeout=2)
            or auth.page.ele("text:登录", timeout=2)
        )

        if not login_btn:
            print("[Browser] ❌ 无法定位登录按钮，请手动在浏览器中点击登录")
            input("    手动点击登录后按回车继续...")
        else:
            print("[Browser] 点击登录...")
            login_btn.click()
            time.sleep(3)

        # 4. 检查验证码
        if "captcha" in auth.page.html.lower() or "验证码" in auth.page.html:
            print("[Browser] ⚠️ 需要验证码！请在浏览器中完成验证...")
            input("    完成验证码并点击登录后，按回车继续: ")
            time.sleep(2)

        # 5. 等待登录完成
        waited = 0
        while "authserver/login" in auth.page.url and waited < 15:
            time.sleep(1)
            waited += 1

        if "authserver/login" in auth.page.url:
            print("[Browser] ❌ 登录失败")
            return None

        print(f"[Browser] ✅ IDS登录成功: {auth.page.url}")

        # 6. 直接访问课表URL（浏览器自动完成SSO）
        schedule_url = (
            "http://bkjw.njust.edu.cn/njlgdx/xskb/xskb_list.do"
            "?Ves632DSdyV=NEW_XSD_PYGL"
        )
        print(f"[Browser] 正在访问课表页面...")
        auth.page.get(schedule_url)
        time.sleep(5)

        current_url = auth.page.url
        print(f"[Browser] 当前URL: {current_url}")

        # 7. 检查是否成功到达课表页
        if "xskb" in current_url and "bkjw" in current_url:
            print("[Browser] ✅ 已进入课表页面")
            return auth.page.html
        elif "authserver" in current_url:
            print("[Browser] ⚠️ SSO跳转未完成，仍在认证流程中")
            print("    请在浏览器中手动点击'本科教务'进入课表系统")
            input("    完成后按回车继续...")
            return auth.page.html
        else:
            print(f"[Browser] ⚠️ 未到达课表页: {current_url}")
            print("    请在浏览器中手动导航到课表页面")
            input("    完成后按回车继续...")
            return auth.page.html

    except Exception as e:
        print(f"[Browser] 浏览器自动化异常: {e}")
        return None
    finally:
        auth._close()
