#!/usr/bin/env python3
"""
课表抓取测试脚本（支持金智IDS统一认证 + HTML解析）

运行方式:
    python -m src.main

认证流程:
1. 先尝试IDS模拟登录（无头、快速）
2. 失败则 fallback 到浏览器自动化（DrissionPage）
3. 拿到IDS Cookie后，直接请求课表HTML页面并解析

首次使用前:
1. 复制 src/config.example.py 到 src/config.py
2. 在 src/config.py 中填入你的学号、密码、开学日期
3. 可选: pip install -r requirements.txt
"""

import sys
import os

# 确保可以从项目根目录导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api_client import QiangzhiClient, parse_course_time, format_weekday
from src.ics_exporter import quick_export


def print_schedule_table(courses):
    """以表格形式打印课表"""
    if not courses:
        print("本周没有课程（或获取失败）")
        return

    print(f"\n{'='*60}")
    print(f"本周课表（共 {len(courses)} 门课程）")
    print(f"{'='*60}")

    # 按星期几分组
    by_day = {i: [] for i in range(1, 8)}

    for c in courses:
        kcsj = c.get("kcsj", "")
        weekday, periods = parse_course_time(kcsj)
        if weekday:
            by_day[weekday].append(c)

    # 按星期几输出
    for day in range(1, 8):
        day_courses = by_day[day]
        if not day_courses:
            continue

        print(f"\n📅 {format_weekday(day)}")
        print("-" * 50)

        # 按节次排序
        day_courses.sort(
            key=lambda c: parse_course_time(c.get("kcsj", ""))[1][0]
            if parse_course_time(c.get("kcsj", ""))[1] else 0
        )

        for c in day_courses:
            kcmc = c.get("kcmc", "未知课程")
            jsmc = c.get("jsmc", "未知教室")
            jsxm = c.get("jsxm", "未知教师")
            kssj = c.get("kssj", "")
            jssj = c.get("jssj", "")
            kkzc = c.get("kkzc", "")

            _, periods = parse_course_time(c.get("kcsj", ""))
            period_str = (
                f"第{periods[0]}-{periods[-1]}节"
                if len(periods) > 1 else f"第{periods[0]}节"
            )

            time_str = f" ({kssj}-{jssj})" if kssj and jssj else ""

            print(f"  ⏰ {period_str}{time_str}")
            print(f"     📖 {kcmc}")
            print(f"     🏫 {jsmc} | 👨‍🏫 {jsxm}")
            print(f"     📅 开课周次: {kkzc}")


def try_ids_login(student_id: str, password: str):
    """尝试IDS模拟登录"""
    try:
        from src.ids_auth import get_sso_session
        print("\n[1/2] 尝试IDS模拟登录（无头模式）...")
        session = get_sso_session(student_id, password)
        if session:
            return True, session
        return False, None
    except Exception as e:
        print(f"[IDS] 模拟登录异常: {e}")
        return False, None


def try_browser_login(student_id: str, password: str):
    """浏览器自动化兜底登录"""
    try:
        from src.browser_auth import get_cookies_via_browser
        print("\n[Browser] 启动Edge浏览器完成SSO登录...")
        print("    请留意弹出的浏览器窗口，如有验证码请在浏览器中手动处理")

        cookies = get_cookies_via_browser(student_id, password, headless=False)
        if not cookies:
            return False, None

        import requests
        session = requests.Session()
        for k, v in cookies.items():
            session.cookies.set(k, v)

        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            ),
        })

        return True, session

    except Exception as e:
        print(f"[Browser] 浏览器登录异常: {e}")
        return False, None


def get_week_from_start_date(start_date: str) -> int:
    """根据开学日期计算当前是第几周"""
    from datetime import datetime
    start = datetime.strptime(start_date, "%Y-%m-%d")
    today = datetime.now()
    days_diff = (today - start).days
    if days_diff < 0:
        return 0
    return days_diff // 7 + 1


def main():
    """主函数"""
    print("=" * 60)
    print("南京理工大学课表抓取工具")
    print("（适配金智IDS + HTML课表解析）")
    print("=" * 60)

    # 导入配置
    try:
        from src.config import STUDENT_ID, PASSWORD, BASE_URL, SEMESTER_START_DATE
        if STUDENT_ID == "你的学号" or PASSWORD == "你的密码":
            print("\n⚠️  请先在 src/config.py 中填入你的学号和密码！")
            print("   复制 src/config.example.py → src/config.py，然后编辑。")
            return
    except ImportError:
        print("\n⚠️  配置文件未找到！")
        print("   请复制 src/config.example.py → src/config.py，填入你的信息。")
        return

    print(f"\n🎓 学号: {STUDENT_ID}")

    # ---------- 认证阶段 ----------
    session = None

    # 第1步：尝试IDS模拟登录
    ids_ok, session = try_ids_login(STUDENT_ID, PASSWORD)

    # 第2步：失败则用浏览器兜底
    if not ids_ok:
        print("\n⚠️  IDS模拟登录未成功，准备使用浏览器自动化方案...")
        choice = input("是否启动Edge浏览器完成登录？(y/n): ").strip().lower()

        if choice == 'y':
            browser_ok, session = try_browser_login(STUDENT_ID, PASSWORD)
            if not browser_ok:
                print("\n❌ 浏览器方案也失败了，无法继续获取课表")
                return
        else:
            print("\n已取消，退出。")
            return

    print("\n✅ 认证完成！已获得教务系统访问权限")

    # ---------- 获取课表HTML ----------
    print("📡 正在连接教务系统课表页面...")
    client = QiangzhiClient(STUDENT_ID, session=session)

    # 请求课表页面
    html = client.get_schedule_page()

    if not html:
        print("❌ 无法获取课表页面")
        print("   可能原因：")
        print("   • Cookie已过期，需要重新登录")
        print("   • 教务系统维护中")
        print("   • 网络问题")
        return

    # 检测返回的是否是登录页（SSO未完成）
    is_login = (
        "authserver/login" in html
        or "pwdEncryptSalt" in html
        or "统一身份认证" in html
        or 'name="passwordText"' in html.lower()
        # 强智系统自己的登录页特征
        or "Verifyservlet" in html
        or 'name="USERNAME"' in html
        or 'name="PASSWORD"' in html
        or "请先登录系统" in html
        or "RANDOMCODE" in html
        or "登录个人中心" in html
    )

    if is_login:
        print("\n⚠️  requests SSO未成功，返回的是登录页面")
        print("   切换到智慧理工门户方案（门户→强智票据跳转）...")
        from src.portal_browser import get_schedule_via_portal
        html = get_schedule_via_portal(STUDENT_ID, PASSWORD)

        if not html:
            print("❌ 门户方案也未能获取课表")
            return
        
        # 再次检查浏览器返回的HTML是否真的是课表
        still_login = (
            "Verifyservlet" in html
            or 'name="USERNAME"' in html
            or "请先登录系统" in html
            or "登录个人中心" in html
        )
        if still_login:
            print("⚠️  浏览器返回的仍是登录页，SSO跳转未完成")
            print("   请检查浏览器中的状态")
            return

    # 保存HTML供分析
    html_path = os.path.expanduser("~/Desktop/njust_schedule_page.html")
    client.save_schedule_html(html, html_path)

    print(f"\n📄 HTML已保存，你可以用浏览器打开查看: {html_path}")

    # ---------- 尝试解析课表 ----------
    print("\n🔍 正在尝试解析课表数据...")
    courses = client.parse_schedule_html(html)

    if courses:
        print(f"✅ 解析成功！共 {len(courses)} 门课程")
        print_schedule_table(courses)
    else:
        print("⚠️  解析未成功（HTML结构需要进一步分析）")
        print("   请把保存的HTML文件贴给我，我来写解析器")

    # ---------- 学期/周次信息 ----------
    week = get_week_from_start_date(SEMESTER_START_DATE)
    print(f"\n📅 根据开学日期计算: 当前是第 {week} 周")

    # ---------- 导出ICS ----------
    if courses:
        print(f"\n{'='*60}")
        choice = input("是否导出为 ICS 日历文件？(y/n): ").strip().lower()

        if choice == 'y':
            export_all = input("导出全部周次还是仅本周？(all/week): ").strip().lower()
            week_filter = None if export_all == 'all' else week

            output_path = os.path.expanduser("~/Desktop/njust_schedule.ics")
            print(f"\n📤 正在导出到 {output_path}...")

            success = quick_export(
                courses=courses,
                output_path=output_path,
                semester_start=SEMESTER_START_DATE,
                week=week_filter
            )

            if success:
                print(f"✅ 导出成功！")
                print(f"   文件位置: {output_path}")
            else:
                print("❌ 导出失败")

    print(f"\n{'='*60}")
    print("完成！")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
