# InteractComp 三模型标注质量测试平台

通过多模型并行作答评估标注数据难度与质量。判断规则：当“2个及以上模型答对”视为标注质量不合格，反之为合格。

- 后端：FastAPI（见 [web_api.py](web_api.py)）
- 前端：React + Vite（见 [frontend/src/App.jsx](frontend/src/App.jsx)）
- 基准逻辑与Agent：
  - 多模型评估入口：[benchmarks/InteractComp.py](benchmarks/InteractComp.py)
  - Agent与工厂方法：[workflow/InteractComp.py](workflow/InteractComp.py)

## 功能特点
- 三模型固定评估：gpt-5-mini、gpt-5、claude-4-sonnet
- Web 界面上传 JSONL/JSON 文件、一键启动评估、下载 CSV 报告
- 异步评估与进度查询、总成本统计
- 简单命令行入口（见 [run_baseline.py](run_baseline.py)）

## 目录结构
```text
.
├─ web_api.py                 # FastAPI 后端（/upload、/test/start、/test/{id} 等）
├─ frontend/                  # React 前端（上传/结果页）
│  ├─ src/App.jsx
│  └─ package.json
├─ benchmarks/                # 基准评估（多模型评估实现）
│  └─ InteractComp.py
├─ workflow/                  # Agent与工厂（create_multi_model_agent_factory等）
│  └─ InteractComp.py
├─ config/
│  ├─ config2.example.yaml
│  └─ config2.yaml            # 你的API Keys配置
├─ data/                      # 示例/自备数据
├─ requirements.txt
└─ run_baseline.py
```

## 环境要求
- Python 3.11+
- Node.js 18+

## 快速开始

1) 安装依赖
```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

2) 配置 API Keys（复制模板并填写）
```bash
cp config/config2.example.yaml config/config2.yaml
```

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

  "claude-4-sonnet":
    api_type: "openai"     # 通过代理访问
    base_url: "https://one-api.example.com/v1"
    api_key: "sk-xxxxxxxxxx"
```

3) 启动服务
```bash
# 后端
python web_api.py

# 前端（新终端）
cd frontend
npm run dev
```

- 后端接口文档：http://localhost:8000/docs
- 前端开发预览：http://localhost:3000

前端通过 fetch('/upload' 等) 调用后端接口，开发模式请在 Vite 代理或Nginx层做转发；后端已开启 CORS。

## 数据格式（JSONL 推荐）
每行一个对象，包含 question / answer / context 字段。
```json
{"question": "Which early computing system influenced desktop metaphor?", "answer": "Xerox Alto (1973)", "context": "早期图形界面计算机系统..."}
{"question": "Which Japanese anime depicts humans struggling...", "answer": "甲鉄城のカバネリ", "context": "关于人类在装甲列车上生存的动画..."}
```

## Web 界面流程
1) 打开前端 → 自动检查配置状态（/config/status）
2) 上传 .jsonl/.json 数据（/upload）
3) 开始三模型评估（/test/start）
4) 轮询任务状态（/test/{task_id}）
5) 下载 CSV 报告（/test/{task_id}/download-csv）

前端实现参考：[frontend/src/App.jsx](frontend/src/App.jsx)。

## API 接口
- GET `/`：服务状态
- GET `/config/status`：检查配置文件状态
- POST `/upload`：上传数据文件（.jsonl/.json）
- POST `/test/start`：开始评估（请求体为文件ID数组）
- GET `/test/{task_id}`：查询进度/结果
- GET `/test/{task_id}/download-csv`：下载详细CSV报告

示例（Python）：
```python
import requests

# 上传
fid = requests.post('http://localhost:8000/upload',
                    files={'file': open('data/data.jsonl','rb')}).json()['file_id']

# 启动
task = requests.post('http://localhost:8000/test/start', json=[fid]).json()
tid = task['task_id']

# 轮询
print(requests.get(f'http://localhost:8000/test/{tid}').json())

# 下载报告
csv = requests.get(f'http://localhost:8000/test/{tid}/download-csv')
open('report.csv','wb').write(csv.content)
```

实现参考：
- 后端路由：[web_api.py](web_api.py)
- 评估逻辑入口与多模型聚合：[benchmarks/InteractComp.py](benchmarks/InteractComp.py)
- Agent工厂/调用：[workflow/InteractComp.py](workflow/InteractComp.py)

## 命令行使用
```bash
# 多模型评估（默认）
python run_baseline.py multi

# 单模型评估
python run_baseline.py single

# 对比评估
python run_baseline.py comparison
```

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