"""
考试安排查询：通过智慧理工门户获取考试信息

流程：
1. 门户登录 → 进入强智系统（复用 portal_browser 的通用流程）
2. 在强智主页点击"考试报名"
3. 等待导航到考试报名页面
4. 点击"查询"
5. 获取考试安排HTML
"""

import os
import time
from typing import Optional

from .portal_browser import (
    enter_qiangzhi_system,
    find_and_click,
    _poll_url_change,
    _get_tab_by_url,
)


def get_exams_via_portal(student_id: str, password: str) -> Optional[str]:
    """通过智慧理工门户获取考试安排HTML"""
    browser_page, active_page = enter_qiangzhi_system(student_id, password, prefix="[Exam]")
    if not browser_page or not active_page:
        return None

    try:
        # Step 5: 在强智主页点击"考试报名"
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

        # Step 6: 点击"查询"按钮
        print("[Exam] 正在查找'查询'按钮...")
        time.sleep(2)

        query_clicked = False
        try:
            btn = active_page.ele("#btn_query", timeout=3)
            if btn:
                print("[Exam] 找到查询按钮 #btn_query")
                btn.click()
                query_clicked = True
                time.sleep(3)
        except:
            pass

        if not query_clicked:
            # fallback: 执行JS函数
            try:
                active_page.run_js("queryKsap()")
                print("[Exam] 通过JS调用 queryKsap()")
                query_clicked = True
                time.sleep(3)
            except Exception as e:
                print(f"[Exam] JS调用失败: {e}")

        if not query_clicked:
            print("[Exam] 未自动触发查询")
            print("    请在浏览器中手动点击'查询'按钮")
            input("    完成后按回车继续: ")
        else:
            print("[Exam] 已触发查询，等待结果加载...")

        # 等待表单提交和页面加载（POST到 xsksap_list）
        time.sleep(5)

        # 检查URL是否变成了列表页
        ok, url = _poll_url_change(active_page, ["xsksap_list"], timeout_sec=15)
        if ok:
            print(f"[Exam] 查询结果页: {url}")
        else:
            print(f"[Exam] 当前URL: {active_page.url}")
            # 即使URL没变，也可能通过AJAX加载了数据

        # Step 7: 获取最终HTML
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
        # 跨平台获取桌面路径
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(desktop_path):
            desktop_path = os.path.join(os.path.expanduser("~"), "桌面")
        save_path = os.path.join(desktop_path, "njust_exams_page.html")
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
        try:
            browser_page.quit()
        except:
            pass
        return None
