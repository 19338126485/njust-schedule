# 南京理工大学个人课表项目

## 项目简介

替代即将停止服务的「周三课表」，自动从南京理工大学教务系统抓取课表数据。

## 技术背景

- 南理工本科教务系统 (`bkjw.njust.edu.cn`) 使用的是 **湖南强智科技** 的教务系统
- 强智系统提供了一套 App JSON API，可以直接获取结构化课表数据
- 无需解析 HTML 表格

## 核心 API

### 1. 登录获取 Token
```
GET http://bkjw.njust.edu.cn/app.do?method=authUser&xh={学号}&pwd={密码}
```

### 2. 获取当前时间信息（第几周）
```
GET http://bkjw.njust.edu.cn/app.do?method=getCurrentTime&currDate={YYYY-MM-DD}
```

### 3. 获取课表
```
GET http://bkjw.njust.edu.cn/app.do?method=getKbcxAzc&xh={学号}&xnxqid={学期}&zc={周次}
```

## 项目结构

```
南京理工大学个人课表项目/
├── README.md              # 项目说明
├── config.py              # 配置文件（含用户凭据，已加入 .gitignore）
├── requirements.txt        # Python 依赖
├── .gitignore            # Git 忽略规则
├── src/
│   ├── __init__.py
│   ├── api_client.py      # 强智教务 API 客户端
│   ├── ics_exporter.py    # ICS 日历文件导出
│   └── utils.py           # 工具函数
└── tests/
    └── test_api.py        # API 测试
```

## 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置学号密码（复制 `config.example.py` 到 `config.py`）：
```bash
cp src/config.example.py src/config.py
# 然后编辑 src/config.py，填入你的学号和密码
```

3. 运行测试：
```bash
python -m src.test_api
```

## 数据来源

- 南京理工大学本科教务系统: http://bkjw.njust.edu.cn
- 强智科技 App API

## 安全提醒

⚠️ **密码安全**：本项目为个人使用工具，密码仅在本地存储，不会上传到任何第三方服务器。请勿将包含密码的 `config.py` 提交到公共仓库。
