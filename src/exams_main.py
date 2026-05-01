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

    # 尝试简单提取表格内容
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.find_all("table")
        print(f"\n[Debug] 页面包含 {len(tables)} 个表格")
        for i, table in enumerate(tables[:3]):
            rows = table.find_all("tr")
            print(f"  表格#{i}: {len(rows)} 行")
            if rows:
                for j, row in enumerate(rows[:3]):
                    cells = row.find_all(["td", "th"])
                    texts = [c.get_text(strip=True) for c in cells]
                    if any(texts):
                        print(f"    行{j}: {texts}")
    except Exception as e:
        print(f"\n[Debug] 表格分析失败: {e}")


if __name__ == "__main__":
    main()
