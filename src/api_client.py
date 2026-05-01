"""
南京理工大学强智教务系统 API 客户端

封装强智 App API 的调用逻辑，包括：
- 登录获取 Token
- 获取当前学期/周次
- 获取课表数据
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Optional, Any


class QiangzhiClient:
    """
    强智教务系统客户端

    南理工已关闭 app.do JSON 接口，改为直接解析课表 HTML 页面。

    使用方式：
        # 先通过IDS拿到session/cookie
        from src.ids_auth import get_sso_session
        session = get_sso_session("学号", "密码")

        # 然后用session创建客户端
        client = QiangzhiClient("学号", session=session)
        html = client.get_schedule_page()
        courses = client.parse_schedule_html(html)
    """

    BASE_URL = "http://bkjw.njust.edu.cn"
    SCHEDULE_URL = (
        "http://bkjw.njust.edu.cn/njlgdx/xskb/xskb_list.do"
        "?Ves632DSdyV=NEW_XSD_PYGL"
    )

    def __init__(self, student_id: str, password: Optional[str] = None,
                 session: Optional[requests.Session] = None):
        self.student_id = student_id
        self.password = password

        if session is not None:
            self.session = session
        else:
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            })

    # ===================== 已废弃：app.do JSON 接口 =====================
    # 南理工的 app.do 接口已关闭（返回404），以下方法保留但不再使用

    def get_current_time(self, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        【已废弃】尝试获取当前学期/周次 —— 南理工 app.do 已关闭
        Fallback：使用配置中的开学日期手动计算
        """
        print("[API] ⚠️ app.do 接口已关闭，尝试从配置获取学期信息")
        try:
            from src.config import SEMESTER_START_DATE
            start = datetime.strptime(SEMESTER_START_DATE, "%Y-%m-%d")
            today = datetime.now()
            days_diff = (today - start).days
            if days_diff < 0:
                week = 0
            else:
                week = days_diff // 7 + 1
            return {
                "xnxqh": "2025-2026-2",
                "zc": week,
                "s_time": SEMESTER_START_DATE,
            }
        except Exception:
            return None

    def get_schedule(self, semester: str, week: int) -> List[Dict[str, Any]]:
        """【已废弃】app.do 课表接口已关闭"""
        print("[API] ⚠️ app.do getKbcxAzc 接口已关闭")
        return []

    def get_current_week_schedule(self) -> List[Dict[str, Any]]:
        """【已废弃】app.do 接口已关闭"""
        print("[API] ⚠️ app.do 接口已关闭，请使用 get_schedule_page() + parse_schedule_html()")
        return []

    # ===================== 新方法：HTML 页面抓取 =====================

    def get_schedule_page(self) -> Optional[str]:
        """
        直接请求课表HTML页面

        使用已携带IDS Cookie的session访问课表URL。
        SSO会自动在后台完成：强智系统发现未登录→302到IDS→IDS验证Cookie→
        签发Ticket→强智验证→返回课表页。

        Returns:
            课表页面的HTML文本
        """
        try:
            print(f"[API] 正在请求课表页面...")
            resp = self.session.get(
                self.SCHEDULE_URL,
                allow_redirects=True,
                timeout=20,
            )
            print(f"[API] 响应状态: {resp.status_code}, 最终URL: {resp.url}")

            if resp.status_code == 200:
                return resp.text
            else:
                print(f"[API] 请求失败: {resp.status_code}")
                return None

        except Exception as e:
            print(f"[API] 获取课表页面失败: {e}")
            return None

    def save_schedule_html(self, html: str, path: str) -> bool:
        """保存HTML到本地文件供调试分析"""
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"[API] HTML已保存: {path} ({len(html)} bytes)")
            return True
        except Exception as e:
            print(f"[API] 保存失败: {e}")
            return False

    def parse_schedule_html(self, html: str) -> List[Dict[str, Any]]:
        """
        解析课表HTML为结构化数据

        从强智教务系统的课表页面提取课程信息，适配南理工HTML结构。
        找到课程列表表格，解析每门课的名称、教师、时间、地点。
        """
        import re
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            print("[API] 缺少 BeautifulSoup4，请运行: pip install beautifulsoup4")
            return []

        soup = BeautifulSoup(html, "html.parser")
        courses = []

        # 查找所有表格
        tables = soup.find_all("table")
        if not tables:
            print("[API] ⚠️ 未找到课程表格")
            return courses

        # 找到课程列表表格（含"课程名称"和"时间"列）
        list_table = None
        for table in tables:
            header_row = table.find("tr")
            if not header_row:
                continue
            headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
            if "课程名称" in headers and "时间" in headers:
                list_table = table
                break

        if not list_table:
            print("[API] ⚠️ 未找到课程列表表格")
            return courses

        print(f"[API] 找到课程列表表格，开始解析...")

        # 南京理工大学江阴校区 — 小节时间映射
        # 每小节45分钟，小节之间课间5分钟，大节之间课间15分钟
        # 第14小节为网课占位符
        #
        # 第一大节：1~3小节，8:00~10:25
        # 第二大节：4~5小节，10:40~12:15
        # 第三大节：6~7小节，14:00~15:35
        # 第四大节：8~10小节，15:50~18:15
        # 第五大节：11~13小节，19:00~21:25
        JIE_START = {
            1: "08:00", 2: "08:50", 3: "09:40",
            4: "10:40", 5: "11:30",
            6: "14:00", 7: "14:50",
            8: "15:50", 9: "16:40", 10: "17:30",
            11: "19:00", 12: "19:50", 13: "20:40",
            14: "22:15",  # 网课占位符
        }
        JIE_END = {
            1: "08:45", 2: "09:35", 3: "10:25",
            4: "11:25", 5: "12:15",
            6: "14:45", 7: "15:35",
            8: "16:35", 9: "17:25", 10: "18:15",
            11: "19:45", 12: "20:35", 13: "21:25",
            14: "23:00",  # 网课占位符
        }

        weekday_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7}

        # 解析表格数据行（跳过表头）
        rows = list_table.find_all("tr")[1:]
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 8:
                continue

            texts = [c.get_text(strip=True) for c in cells]

            course_name = texts[3]   # 课程名称
            teacher = texts[4]       # 教师
            time_str = texts[5]      # 时间，如"星期三(04-05小节)星期五(02-03小节)"
            location_str = texts[7]  # 地点，如"江阴致远A104,江阴致远A104"

            if not course_name or not time_str:
                continue

            # 解析时间段
            # 格式: 星期X(XX-XX小节)
            pattern = r'星期([一二三四五六日])\((\d{2})-(\d{2})小节\)'
            matches = re.findall(pattern, time_str)

            # 解析地点（逗号分隔，与时间段一一对应）
            locations = [loc.strip() for loc in location_str.split(",") if loc.strip()]

            # 默认周数（全学期，后续可从周视图改进）
            weeks_str = "1-16"

            for i, (weekday_str, start_jie, end_jie) in enumerate(matches):
                weekday = weekday_map.get(weekday_str, 0)
                if weekday == 0:
                    continue

                start_jie_num = int(start_jie)
                end_jie_num = int(end_jie)

                # 构建kcsj编码: 星期 + 节次（每两位一组）
                kcsj = str(weekday)
                for j in range(start_jie_num, end_jie_num + 1):
                    kcsj += f"{j:02d}"

                # 地点
                loc = locations[i] if i < len(locations) else ""

                # 开始和结束时间
                start_time = JIE_START.get(start_jie_num, "08:00")
                end_time = JIE_END.get(end_jie_num, "09:35")

                courses.append({
                    "kcmc": course_name,
                    "jsxm": teacher,
                    "jsmc": loc,
                    "kcsj": kcsj,
                    "kkzc": weeks_str,
                    "kssj": start_time,
                    "jssj": end_time,
                })

        print(f"[API] 解析完成，共 {len(courses)} 个课程时间段")
        return courses


def parse_course_time(kcsj: str) -> tuple:
    """
    解析课程时间编码
    
    强智系统的 kcsj 字段编码规则：
    - 第1位: 星期几 (1-7)
    - 后续: 节次，每两位一组
    
    例如:
    - "10102" = 周一第1-2节
    - "30506" = 周三第5-6节
    
    Args:
        kcsj: 课程时间编码字符串
        
    Returns:
        (星期几, [节次列表])
    """
    if not kcsj or len(kcsj) < 3:
        return (0, [])
    
    weekday = int(kcsj[0])
    periods = []
    
    # 从第1位开始，每两位一组
    for i in range(1, len(kcsj), 2):
        if i + 1 < len(kcsj):
            period = int(kcsj[i:i+2])
            periods.append(period)
    
    return (weekday, periods)


def format_weekday(weekday: int) -> str:
    """将数字星期转换为中文"""
    weekdays = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return weekdays[weekday] if 1 <= weekday <= 7 else "未知"
