"""
ICS 日历文件导出器

将课表数据导出为 .ics 格式，可导入：
- Apple 日历 / iOS 日历
- Google 日历
- Outlook
- 任何支持 ICS 的日历应用

特性：
- 自动根据单双周重复
- 包含教室、教师信息
- 课前提醒
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re


class ICSExporter:
    """ICS 日历文件导出器"""
    
    def __init__(self, semester_start_date: Optional[str] = None):
        """
        Args:
            semester_start_date: 开学第一周周一日期 YYYY-MM-DD
        """
        self.semester_start = None
        if semester_start_date:
            self.semester_start = datetime.strptime(semester_start_date, "%Y-%m-%d")
    
    def _parse_weeks(self, week_str: str) -> List[int]:
        """
        解析上课周次字符串
        
        支持的格式：
        - "1-16" → [1,2,3,...,16]
        - "1,3,5,7" → [1,3,5,7]
        - "2-16双" → [2,4,6,...,16]
        - "1-15单" → [1,3,5,...,15]
        
        Args:
            week_str: 周次字符串，如 "1-16"、"2,4,6"
            
        Returns:
            周次数字列表
        """
        weeks = []
        week_str = week_str.strip()
        
        if not week_str:
            return weeks
        
        # 判断单双周
        is_single = "单" in week_str
        is_double = "双" in week_str
        
        # 移除中文标记
        week_str = week_str.replace("单", "").replace("双", "").strip()
        
        # 分割逗号分隔的部分
        parts = week_str.split(",")
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            if "-" in part:
                # 范围如 "1-16"
                try:
                    start, end = part.split("-")
                    start_week = int(start.strip())
                    end_week = int(end.strip())
                    
                    for w in range(start_week, end_week + 1):
                        if is_single and w % 2 == 0:
                            continue
                        if is_double and w % 2 == 1:
                            continue
                        weeks.append(w)
                except ValueError:
                    continue
            else:
                # 单个周次
                try:
                    weeks.append(int(part))
                except ValueError:
                    continue
        
        return sorted(set(weeks))
    
    def _weekday_to_date(self, week: int, weekday: int) -> Optional[datetime]:
        """
        将周次和星期几转换为具体日期
        
        Args:
            week: 教学周次（从1开始）
            weekday: 星期几（1=周一, 7=周日）
            
        Returns:
            对应的日期 datetime 对象
        """
        if not self.semester_start:
            return None
        
        # 计算偏移：第一周周一 + (week-1)*7天 + (weekday-1)天
        days_offset = (week - 1) * 7 + (weekday - 1)
        return self.semester_start + timedelta(days=days_offset)
    
    def _parse_time(self, time_str: str) -> tuple:
        """
        解析时间字符串为小时和分钟
        
        Args:
            time_str: 如 "08:00"
            
        Returns:
            (小时, 分钟)
        """
        try:
            h, m = time_str.split(":")
            return int(h), int(m)
        except (ValueError, AttributeError):
            # 默认时间映射（如果无法解析）
            period_times = {
                1: (8, 0), 2: (9, 55), 3: (14, 0), 4: (15, 55),
                5: (18, 30), 6: (20, 15)
            }
            # 尝试从字符串提取节次
            for p, (h, m) in period_times.items():
                if str(p) in time_str:
                    return h, m
            return 8, 0  # 默认第一节
    
    def _period_to_time(self, period: int) -> tuple:
        """
        节次到开始时间的映射
        
        南京理工大学常见排课时间（需根据实际情况调整）
        """
        # 标准时间映射
        times = {
            1: (8, 0),    2: (8, 55),   3: (10, 0),   4: (10, 55),
            5: (14, 0),   6: (14, 55),  7: (16, 0),   8: (16, 55),
            9: (18, 30),  10: (19, 25), 11: (20, 20), 12: (21, 15),
        }
        return times.get(period, (8, 0))
    
    def _generate_uid(self, course: Dict, week: int, weekday: int) -> str:
        """生成事件唯一标识"""
        kcmc = course.get("kcmc", "未知课程")
        jsmc = course.get("jsmc", "")
        return f"{kcmc}-{jsmc}-{week}-{weekday}@njust-schedule"
    
    def _escape_ics_text(self, text: str) -> str:
        """转义 ICS 文本中的特殊字符"""
        return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    
    def export_courses(self, courses: List[Dict[str, Any]], output_path: str,
                       week_filter: Optional[int] = None) -> bool:
        """
        将课程列表导出为 ICS 文件
        
        Args:
            courses: 课程数据列表
            output_path: 输出文件路径
            week_filter: 只导出指定周的课程（None 则导出全部）
            
        Returns:
            是否成功
        """
        if not self.semester_start:
            print("错误：未设置学期开始日期")
            return False
        
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//NJUST Schedule//CN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "X-WR-CALNAME:南京理工大学课表",
            "X-WR-TIMEZONE:Asia/Shanghai",
        ]
        
        event_count = 0
        
        for course in courses:
            kcmc = course.get("kcmc", "未知课程")
            jsmc = course.get("jsmc", "未知教室")
            jsxm = course.get("jsxm", "未知教师")
            kcsj = course.get("kcsj", "")
            kkzc = course.get("kkzc", "")
            kssj = course.get("kssj", "")  # 开始时间 HH:MM
            jssj = course.get("jssj", "")  # 结束时间 HH:MM
            
            # 解析上课周次
            weeks = self._parse_weeks(kkzc)
            if not weeks:
                continue
            
            # 解析课程时间
            if not kcsj or len(kcsj) < 3:
                continue
            
            weekday = int(kcsj[0])
            periods = []
            for i in range(1, len(kcsj), 2):
                if i + 1 < len(kcsj):
                    periods.append(int(kcsj[i:i+2]))
            
            if not periods:
                continue
            
            # 确定每节课的开始和结束时间
            if kssj and jssj:
                start_h, start_m = self._parse_time(kssj)
                end_h, end_m = self._parse_time(jssj)
            else:
                start_h, start_m = self._period_to_time(min(periods))
                # 默认每节课45分钟，连上则延长
                end_period = max(periods)
                end_h, end_m = self._period_to_time(end_period)
                end_m += 45
                if end_m >= 60:
                    end_h += 1
                    end_m -= 60
            
            # 为每个上课周创建事件
            for week in weeks:
                if week_filter is not None and week != week_filter:
                    continue
                
                date = self._weekday_to_date(week, weekday)
                if not date:
                    continue
                
                start_dt = date.replace(hour=start_h, minute=start_m, second=0)
                end_dt = date.replace(hour=end_h, minute=end_m, second=0)
                
                uid = self._generate_uid(course, week, weekday)
                
                lines.extend([
                    "BEGIN:VEVENT",
                    f"DTSTART;TZID=Asia/Shanghai:{start_dt.strftime('%Y%m%dT%H%M%S')}",
                    f"DTEND;TZID=Asia/Shanghai:{end_dt.strftime('%Y%m%dT%H%M%S')}",
                    f"SUMMARY:{self._escape_ics_text(kcmc)}",
                    f"LOCATION:{self._escape_ics_text(jsmc)}",
                    f"DESCRIPTION:教师: {self._escape_ics_text(jsxm)}\\n"
                    f"周次: 第{week}周\\n"
                    f"上课时间: 第{min(periods)}-{max(periods)}节",
                    f"UID:{uid}",
                    "BEGIN:VALARM",
                    "ACTION:DISPLAY",
                    "DESCRIPTION:上课提醒",
                    "TRIGGER:-PT15M",  # 课前15分钟提醒
                    "END:VALARM",
                    "END:VEVENT",
                ])
                event_count += 1
        
        lines.append("END:VCALENDAR")
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\r\n".join(lines) + "\r\n")
            print(f"成功导出 {event_count} 个课程事件到 {output_path}")
            return True
        except IOError as e:
            print(f"文件写入失败: {e}")
            return False


def quick_export(courses: List[Dict], output_path: str, 
                 semester_start: str, week: Optional[int] = None) -> bool:
    """
    快速导出课程到 ICS 文件
    
    Args:
        courses: 课程列表
        output_path: 输出路径
        semester_start: 学期开始日期 YYYY-MM-DD
        week: 只导出指定周（None=全部）
        
    Returns:
        是否成功
    """
    exporter = ICSExporter(semester_start)
    return exporter.export_courses(courses, output_path, week)
