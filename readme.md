# InteractComp 多用户标注质量测试平台

通过多模型并行作答评估标注数据难度与质量。判断规则：当"2个及以上模型答对"视为标注质量不合格，反之为合格。

## 🆕 v3.0 多用户版本特性

- **多用户支持**: 用户注册、登录、会话管理
- **数据共享**: 所有用户的评估结果互相可见
- **权限管理**: 文件上传权限控制，任务创建者信息记录
- **JSON存储**: 基于文件的用户数据存储，无需数据库
- **社区功能**: 查看所有用户的任务和评估结果

## 系统架构

- 后端：FastAPI + 多用户认证（见 [web_api.py](web_api.py)）
- 前端：React + Vite 多用户界面（见 [frontend/src/MultiUserApp.jsx](frontend/src/MultiUserApp.jsx)）
- 用户管理：JSON文件存储（见 [utils/user_manager.py](utils/user_manager.py)）
- 基准逻辑与Agent：
  - 多模型评估入口：[benchmarks/InteractComp.py](benchmarks/InteractComp.py)
  - Agent与工厂方法：[workflow/InteractComp.py](workflow/InteractComp.py)tComp 三模型标注质量测试平台

通过多模型并行作答评估标注数据难度与质量。判断规则：当“2个及以上模型答对”视为标注质量不合格，反之为合格。

- 后端：FastAPI（见 [web_api.py](web_api.py)）
- 前端：React + Vite（见 [frontend/src/App.jsx](frontend/src/App.jsx)）
- 基准逻辑与Agent：
  - 多模型评估入口：[benchmarks/InteractComp.py](benchmarks/InteractComp.py)
  - Agent与工厂方法：[workflow/InteractComp.py](workflow/InteractComp.py)

## 功能特点
<<<<<<< HEAD

### 核心评估功能
- 三模型固定评估：gpt-5-mini、gpt-5、claude-4-sonnet
=======
- 三模型固定评估：gpt-5-mini、gpt-5、claude-sonnet-4-20250514
- Web 界面上传 JSONL/JSON 文件、一键启动评估、下载 CSV 报告
>>>>>>> eb0ea3c (WIP: local edits before syncing with origin/main)
- 异步评估与进度查询、总成本统计
- 简单命令行入口（见 [run_baseline.py](run_baseline.py)）

### 多用户功能
- **用户认证**: 注册、登录、会话管理
- **数据隔离**: 每个用户的文件上传独立管理
- **共享查看**: 所有用户可查看彼此的评估结果
- **权限控制**: 只能操作自己上传的文件，但可查看所有任务结果
- **社区面板**: 查看平台所有用户和任务统计

### Web界面功能
- 响应式设计，支持移动端
- 文件拖拽上传
- 实时评估进度显示
- CSV报告下载
- 任务历史管理
- 用户社区数据展示

## 目录结构
```text
.
├─ web_api.py                    # FastAPI 后端（多用户版）
├─ start_multiuser.py           # 多用户版启动脚本
├─ frontend/                    # React 前端
│  ├─ src/
│  │  ├─ App.jsx               # 原版单用户界面
│  │  ├─ MultiUserApp.jsx      # 新版多用户界面
│  │  └─ main.jsx              # 入口文件
│  └─ package.json
├─ utils/
│  └─ user_manager.py          # 用户管理（JSON存储）
├─ user_data/                   # 用户数据目录
│  ├─ users.json               # 用户信息
│  ├─ sessions.json            # 用户会话
│  ├─ users/                   # 用户个人数据
│  └─ shared/                  # 共享数据
├─ benchmarks/                  # 基准评估
│  └─ InteractComp.py
├─ workflow/                    # Agent与工厂
│  └─ InteractComp.py
├─ config/
│  ├─ config2.example.yaml
│  └─ config2.yaml            # API Keys配置
├─ data/                       # 示例数据
├─ requirements.txt            # 更新依赖（包含认证）
└─ run_baseline.py            # 命令行版本
```

## 环境要求
- Python 3.11+
- Node.js 18+

## 快速开始

### 方式一：使用多用户启动脚本（推荐）

1) 安装依赖
```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

2) 配置 API Keys（复制模板并填写）
```bash
cp config/config2.example.yaml config/config2.yaml
# 编辑 config2.yaml 填入你的API Keys
```

3) 一键启动多用户平台
```bash
python start_multiuser.py
```

4) 启动前端开发服务器
```bash
cd frontend
npm run dev
```

5) 访问平台
- 多用户前端：http://localhost:3000
- API文档：http://localhost:8000/docs
- 配置检查：http://localhost:8000/config/status

### 方式二：手动启动

1) 安装依赖和配置（同上）

2) 启动后端
```bash
python web_api.py
```

3) 启动前端
```bash
cd frontend
npm run dev
```

## 数据格式（JSONL 推荐）
每行一个对象，包含 question / answer / context 字段。
```json
{"question": "Which early computing system influenced desktop metaphor?", "answer": "Xerox Alto (1973)", "context": "早期图形界面计算机系统..."}
{"question": "Which Japanese anime depicts humans struggling...", "answer": "甲鉄城のカバネリ", "context": "关于人类在装甲列车上生存的动画..."}
```

## 完整使用流程

### 1. 环境准备
```bash
# 克隆项目
git clone <repository_url>
cd InteractComp_test

# 安装Python依赖
pip install -r requirements.txt

# 安装Node.js依赖
cd frontend
npm install
cd ..
```

### 2. 配置API Keys
```bash
# 复制配置模板
cp config/config2.example.yaml config/config2.yaml

# 编辑配置文件，填入你的API Keys
vim config/config2.yaml  # 或使用其他编辑器
```

配置文件示例：
```yaml
models:
  "gpt-5-mini":
    api_type: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "sk-proj-xxxxxxxxxx"
    temperature: 0

  "gpt-5":
    api_type: "openai"
    base_url: "https://api.openai.com/v1"
    api_key: "sk-proj-xxxxxxxxxx"
    temperature: 0

  "claude-sonnet-4-20250514":
    api_type: "openai"     # 通过代理访问
    base_url: "https://one-api.example.com/v1"
    api_key: "sk-xxxxxxxxxx"
    temperature: 0

search:
  engines:
    google:
      api_key: "<your_serper_api_key>"
```

### 3. 初始化系统
```bash
# 初始化用户数据目录和系统结构
python init_multiuser.py
```

### 4. 启动服务
```bash
# 方式一：使用启动脚本（推荐）
python start_multiuser.py

# 方式二：分别启动
# 终端1 - 后端服务
python web_api.py

# 终端2 - 前端服务
cd frontend
npm run dev
```

### 5. 访问平台
- **前端界面**: http://localhost:3000
- **API文档**: http://localhost:8000/docs
- **配置检查**: http://localhost:8000/config/status

### 6. 使用平台
1. **注册/登录**: 访问前端页面，注册新用户或登录
2. **上传数据**: 上传 .jsonl 或 .json 格式的标注数据
3. **开始评估**: 选择文件，点击开始三模型评估
4. **查看结果**: 等待评估完成，查看详细结果
5. **下载报告**: 下载CSV格式的评估报告
6. **社区数据**: 查看其他用户的评估结果

## API 接口

### 认证相关
- POST `/auth/register`：用户注册
- POST `/auth/login`：用户登录
- GET `/auth/me`：获取当前用户信息
- POST `/auth/logout`：用户登出

### 核心功能（需要认证）
- GET `/`：服务状态
- GET `/config/status`：检查配置文件状态
- POST `/upload`：上传数据文件（.jsonl/.json）
- GET `/files`：获取当前用户的文件列表
- POST `/test/start`：开始评估（请求体：{file_ids: []}）
- GET `/test/{task_id}`：查询进度/结果
- GET `/test/{task_id}/download-csv`：下载详细CSV报告
- GET `/tasks`：获取任务列表（个人+全部）
- GET `/users`：获取用户列表

### 示例用法（Python）：
```python
import requests

# 注册用户
register_data = {
    "username": "test_user",
    "password": "password123",
    "display_name": "测试用户"
}
requests.post('http://localhost:8000/auth/register', json=register_data)

# 登录获取token
login_data = {"username": "test_user", "password": "password123"}
login_resp = requests.post('http://localhost:8000/auth/login', json=login_data)
token = login_resp.json()['token']

# 设置认证头
headers = {'Authorization': f'Bearer {token}'}

# 上传文件
with open('data/data.jsonl', 'rb') as f:
    files = {'file': f}
    upload_resp = requests.post('http://localhost:8000/upload', 
                               files=files, headers=headers)
    file_id = upload_resp.json()['file_id']

# 启动评估
task_resp = requests.post('http://localhost:8000/test/start', 
                         json={'file_ids': [file_id]}, headers=headers)
task_id = task_resp.json()['task_id']

# 查询结果
result = requests.get(f'http://localhost:8000/test/{task_id}', headers=headers)
print(result.json())

# 下载报告
report = requests.get(f'http://localhost:8000/test/{task_id}/download-csv', 
                     headers=headers)
with open('report.csv', 'wb') as f:
    f.write(report.content)
```

## 快速诊断

运行系统状态检查脚本：
```bash
python check_system.py
```

这个脚本会检查：
- Python环境和依赖
- 文件结构完整性
- 配置文件正确性
- 用户系统状态
- 后端/前端服务运行状态

## 故障排除

### 常见问题

**Q: 前端页面显示"无法连接到后端服务"**
A: 确保后端服务正在运行（`python web_api.py`），检查端口8000是否被占用

**Q: 登录后显示"认证失效"**
A: 可能是会话过期（24小时），请重新登录

**Q: 文件上传失败**
A: 检查文件格式是否为 .jsonl 或 .json，文件内容是否符合格式要求

**Q: 评估任务一直显示"pending"状态**
A: 检查 config2.yaml 中的API Keys是否正确配置，查看后端日志错误信息

**Q: 前端npm run dev失败**
A: 确保Node.js版本≥16，删除node_modules重新安装：`rm -rf node_modules && npm install`

### 数据格式要求

**JSONL格式** (推荐):
```jsonl
{"question": "What is the capital of France?", "answer": "Paris", "context": "France is a country..."}
{"question": "Who wrote Romeo and Juliet?", "answer": "William Shakespeare", "context": "Romeo and Juliet is..."}
```

**JSON格式**:
```json
[
  {"question": "What is the capital of France?", "answer": "Paris", "context": "France is a country..."},
  {"question": "Who wrote Romeo and Juliet?", "answer": "William Shakespeare", "context": "Romeo and Juliet is..."}
]
```

### 系统限制

- 会话有效期：24小时
- 文件大小限制：建议单个文件不超过100MB
- 并发评估：最多20个并发任务
- 支持的模型：gpt-5-mini, gpt-5, claude-4-sonnet

### 日志和调试

查看系统日志：
```bash
# 后端日志
tail -f logs/system.log

# 用户操作日志
ls user_data/users/
```

## 开发和扩展

### 添加新的评估模型

1. 在 `config2.yaml` 中添加模型配置
2. 更新 `EVALUATION_MODELS` 列表在 `web_api.py`
3. 确保模型兼容OpenAI API格式

### 自定义前端界面

- 前端源码位于 `frontend/src/`
- 主要组件：`MultiUserApp.jsx`
- 样式使用：Tailwind CSS
- 图标库：Lucide React

### 扩展存储后端

当前使用JSON文件存储，可扩展到数据库：
- 修改 `utils/user_manager.py`
- 保持API接口不变
- 支持 SQLite, PostgreSQL, MongoDB 等

## 部署建议

- 生产后端（Gunicorn + Uvicorn）
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker web_api:app --bind 0.0.0.0:8000
```

- Nginx 反向代理（示例）
```nginx
server {
  listen 80;
  server_name your-domain.com;

  location / {
    root /path/to/frontend/dist;
    try_files $uri $uri/ /index.html;
  }

  location /api/ {
    proxy_pass http://localhost:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }
}
```

- Docker（简单示例）
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "web_api.py"]
```

```bash
docker build -t interactcomp .
docker run -d -p 8000:8000 -v ./config:/app/config interactcomp
```

## 许可证
MIT License（见 [LICENSE](LICENSE)）