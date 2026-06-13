# 南京理工大学课表项目 - 开发计划

**项目目标**: 替代「周三课表」小程序，长期自用的课表查询工具  
**当前稳定版本**: `v2.2-refactor`  
**开发状态**: 活跃维护中

---

## 已完成的里程碑

### v1.0-pwa — PWA 基础版
- [x] 课表数据抓取与解析
- [x] PWA 离线查看（周视图/日视图）
- [x] ICS 日历导出
- [x] GitHub Pages 部署

### v2.0-stable — 考试+一键更新
- [x] 考试安排抓取与解析
- [x] 一键更新脚本 (`update.bat`)
- [x] 自动推送到 GitHub Pages

### v2.1-clean-requests — 清理 requests 路径
- [x] 删除 `ids_auth.py`（requests 模拟 IDS 登录，已证明走不通）
- [x] 删除 `browser_auth.py`（浏览器 Cookie 备用方案，被 portal_browser 覆盖）
- [x] 删除 `direct_browser.py`（dead code）
- [x] 删除 `debug_ids.py`（IDS 诊断脚本，不再需要）
- [x] 简化 `api_client.py`：去掉 session 依赖，删除废弃 app.do 方法
- [x] 简化 `main.py`：直接走 portal_browser，删除两个 login 函数
- [x] 简化 `update.py`：直接走浏览器自动化

### v2.2-refactor — 浏览器基类提取 + 前端修复 + 依赖清理
- [x] 提取 `enter_qiangzhi_system()` 公共函数，消除 portal_browser/exam_browser 重复代码
- [x] `schedule.js` 从 `Storage.getStartDate()` 读取开学日期，替代硬编码
- [x] `storage.js` 默认开学日期同步为 `2026-03-02`
- [x] `sw.js` 修复带 `?v=...` 查询参数的缓存匹配
- [x] `requirements.txt` 移除 `requests`、`PyExecJS`、`lxml`

---

## 待修复的已知问题

### 🔴 高优先级

| 问题 | 影响 | 文件 |
|------|------|------|
| 课程时间重叠时 UI 覆盖 | 同一格子多门课只显示一个 | `webapp/css/style.css`, `webapp/js/schedule.js` |
| `exam_parser.py` 表头硬编码中文 | 教务系统改字就解析失败 | `src/exam_parser.py` |

### 🟡 中优先级

| 问题 | 影响 | 文件 |
|------|------|------|
| `ics_exporter.py` fallback 时间映射与实际课表不符 | ICS 导出时间可能偏差 | `src/ics_exporter.py` |
| `exams_main.py` 和 `update.py` 有重复的数据保存逻辑 | 代码冗余 | `src/exams_main.py`, `update.py` |

### 🟢 低优先级

| 问题 | 影响 |
|------|------|
| `update.py` 的 commit message 是固定格式 | 不区分课表/考试/双更新的场景 |

---

## 重构路线图（已完成 Phase 1-3，剩余可选优化）

### 课程冲突显示
Grid布局中同一格子多个课程时，用flex column堆叠或交替显示。

### 考试解析器健壮性
`exam_parser.py` 表头映射改为模糊匹配（兼容"考场"/"考试地点"等变体）。

---

## 排课时间（已确认）

| 大节 | 小节 | 开始 | 结束 |
|------|------|------|------|
| 第一大节 | 1~3 | 08:00 | 10:25 |
| 第二大节 | 4~5 | 10:40 | 12:15 |
| 第三大节 | 6~7 | 14:00 | 15:35 |
| 第四大节 | 8~10 | 15:50 | 18:15 |
| 第五大节 | 11~13 | 19:00 | 21:25 |
| 网课占位 | 14 | 22:15 | 23:00 |

---

## 关键外部依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| DrissionPage | 4.1.1.2 | 浏览器自动化 |
| beautifulsoup4 | >=4.12.0 | HTML解析 |
| icalendar | - | ICS日历导出 |

---

## 重要URL

- **门户**: `https://ehall2.njust.edu.cn/index.html#/`
- **课表URL**: `http://bkjw.njust.edu.cn/njlgdx/xskb/xskb_list.do?Ves632DSdyV=NEW_XSD_PYGL`
- **强智主页**: `http://bkjw.njust.edu.cn/njlgdx/framework/main.jsp`
- **GitHub Pages**: https://19338126485.github.io/njust-schedule/
