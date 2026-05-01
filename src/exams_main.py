#!/usr/bin/env python3
"""
考试安排查询主入口

运行方式:
    python -m src.exams_main

流程:
1. IDS模拟登录（备用）
2. 浏览器门户方案（主力）
3. 获取考试安排HTML
4. 保存到桌面供分析 / 尝试解析

首次使用前:
    复制 src/config.example.py 到 src/config.py 并填入学号密码
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.exam_browser import get_exams_via_portal


def main():
    try:
        from src.config import STUDENT_ID, PASSWORD
    except ImportError:
        print("❌ 缺少配置文件")
        print("   请复制 src/config.example.py 到 src/config.py")
        print("   然后填入你的学号和密码")
        return

    print("=" * 60)
    print("📝 南京理工大学考试安排查询")
    print(f"🎓 学号: {STUDENT_ID}")
    print("=" * 60)

    print("\n[1/1] 通过门户获取考试安排...")
    print("   流程: 门户登录 → 教务系统 → 考试报名 → 查询")
    print("   请留意弹出的浏览器窗口\n")

    html = get_exams_via_portal(STUDENT_ID, PASSWORD)

    if not html:
        print("\n❌ 未能获取考试安排HTML")
        return

    # 检查是否有数据
    has_exam = (
        "考试时间" in html
        or "考试地点" in html
        or "座位号" in html
        or "考场" in html
        or "考试名称" in html
        or "课程名称" in html
    )

    if has_exam:
        print("\n✅ 考试安排HTML已获取")
        print("   文件保存: ~/Desktop/njust_exams_page.html")
        print("\n📋 接下来：")
        print("   1. 分析HTML结构")
        print("   2. 实现解析器")
        print("   3. 导出为JSON/文本")
    else:
        print("\n⚠️ 页面似乎不含考试数据")
        print("   可能原因：")
        print("   • 当前学期无考试安排")
        print("   • 需要在浏览器中完成更多操作")
        print("   • 页面结构需要手动确认")
        print("\n   HTML已保存到 ~/Desktop/njust_exams_page.html")
        print("   请查看文件内容确认实际状态")

    # 尝试解析
    try:
        from src.exam_parser import parse_exam_html, print_exams
        exams = parse_exam_html(html)
        print_exams(exams)

        # 保存为JSON
        import json
        # 跨平台获取桌面路径（中文Windows是"桌面"）
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(desktop_path):
            desktop_path = os.path.join(os.path.expanduser("~"), "桌面")
        json_path = os.path.join(desktop_path, "njust_exams.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(exams, f, ensure_ascii=False, indent=2)
        print(f"\n📄 考试数据已保存: {json_path}")

        # 同时更新webapp的考试数据
        webapp_exam_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "webapp", "data", "exams.json"
        )
        os.makedirs(os.path.dirname(webapp_exam_path), exist_ok=True)
        with open(webapp_exam_path, "w", encoding="utf-8") as f:
            json.dump(exams, f, ensure_ascii=False, indent=2)
        print(f"📄 PWA考试数据已更新: {webapp_exam_path}")

    except Exception as e:
        print(f"\n⚠️ 解析失败: {e}")
        print("   HTML已保存，可手动分析")


if __name__ == "__main__":
    main()
