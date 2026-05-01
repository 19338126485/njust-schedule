"""
考试安排HTML解析器

解析强智系统考试安排查询结果页（xsksap_list）
提取：课程名称、考试时间、考场、座位号、考试场次
"""

from typing import List, Dict, Any
import re


def parse_exam_html(html: str) -> List[Dict[str, Any]]:
    """解析考试安排HTML为结构化数据"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("[ExamParser] 缺少 BeautifulSoup4")
        return []

    soup = BeautifulSoup(html, "html.parser")
    exams = []

    # 尝试多种表格选择器
    table = (
        soup.select_one("table#dataList")
        or soup.select_one("table.Nsb_table")
        or soup.select_one("table.Nsb_r_list")
    )

    if not table:
        print("[ExamParser] ⚠️ 未找到考试数据表格")
        return exams

    rows = table.find_all("tr")
    if len(rows) < 2:
        print("[ExamParser] ⚠️ 表格行数不足（无数据）")
        return exams

    # 表头行（第一行）
    header_row = rows[0]
    headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
    print(f"[ExamParser] 表头: {headers}")

    # 数据行（从第二行开始）
    for row in rows[1:]:
        cells = row.find_all("td")
        if not cells:
            continue

        texts = [c.get_text(strip=True) for c in cells]
        if not texts or not any(texts):
            continue

        # 根据表头映射字段
        exam = {}
        for i, text in enumerate(texts):
            if i < len(headers):
                header = headers[i]
                if "序号" in header:
                    exam["index"] = text
                elif "考试场次" in header:
                    exam["exam_code"] = text
                elif "课程编号" in header:
                    exam["course_code"] = text
                elif "课程名称" in header:
                    exam["course_name"] = text
                elif "考试时间" in header:
                    exam["exam_time"] = text
                    # 拆分日期和时间范围
                    match = re.match(r"(\d{4}-\d{2}-\d{2})\s+(.+?)(?:~|—|-)(.+)", text)
                    if match:
                        exam["date"] = match.group(1)
                        exam["start_time"] = match.group(2).strip()
                        exam["end_time"] = match.group(3).strip()
                elif "考场" in header:
                    exam["room"] = text
                elif "座位号" in header:
                    exam["seat"] = text
                else:
                    exam[f"field_{i}"] = text
            else:
                exam[f"field_{i}"] = text

        if exam.get("course_name"):
            exams.append(exam)

    print(f"[ExamParser] 解析完成: {len(exams)} 条考试记录")
    return exams


def print_exams(exams: List[Dict[str, Any]]) -> None:
    """打印考试安排表格"""
    if not exams:
        print("暂无考试安排")
        return

    print("\n" + "=" * 80)
    print(f"{'序号':<4} {'课程名称':<30} {'考试时间':<22} {'考场':<14} {'座位号':<6}")
    print("-" * 80)

    for e in exams:
        name = e.get("course_name", "")[:28]
        time_str = e.get("exam_time", "")[:20]
        room = e.get("room", "")[:12]
        seat = e.get("seat", "")
        idx = e.get("index", "")
        print(f"{idx:<4} {name:<30} {time_str:<22} {room:<14} {seat:<6}")

    print("=" * 80)
