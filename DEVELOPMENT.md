# 开发说明 — 南理工课表项目

> 本文档供日后继续开发时参考。记录当前架构、已知问题、未来改进方向。

---

## 当前版本

- **稳定版 tag**: `v2.0-stable`
- **备份 branch**: `backup/v2.0-stable`
- **GitHub Pages**: https://19338126485.github.io/njust-schedule/

---

## 已完成功能

| 模块 | 说明 |
|------|------|
| 课表抓取 | IDS统一认证 → 强智教务系统 → 解析HTML → `schedule.json` |
| 考试抓取 | 浏览器自动化：门户 → 教务系统 → 考试报名 → 查询 → `exams.json` |
| ICS导出 | 将课表导出为 `.ics` 日历文件，支持手机/电脑日历导入 |
| PWA手机端 | 离线可用，周视图/日视图，课程弹窗详情 |
| 一键更新 | 双击 `update.bat` 自动抓取 + push 到 GitHub Pages |
| 在线刷新 | PWA菜单里「🔄 刷新数据」清除缓存并重新拉取 |

---

## 技术架构

### 数据流

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  教务系统    │───▶│  Python脚本  │───▶│ schedule.json│
│ (强智+IDS)  │    │ (本地电脑运行) │    │   exams.json  │
└─────────────┘    └──────────────┘    └──────┬──────┘
                                                │
                                          git push
                                                ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  手机浏览器  │◀───│  GitHub Pages│◀───│  GitHub仓库  │
│   (PWA)     │    │   (静态托管)   │    │              │
└─────────────┘    └──────────────┘    └─────────────┘
```

### 核心文件

| 文件 | 职责 |
|------|------|
| `update.bat` / `update.py` | 一键更新入口。自动抓取课表+考试，git push |
| `src/ids_auth.py` | IDS统一认证。AES加密密码，获取CAS Cookie |
| `src/portal_browser.py` | 浏览器自动化（DrissionPage）。门户→教务系统→课表/考试 |
| `src/exam_browser.py` | 考试查询浏览器流程。复用 `portal_browser.py` 的 `find_and_click` |
| `src/exam_parser.py` | 考试HTML解析。解析 `<table id="dataList">` |
| `src/api_client.py` | 强智系统HTTP客户端 + 课表HTML解析。输出前端友好JSON |
| `src/ics_exporter.py` | ICS日历导出。支持单双周、课前提醒 |
| `webapp/js/schedule.js` | 课表渲染引擎。Grid布局，周/日视图切换 |
| `webapp/js/app.js` | PWA主逻辑。数据加载、弹窗、刷新按钮 |
| `webapp/js/storage.js` | localStorage管理。课表/考试数据的存取 |
| `webapp/sw.js` | Service Worker。网络优先策略，离线可用 |

---

## 关键决策记录

### 1. 登录策略：IDS SSO + 浏览器兜底

南理工教务系统强制通过 `ids.njust.edu.cn` 金智IDS统一认证登录。纯 `requests` 能登录IDS，但无法完成CAS ticket交换到强智教务系统。

**方案**：
1. 先用 `requests` IDS模拟登录（快速、无头）
2. 如果课表请求返回登录页 → 自动启动浏览器兜底
3. 浏览器走完整SSO链路：IDS登录 → 302跳转 → 强智系统

### 2. 课表解析：从周视图提取周次

强智系统的课表页面包含两个视图：
- **列表视图**：有课程名称/教师/时间/地点，**但没有周次**
- **周视图**：每个课程格子里有 `<font title="周次(节次)">16(周)</font>`

周次数字在标签**文本**中，不在 `title` 属性里。`_extract_weeks_from_week_view()` 从周视图提取 `{课程名: 周次}` 映射，然后列表视图解析时 lookup。

### 3. PWA缓存策略：网络优先

`sw.js` 使用网络优先策略（fetch成功就用最新，失败才fallback缓存）。开发阶段避免缓存旧版本。

生产使用时注意：如果用户长期离线，看到的仍是上次缓存的数据。

### 4. 数据格式：前端友好JSON

`api_client.py` 输出同时包含两种字段：

```json
{
  "name": "概率与统计",
  "teacher": "侯传志,陆中胜",
  "location": "江阴格物C302",
  "day": 2,
  "startJie": 6,
  "endJie": 7,
  "weeks": "1-12",
  "color": 2,
  // 同时保留强智原始字段
  "kcmc": "概率与统计",
  "jsxm": "侯传志,陆中胜",
  "jsmc": "江阴格物C302",
  "kcsj": "20607",
  "kkzc": "1-12"
}
```

PWA渲染引擎用 `name/day/startJie/endJie/weeks/color`，ICS导出器用 `kssj/jssj/kkzc`。

---

## 已知问题与限制

### 当前已确认的问题

| 问题 | 影响 | 状态 |
|------|------|------|
| 手机端需手动点击「刷新数据」 | 不自动同步最新课表 | ✅ 有workaround（刷新按钮） |
| 课程时间重叠冲突显示 | 两个课在同一小节时可能重叠覆盖 | ❌ 未修复 |
| 课表抓取依赖浏览器自动化 | 必须在Windows电脑+Edge上运行 | 架构限制 |
| 验证码场景需手动输入 | IDS偶尔触发验证码，脚本暂停等待 | 低概率 |
| 长期离线可能看到旧数据 | SW缓存过期策略未配置 | 待改进 |

### 浏览器兼容性

- **Edge**: ✅ 主浏览器（系统自带，DrissionPage默认使用）
- **Chrome**: ✅ 可用（路径不同）
- **Firefox/Safari**: ❌ 未测试
- **手机浏览器**: ✅ 只要支持PWA（Chrome/Edge/Safari均可）

---

## 未来改进方向

### 高优先级（用户明确提过）

| 功能 | 技术方案 | 复杂度 |
|------|----------|--------|
| **课程时间重叠冲突显示** | Grid布局中同一格子多个课程时，用flex column堆叠或交替显示 | 中 |
| **课前提醒（Notification API）** | Service Worker + `self.registration.showNotification()`，定时检查下一节课 | 中 |

### 中优先级

| 功能 | 技术方案 | 复杂度 |
|------|----------|--------|
| **成绩查询** | 复用考试查询的浏览器流程，进入「学籍成绩」模块 | 中 |
| **空教室查询** | 强智系统有「空教室查询」入口，类似考试查询流程 | 中 |
| **自动化定时更新** | Windows任务计划程序每天运行 `update.bat` | 低 |
| **多学期切换** | PWA顶部加学期选择下拉框，数据按学期分localStorage key | 低 |

### 低优先级/探索性

| 功能 | 技术方案 | 复杂度 |
|------|----------|--------|
| **手机端直接更新（无电脑）** | Termux不可行（无GUI浏览器）。方案：电脑开本地API服务器，手机同WiFi访问 | 高 |
| **导出为微信小程序** | 用 uni-app/Taro 重写，但需解决登录问题 | 高 |
| **课表分享/订阅** | 生成ICS订阅URL（.webcal），他人可订阅你的课表 | 中 |

---

## 开发注意事项

### 修改PWA后的必做步骤

```powershell
# 1. 修改 webapp/ 下的文件
# 2. 同步到 docs/（GitHub Pages 源是 /docs）
xcopy /E /I /Y webapp docs

# 3. 升级版本号（强制浏览器刷新）
# 在 webapp/index.html 和 docs/index.html 中修改：
#   js/schedule.js?v=X → v=X+1

# 4. git commit + push
git add -A
git commit -m "fix/feat: xxx"
git push origin main

# 5. 等30秒，GitHub Pages自动部署
```

### 调试手机端问题

1. 手机浏览器访问 `https://19338126485.github.io/njust-schedule/?v=最新版本号`
2. 如果还是旧版 → 清除网站数据（Chrome设置 → 隐私 → 清除浏览数据）
3. 或卸载PWA重新添加

### 测试课表解析

```powershell
cd "C:\Users\19338\Desktop\学习相关\南京理工大学个人课表项目"
python -m src.main
```

查看输出中的周次是否正确（如「模拟与数字电路综合实验」应为 `16`，不是 `1-16`）。

### 测试考试查询

```powershell
python -m src.exams_main
```

---

## 重要外部依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| DrissionPage | 4.1.1.2 | 浏览器自动化 |
| beautifulsoup4 | >=4.12.0 | HTML解析 |
| requests | - | IDS模拟登录 |
| icalendar | - | ICS日历导出 |

### DrissionPage 4.x API差异

官方文档和实际版本有差异，以下已验证可用：

```python
from DrissionPage import ChromiumPage, ChromiumOptions

# 初始化（不是 chromium_options）
co = ChromiumOptions()
co.set_browser_path(edge_path)
page = ChromiumPage(addr_or_opts=co)

# 标签页操作（不是 .tabs 属性）
tabs = page.get_tabs()     # 获取标签页对象列表
page.to_tab(index)         # 切换到指定索引的标签页
```

---

## 安全与隐私

- `src/config.py` 包含学号密码，已加入 `.gitignore`
- 密码仅在本地电脑使用，不上传任何服务器
- GitHub Pages 只托管静态文件（HTML/CSS/JS/JSON），不含密码
- 首次使用前必须确保智慧理工门户首页已显示「教务系统」入口

---

*最后更新: 2026-05-01*
*对应版本: v2.0-stable*
