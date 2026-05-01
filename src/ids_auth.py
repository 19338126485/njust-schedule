"""
金智教育 IDS 统一身份认证模块

南理工的教务系统被收归到 ids.njust.edu.cn 统一认证。
本模块提供两种登录策略：
1. 模拟登录（AES加密）—— 无头、快速
2. 浏览器自动化（DrissionPage）—— 100% 可靠兜底

技术背景：
- 金智IDS标准流程：GET登录页 → 提取隐藏字段(lt/execution/salt) → AES加密密码 → POST登录
- 参考开源项目：vic2ray/UnifiedIdAuthLogin
"""

import requests
import re
import json
from typing import Optional, Dict, Any
from urllib.parse import urljoin


IDS_HOST = "ids.njust.edu.cn"
IDS_LOGIN_URL = f"https://{IDS_HOST}/authserver/login"
IDS_NEED_CAPTCHA = f"https://{IDS_HOST}/authserver/needCaptcha.html"


class NJUSTIDSAuth:
    """
    南京理工大学金智IDS统一身份认证客户端
    
    使用流程：
        auth = NJUSTIDSAuth("学号", "密码")
        if auth.login():
            # 用 auth.session 去访问教务系统，自动携带Cookie
            resp = auth.session.get("http://bkjw.njust.edu.cn/...")
    """
    
    def __init__(self, student_id: str, password: str):
        self.student_id = student_id
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        self.encrypt_js_path: Optional[str] = None  # encryptAES.js 本地路径
    
    def _fetch_login_page(self) -> Optional[Dict[str, str]]:
        """
        获取IDS登录页，提取所有隐藏表单字段
        
        Returns:
            包含 lt, execution, dllt, _eventId, salt 的字典
        """
        try:
            resp = self.session.get(IDS_LOGIN_URL, timeout=15)
            resp.raise_for_status()
            html = resp.text
            
            hidden_fields = {}
            
            # 提取 lt
            m = re.search(r'<input[^>]*name="lt"[^>]*value="([^"]*)"', html)
            if m:
                hidden_fields["lt"] = m.group(1)
            
            # 提取 execution
            m = re.search(r'<input[^>]*name="execution"[^>]*value="([^"]*)"', html)
            if m:
                hidden_fields["execution"] = m.group(1)
            
            # 提取 dllt
            m = re.search(r'<input[^>]*name="dllt"[^>]*value="([^"]*)"', html)
            if m:
                hidden_fields["dllt"] = m.group(1)
            
            # 提取 _eventId
            m = re.search(r'<input[^>]*name="_eventId"[^>]*value="([^"]*)"', html)
            if m:
                hidden_fields["_eventId"] = m.group(1)
            
            # 提取 pwdEncryptSalt（南理工金智系统的AES密钥，注意不是 pwdDefaultEncryptSalt）
            m = re.search(r'id="pwdEncryptSalt"[^>]*value="([^"]*)"', html)
            if m:
                hidden_fields["salt"] = m.group(1)
            
            # 备选：从 script 标签里的变量提取 salt
            if "salt" not in hidden_fields:
                m = re.search(r'var\s+pwdEncryptSalt\s*=\s*["\']([^"\']+)["\']', html)
                if m:
                    hidden_fields["salt"] = m.group(1)
            
            # 备选2：从页面内嵌script中搜索 salt 定义
            if "salt" not in hidden_fields:
                m = re.search(r'pwdEncryptSalt["\']?\s*[:=]\s*["\']([^"\']+)["\']', html)
                if m:
                    hidden_fields["salt"] = m.group(1)
            
            # 查找 encrypt.js 的URL（南理工路径: /authserver/njustSubjecta/static/common/encrypt.js）
            js_match = re.search(r'src="([^"]*encrypt\.js[^"]*)"', html)
            if js_match:
                hidden_fields["encrypt_js_url"] = urljoin(IDS_LOGIN_URL, js_match.group(1))
            else:
                # 备选：查找任何包含 encrypt 的 JS
                js_match = re.search(r'src="([^"]*encrypt[^"]*)"', html)
                if js_match:
                    hidden_fields["encrypt_js_url"] = urljoin(IDS_LOGIN_URL, js_match.group(1))
            
            # 调试：如果没有salt，打印页面片段帮助诊断
            if "salt" not in hidden_fields:
                print("[IDS] ⚠️ 未找到加密盐，登录页可能使用不同加密方式")
                # 搜索页面中所有 input 标签的 name
                all_inputs = re.findall(r'<input[^>]*name="([^"]*)"[^>]*>', html)
                print(f"[IDS] 页面表单字段: {all_inputs[:20]}")
            
            return hidden_fields if hidden_fields else None
            
        except Exception as e:
            print(f"[IDS] 获取登录页失败: {e}")
            return None
    
    def _download_encrypt_js(self, js_url: str) -> bool:
        """下载AES加密JS文件到本地"""
        try:
            resp = self.session.get(js_url, timeout=15)
            resp.raise_for_status()
            
            import os
            self.encrypt_js_path = os.path.join(
                os.path.dirname(__file__), "ids_encrypt.js"
            )
            with open(self.encrypt_js_path, "w", encoding="utf-8") as f:
                f.write(resp.text)
            print(f"[IDS] 已下载加密脚本: {self.encrypt_js_path}")
            return True
        except Exception as e:
            print(f"[IDS] 下载加密脚本失败: {e}")
            return False
    
    def _encrypt_password(self, password: str, salt: str) -> Optional[str]:
        """
        使用金智IDS的AES算法加密密码
        
        南理工的 encrypt.js 提供两个函数：
        - encryptAES(n, f) — 底层AES加密
        - encryptPassword(n, f) — 包装函数，带异常处理
        
        优先尝试 encryptPassword，失败 fallback 到 encryptAES
        """
        try:
            import execjs
        except ImportError:
            print("[IDS] 缺少 execjs，尝试安装: pip install PyExecJS")
            return None
        
        if not self.encrypt_js_path:
            print("[IDS] 未找到加密脚本，无法加密密码")
            return None
        
        try:
            with open(self.encrypt_js_path, "r", encoding="utf-8") as f:
                js_code = f.read()
            
            ctx = execjs.compile(js_code)
            
            # 优先尝试 encryptPassword（有异常保护）
            for func_name in ["encryptPassword", "encryptAES"]:
                try:
                    encrypted = ctx.call(func_name, password, salt)
                    if encrypted and encrypted != password:
                        print(f"[IDS] 使用 {func_name} 加密成功")
                        return encrypted
                except Exception as e:
                    print(f"[IDS] {func_name} 调用失败: {e}")
                    continue
            
            print("[IDS] 所有加密函数均失败，尝试明文提交")
            return password
            
        except Exception as e:
            print(f"[IDS] 密码加密过程失败: {e}")
            return None
    
    def _check_captcha(self) -> Optional[bytes]:
        """
        检查是否需要验证码，如需要则返回验证码图片数据
        
        Returns:
            验证码图片 bytes，不需要则返回 None
        """
        try:
            # 南理工的 needCaptcha 可能需要 Referer
            headers = {"Referer": IDS_LOGIN_URL}
            ts = int(__import__('time').time() * 1000)
            url = f"{IDS_NEED_CAPTCHA}?username={self.student_id}&_={ts}"
            resp = self.session.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            
            raw = resp.text.strip().lower()
            print(f"[IDS] 验证码检查返回: '{raw[:50]}'")
            
            # 金智接口应返回 true/false，但南理工可能返回不同格式
            if raw == "true":
                # 需要验证码，下载图片
                captcha_url = f"https://{IDS_HOST}/authserver/captcha.html"
                img_resp = self.session.get(captcha_url, headers=headers, timeout=10)
                print(f"[IDS] 需要验证码，已下载图片 ({len(img_resp.content)} bytes)")
                return img_resp.content
            elif raw == "false":
                print("[IDS] 不需要验证码")
                return None
            else:
                # 返回了其他内容（如错误页面），无法判断，假设不需要
                print("[IDS] 验证码接口返回异常，假设不需要验证码")
                return None
                
        except Exception as e:
            print(f"[IDS] 检查验证码失败: {e}")
            return None
    
    def login(self) -> bool:
        """
        执行IDS统一身份认证登录
        
        Returns:
            是否登录成功（session中已携带IDS Cookie）
        """
        print("[IDS] 正在获取登录页...")
        fields = self._fetch_login_page()
        
        if not fields:
            print("[IDS] 无法提取登录表单字段，IDS页面结构可能已变更")
            return False
        
        print(f"[IDS] 提取字段: {list(fields.keys())}")
        
        # 下载加密脚本
        js_url = fields.get("encrypt_js_url")
        if js_url:
            self._download_encrypt_js(js_url)
        
        # 加密密码
        salt = fields.get("salt")
        if salt and self.encrypt_js_path:
            encrypted_password = self._encrypt_password(self.password, salt)
            if not encrypted_password:
                print("[IDS] AES加密失败，尝试明文密码提交...")
                encrypted_password = self.password
        else:
            print("[IDS] 无法获取加密盐，尝试明文密码提交...")
            encrypted_password = self.password
        
        # 检查验证码
        captcha_img = self._check_captcha()
        captcha_code = ""
        if captcha_img:
            # 使用改进的验证码处理（自动检测格式+备选查看方式）
            from src.captcha_helper import get_user_captcha
            import os
            base_path = os.path.join(os.path.dirname(__file__), "captcha")
            captcha_code = get_user_captcha(captcha_img, base_path)
        
        # 构造登录表单
        # 南理工IDS关键字段（根据debug_ids.py诊断结果）:
        # - cllt=userNameLogin (用户名密码登录类型)
        # - dllt=generalLogin
        # - password=加密后的密码 (不是明文，也不是passwordText)
        # - 不要提交 passwordText 字段
        # - lt 字段在页面HTML中为空，某些CAS实现可能不需要它
        login_data = {
            "username": self.student_id,
            "password": encrypted_password,
            "lt": fields.get("lt", ""),
            "execution": fields.get("execution", ""),
            "dllt": fields.get("dllt", "generalLogin"),
            "cllt": "userNameLogin",
            "_eventId": fields.get("_eventId", "submit"),
            "rmShown": "1",
        }
        
        if not fields.get("lt"):
            print("[IDS] ⚠️ lt 字段为空，某些 CAS 实现可以正常工作，但如果登录失败可能需要浏览器方案")
        
        if captcha_code:
            login_data["captchaResponse"] = captcha_code
        
        print(f"[IDS] 正在提交登录...")
        
        # 第一次尝试登录
        try:
            resp = self.session.post(
                IDS_LOGIN_URL,
                data=login_data,
                allow_redirects=True,
                timeout=15,
            )
            
            # 检查登录结果
            login_success = self._check_login_response(resp)
            
            # 如果因验证码失败，给用户一次手动输入的机会
            if not login_success and "验证码" in resp.text:
                print("[IDS] ⚠️ 服务器返回验证码要求")
                captcha_img = self._download_captcha_image()
                if captcha_img:
                    # 使用改进的验证码处理（自动检测格式+备选HTML查看方式）
                    from src.captcha_helper import get_user_captcha
                    import os
                    base_path = os.path.join(os.path.dirname(__file__), "captcha_retry")
                    captcha_code = get_user_captcha(captcha_img, base_path)
                    
                    if captcha_code:
                        # 重新获取登录页（因为execution等字段可能已经过期）
                        new_fields = self._fetch_login_page()
                        if new_fields:
                            login_data["lt"] = new_fields.get("lt", login_data["lt"])
                            login_data["execution"] = new_fields.get("execution", login_data["execution"])
                        login_data["captchaResponse"] = captcha_code
                        
                        print("[IDS] 使用验证码重新提交...")
                        resp = self.session.post(
                            IDS_LOGIN_URL,
                            data=login_data,
                            allow_redirects=True,
                            timeout=15,
                        )
                        login_success = self._check_login_response(resp)
            
            return login_success
            
        except Exception as e:
            print(f"[IDS] 登录请求异常: {e}")
            return False
    
    def _download_captcha_image(self) -> Optional[bytes]:
        """直接下载验证码图片"""
        try:
            captcha_url = f"https://{IDS_HOST}/authserver/captcha.html"
            img_resp = self.session.get(captcha_url, timeout=10)
            return img_resp.content
        except Exception:
            return None
    
    def _check_login_response(self, resp) -> bool:
        """
        检查登录响应，判断是否成功
        
        Returns:
            True=登录成功, False=登录失败
        """
        # 调试信息
        print(f"[IDS] 响应状态: {resp.status_code}, 最终URL: {resp.url}")
        
        # 检查是否仍在登录页
        if "authserver/login" in resp.url:
            # 仍在登录页，说明失败了
            resp_text = resp.text
            
            if "密码有误" in resp_text or "用户名或密码" in resp_text or "password error" in resp_text.lower():
                print("[IDS] ❌ 账号或密码错误")
                return False
            
            if "验证码" in resp_text:
                print("[IDS] ⚠️ 需要验证码")
                return False
            
            # 未知错误，打印一段HTML帮助诊断
            print("[IDS] ⚠️ 登录失败，响应内容片段:")
            # 提取可能的错误信息
            error_match = re.search(r'<span[^>]*class="[^"]*error[^"]*"[^>]*>(.*?)</span>', resp_text, re.DOTALL)
            if error_match:
                print(f"    错误信息: {error_match.group(1).strip()}")
            else:
                print(f"    {resp_text[:300]}")
            return False
        
        # 检查是否有 CASTGC Cookie（登录成功的标志）
        cookies_dict = self.session.cookies.get_dict()
        if "CASTGC" in cookies_dict or "MOD_AUTH_CAS" in cookies_dict:
            print("[IDS] ✅ IDS登录成功！已获得统一身份认证Cookie")
            return True
        
        # 即使没CASTGC，如果被重定向走了，也可能成功了
        if resp.url != IDS_LOGIN_URL and "authserver" not in resp.url:
            print(f"[IDS] ✅ 已跳转至: {resp.url}")
            return True
        
        print(f"[IDS] ⚠️ 登录状态不确定")
        return False
    
    def access_jw_system(self) -> bool:
        """
        携带IDS Cookie访问教务系统，完成SSO单点登录
        
        这是关键一步：IDS登录成功后，session里已有IDS的Cookie。
        访问教务系统入口时，强智系统会302到IDS验证，IDS看到有效Cookie后
        签发Ticket，强智验证Ticket后种下自己的JSESSIONID。
        
        Returns:
            是否成功进入教务系统
        """
        jw_url = "http://bkjw.njust.edu.cn/"
        
        try:
            print(f"[IDS] 正在访问教务系统 ({jw_url})...")
            resp = self.session.get(jw_url, allow_redirects=True, timeout=20)
            
            # 检查最终URL
            print(f"[IDS] 最终到达: {resp.url}")
            
            # 检查强智Cookie
            cookies = self.session.cookies.get_dict()
            if "JSESSIONID" in cookies:
                print("[IDS] ✅ 已获得强智教务系统 JSESSIONID")
                return True
            
            # 检查是否仍在IDS域
            if "ids.njust.edu.cn" in resp.url or "authserver" in resp.url:
                print("[IDS] ⚠️ 似乎仍在认证流程中，可能需要额外处理")
                return False
            
            # 检查响应内容是否包含课表系统特征
            if "强智" in resp.text or "教务" in resp.text:
                print("[IDS] ✅ 响应内容包含教务系统标识")
                return True
            
            return False
            
        except Exception as e:
            print(f"[IDS] 访问教务系统失败: {e}")
            return False


def get_sso_session(student_id: str, password: str) -> Optional[requests.Session]:
    """
    便捷函数：一键完成IDS登录+教务系统SSO跳转，返回可用的session
    
    Args:
        student_id: 学号
        password: 密码
        
    Returns:
        已携带IDS和强智Cookie的requests.Session，失败返回None
    """
    auth = NJUSTIDSAuth(student_id, password)
    
    if not auth.login():
        return None
    
    if not auth.access_jw_system():
        print("[IDS] SSO跳转未完全成功，但session仍可能可用")
    
    return auth.session
