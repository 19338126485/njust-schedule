# 南理工课表 — 替代「周三课表」

替代即将停止服务的「周三课表」小程序，自动从南京理工大学教务系统抓取课表和考试数据，PWA离线查看。

## ⚠️ 重要前提

**在使用本工具之前，请确保你的智慧理工门户首页已显示「教务系统」入口。**

南理工门户首页的常用应用列表需要你**手动收藏**才会出现。如果首页看不到「教务系统」图标，浏览器自动化脚本将无法找到入口，导致抓取失败。

**检查方式：**
1. 浏览器打开 [智慧理工门户](https://ehall.njust.edu.cn/new/index.html)
2. 确认首页有「教务系统」图标
3. 如果没有，手动收藏一次（进入教务系统后通常会自动收藏）

## 功能概览

- 📅 **课表查询** — 周视图/日视图，自动计算当前周次
- 📝 **考试安排** — 自动抓取考试时间、考场、座位号
- 📱 **PWA手机端** — 添加到主屏幕，离线可用
- 📤 **课表导出** — 导出 JSON 备份，可随时导入恢复
- 🔄 **一键更新** — 双击 `update.bat` 自动抓取并推送到GitHub Pages

## 技术背景

南理工教务系统使用 **湖南强智科技** 的教务系统，强制通过 `ids.njust.edu.cn` 金智IDS SSO统一认证登录。强智系统原有的 `app.do` JSON API 已关闭，本项目采用浏览器自动化穿透SSO后抓取HTML并解析。

**登录链路：**
```
智慧理工门户 → IDS统一认证 → 教务系统（强智）→ 课表/考试页面
```

## 项目结构

```
南京理工大学个人课表项目/
├── update.bat              ← 双击一键更新（课表+考试+推送）
├── update.py               ← 一键更新逻辑
├── src/
│   ├── portal_browser.py   ← 浏览器自动化（门户→教务系统→课表）
│   ├── exam_browser.py     ← 浏览器自动化（门户→教务系统→考试）
│   ├── exam_parser.py      ← 考试HTML解析器
│   ├── api_client.py       ← 强智系统课表HTML解析器
│   ├── crypto_helper.py    ← 数据加密（PBKDF2 → AES-256-GCM）
│   ├── config.py           ← 学号密码配置（已加入.gitignore）
│   └── config.example.py   ← 配置模板
├── webapp/                 ← PWA本地开发目录
│   ├── index.html
│   ├── css/style.css
│   ├── js/schedule.js      ← 课表渲染引擎
│   ├── js/app.js           ← PWA主逻辑
│   ├── js/storage.js       ← localStorage管理
│   ├── data/schedule.enc.json  ← 课表数据（AES-256-GCM 加密）
│   ├── data/exams.enc.json     ← 考试数据（AES-256-GCM 加密）
│   ├── sw.js               ← Service Worker（离线缓存）
│   └── manifest.json
├── docs/                   ← GitHub Pages 部署目录（webapp 的副本）
├── requirements.txt        ← Python依赖
├── .gitignore
└── README.md
```

## 安装与配置

### 1. 安装Python依赖

```powershell
pip install -r requirements.txt
```

### 2. 配置学号密码

```powershell
copy src\config.example.py src\config.py
# 编辑 src\config.py，填入你的学号和密码
```

### 3. 安装Edge浏览器（已预装在Windows 10/11上）

浏览器自动化使用系统自带的 Edge，无需额外安装。

## 使用方式

### 方式一：一键更新（推荐）

**在电脑上双击 `update.bat`**

自动完成：
1. IDS登录 → 抓取课表 → 加密保存 `schedule.enc.json`
2. 浏览器抓取考试 → 加密保存 `exams.enc.json`
3. `git push` 推送到 GitHub
4. 等30秒，GitHub Pages自动部署
5. 手机上刷新页面即可看到最新数据

访问地址：[https://19338126485.github.io/njust-schedule/](https://19338126485.github.io/njust-schedule/)

### 方式二：手动运行

```powershell
# 抓取课表 + 考试安排（课表和考试会一起更新、加密并推送）
python update.py
```

### 方式三：PWA手机端（无需电脑）

1. 手机浏览器打开 [GitHub Pages 链接](https://19338126485.github.io/njust-schedule/)
2. 浏览器菜单 → **"添加到主屏幕"**
3. 桌面出现「南理工课表」图标
4. 离线也能查看课表（数据已缓存）

**注意**：PWA上的数据是上次 `update.bat` 推送的版本，不会自动更新。需要更新时回到方式一。

## 安全提醒

⚠️ **密码不上传服务器**：`src/config.py` 包含你的学号和密码，已加入 `.gitignore`，不会提交到GitHub。所有登录操作都在你的本地电脑上完成。

⚠️ **课表数据已加密存储**：仓库和 GitHub Pages 上的 `schedule.enc.json` / `exams.enc.json` 是 AES-256-GCM 密文，打开网页需要输入数据密码（`DATA_PASSWORD`）在浏览器本地解密，密码仅存于当前标签页，关闭网页即失效，不会上传。

⚠️ **GitHub Pages只托管静态PWA文件**（HTML/CSS/JS/加密JSON），不包含任何明文课表或敏感信息。

## 数据来源

- 南京理工大学本科教务系统：[http://bkjw.njust.edu.cn](http://bkjw.njust.edu.cn)
- 金智IDS统一认证：[https://ids.njust.edu.cn](https://ids.njust.edu.cn)
- 智慧理工门户：[https://ehall.njust.edu.cn](https://ehall.njust.edu.cn)

## 已知限制

- 课表数据抓取依赖浏览器自动化，**需要在电脑上运行**，无法在手机上直接更新
- 强智系统页面结构可能随版本升级变化，解析器可能需要适配
- 验证码场景（IDS登录偶尔触发）需要手动输入

## 回退与备份

项目已打 tag `v1.0-pwa` 作为稳定备份。如后续修改导致问题：

```powershell
git reset --hard v1.0-pwa
```

---

*个人自用工具，仅供南京理工大学学生参考。*
