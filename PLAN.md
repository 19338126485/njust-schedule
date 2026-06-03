# 南京理工大学课表项目 - 开发计划

**项目目标**: 替代「周三课表」小程序，长期自用的课表查询工具  
**当前稳定版本**: `v2.1-clean-requests`  
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

---

## 待修复的已知问题

### 🔴 高优先级

| 问题 | 影响 | 文件 |
|------|------|------|
| `portal_browser.py` 和 `exam_browser.py` 80%代码重复 | 教务系统改版要改两处 | `src/portal_browser.py`, `src/exam_browser.py` |
| `schedule.js` 硬编码开学日期 `2026-03-02` | 用户设置开学日期后周次仍错 | `webapp/js/schedule.js` |
| `storage.js` 默认开学日期 `'2026-02-17'` 与配置不一致 | 前后端周次计算不一致 | `webapp/js/storage.js` |
| Service Worker 缓存 `data/*.json` 不带查询参数，但 `app.js` 请求带 `?v=...` | 离线时数据文件缓存 miss | `webapp/sw.js` |

### 🟡 中优先级

| 问题 | 影响 | 文件 |
|------|------|------|
| 课程时间重叠时 UI 覆盖 | 同一格子多门课只显示一个 | `webapp/css/style.css`, `webapp/js/schedule.js` |
| `ics_exporter.py` fallback 时间映射与实际课表不符 | ICS 导出时间可能偏差 | `src/ics_exporter.py` |
| `requirements.txt` 包含 `requests`, `PyExecJS` 等不再需要依赖 | 安装冗余 | `requirements.txt` |
| `exam_parser.py` 表头硬编码中文 | 教务系统改个字就解析失败 | `src/exam_parser.py` |

### 🟢 低优先级

| 问题 | 影响 |
|------|------|
| `exams_main.py` 和 `update.py` 有重复的数据保存逻辑 | 代码冗余 |
| `update.py` 的 commit message 是固定格式 | 不区分课表/考试/双更新的场景 |

---

## 重构路线图

### Phase 1: 提取浏览器公共基类

**目标**: 合并 `portal_browser.py` 和 `exam_browser.py` 的重复部分

**提取内容**:
```
src/browser/
    base.py          ← _safe_import_drission, _init_browser, _poll_url_change
    portal_flow.py   ← 门户登录 → IDS登录 → 点击教务系统 → 标签页切换
    schedule_flow.py ← portal_flow + 点击课表入口
    exam_flow.py     ← portal_flow + 点击考试报名 + 触发查询
```

**收益**: 教务系统登录流程改版时，只改一个地方。

### Phase 2: 前端修复

1. `schedule.js` 从 `Storage.getStartDate()` 读取开学日期
2. `storage.js` 默认日期同步为 `2026-03-02`
3. `sw.js` 缓存策略修复：对 `data/*.json` 的请求做查询参数剥离，或改用正确的 cache-busting
4. 课程冲突显示：同一格子多门课时用 flex column 堆叠

### Phase 3: 基础设施清理

1. `requirements.txt` 移除 `requests`, `PyExecJS`
2. `exam_parser.py` 表头映射改为模糊匹配（兼容"考场"/"考试地点"等变体）
3. `update.py` commit message 增加变更摘要（课表/考试/双更新）

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
