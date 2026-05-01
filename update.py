#!/usr/bin/env python3
"""
一键更新脚本

用法：
    python update.py          # 命令行
    双击 update.bat           # Windows 图形界面

自动完成：
1. IDS登录 → 抓取课表 → 保存 schedule.json
2. 浏览器抓取考试 → 保存 exams.json
3. git add → commit → push
4. GitHub Pages 自动部署（约30秒）
"""

import sys
import os
import subprocess
import json
import time

# 把项目根目录加入路径
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from src.config import STUDENT_ID, PASSWORD


def update_schedule():
    """抓取课表并保存（优先requests，失败则用浏览器兜底）"""
    print("\n" + "=" * 60)
    print("📚 正在抓取课表...")
    print("=" * 60)

    html = None
    courses = None

    # 尝试1: requests IDS登录
    print("[Update] 尝试 requests IDS 登录...")
    from src.ids_auth import NJUSTIDSAuth
    auth = NJUSTIDSAuth(STUDENT_ID, PASSWORD)
    if auth.login():
        print("[Update] IDS登录成功，尝试请求课表...")
        from src.api_client import QiangzhiClient
        client = QiangzhiClient(STUDENT_ID, session=auth.session)
        html = client.get_schedule_page()
        if html:
            courses = client.parse_schedule_html(html)
            if courses:
                print(f"✅ requests方式解析到 {len(courses)} 门课程")

    # 尝试2: 浏览器兜底（当requests方式失败时）
    if not courses:
        print("[Update] requests方式未获取到课表，启动浏览器兜底...")
        from src.portal_browser import get_schedule_via_portal
        html = get_schedule_via_portal(STUDENT_ID, PASSWORD)
        if html:
            from src.api_client import QiangzhiClient
            client = QiangzhiClient(STUDENT_ID)
            courses = client.parse_schedule_html(html)
            if courses:
                print(f"✅ 浏览器方式解析到 {len(courses)} 门课程")

    if not courses:
        print("❌ 课表抓取全部失败（requests + 浏览器）")
        return False

    # 保存到 webapp 和 docs
    for rel_path in ["webapp/data/schedule.json", "docs/data/schedule.json"]:
        full = os.path.join(project_dir, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            json.dump(courses, f, ensure_ascii=False, indent=2)
        print(f"   已保存: {rel_path}")

    return True


def update_exams():
    """抓取考试安排并保存"""
    print("\n" + "=" * 60)
    print("📋 正在抓取考试安排...")
    print("=" * 60)

    from src.exam_browser import get_exams_via_portal
    from src.exam_parser import parse_exam_html

    html = get_exams_via_portal(STUDENT_ID, PASSWORD)
    if not html:
        print("❌ 考试抓取失败")
        return False

    # 解析
    exams = parse_exam_html(html)
    print(f"✅ 解析到 {len(exams)} 场考试")

    # 保存到 webapp 和 docs
    for rel_path in ["webapp/data/exams.json", "docs/data/exams.json"]:
        full = os.path.join(project_dir, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            json.dump(exams, f, ensure_ascii=False, indent=2)
        print(f"   已保存: {rel_path}")

    return True


def git_push():
    """推送到 GitHub"""
    print("\n" + "=" * 60)
    print("🚀 推送到 GitHub Pages...")
    print("=" * 60)

    os.chdir(project_dir)

    # add
    subprocess.run(
        ["git", "add", "-A"],
        capture_output=True, encoding="utf-8", errors="replace"
    )

    # 检查是否有变更
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        capture_output=True, encoding="utf-8", errors="replace"
    )
    if diff.returncode == 0:
        print("ℹ️ 没有数据变更，无需推送")
        return True

    # commit
    now = time.strftime("%Y-%m-%d %H:%M")
    result = subprocess.run(
        ["git", "commit", "-m", f"update: {now} 自动更新课表和考试"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        err = result.stderr.strip() if result.stderr else "未知错误"
        print(f"❌ Git commit 失败: {err}")
        return False
    print(f"✅ Git commit: {now}")

    # push
    result = subprocess.run(
        ["git", "push", "origin", "main"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        err = result.stderr.strip() if result.stderr else "未知错误"
        print(f"❌ Git push 失败: {err}")
        return False

    print("✅ 推送成功！")
    return True


def main():
    print("🎓 南理工课表一键更新")
    print(f"   学号: {STUDENT_ID}")
    print("   流程: 课表 → 考试 → GitHub Pages")

    ok_schedule = update_schedule()
    ok_exams = update_exams()

    if ok_schedule or ok_exams:
        git_push()
        print("\n" + "=" * 60)
        print("🎉 更新完成！")
        print("   手机上刷新即可看到最新数据:")
        print("   https://19338126485.github.io/njust-schedule/")
        print("=" * 60)
    else:
        print("\n⚠️ 抓取全部失败，未推送")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
