# InteractComp 三模型标注质量测试平台

🤖 **智能评估标注质量的AI驱动平台**

InteractComp是一个基于多AI模型的标注数据质量评估平台。通过让多个AI模型尝试回答标注中的问题，评估标注的难度和质量。

## 📊 核心理念

**优秀的标注应该让AI模型难以找到正确答案**

- ✅ **质量合格**：少数模型答对 → 标注具有挑战性
- ❌ **质量不合格**：多数模型答对 → 标注过于简单，需要增加难度

## 🎯 评估逻辑

| 评估结果 | 判断标准 | 含义 |
|---------|---------|------|
| **质量合格** | 0-1个模型答对 | 标注难度适中，能够有效区分能力 |
| **质量不合格** | 2-3个模型答对 | 标注过于简单，需要增加混淆性和难度 |

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd InteractComp

# 安装Python依赖
pip install -r requirements.txt

# 安装前端依赖（如果需要Web界面）
cd frontend
npm install
cd ..
```

### 2. 配置API Keys

```bash
# 复制配置文件模板
cp config/config2.example.yaml config/config2.yaml

# 编辑配置文件，填入你的API Keys
vim config/config2.yaml
```

配置文件格式：
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
    api_type: "openai"  # 通过代理访问
    base_url: "https://one-api.example.com/v1"
    api_key: "sk-xxxxxxxxxx"
    temperature: 0
```

### 3. 启动服务

#### Web界面方式（推荐）
```bash
# 启动后端API
python web_api.py

# 启动前端（新终端）
cd frontend
npm run dev

# 访问 http://localhost:3000
```

#### 命令行方式
```bash
# 多模型评估（默认）
python run_baseline.py multi

# 单模型评估
python run_baseline.py single

# 对比评估
python run_baseline.py comparison
```

## 📁 数据格式

### InteractComp格式 (.jsonl)

每行一个JSON对象，包含以下字段：

```json
{
  "question": "问题描述",
  "answer": "正确答案（隐藏）",
  "context": "上下文信息，用于回答用户询问"
}
```

**示例数据：**
```json
{"question": "Which Japanese anime depicts humans struggling to survive inside enclosed strongholds?", "answer": "甲鉄城のカバネリ (Kabaneri of the Iron Fortress)", "context": "这是一部关于人类在装甲列车上生存的动画..."}
{"question": "Which early computing system influenced desktop metaphor?", "answer": "Xerox Alto (1973)", "context": "这是一个早期的图形界面计算机系统..."}
```

## 🌐 Web界面使用

### 1. 配置检查
- 页面会自动检查`config2.yaml`配置状态
- 绿色✅表示配置就绪，橙色⚠️表示需要完善配置

### 2. 上传数据
- 支持`.jsonl`格式文件
- 可以上传多个文件，系统会自动合并

### 3. 开始评估
- 点击"开始三模型评估"按钮
- 系统会并行运行三个AI模型进行评估

### 4. 查看结果
- **质量合格率**：少数模型答对的比例
- **质量不合格率**：多数模型答对的比例  
- **详细报告**：每个问题的具体模型表现
- **CSV下载**：完整的评估数据

## 🖥️ 命令行使用

### 多模型评估
```bash
python run_baseline.py multi
```

输出示例：
```
🤖 Running multi-model evaluation: ['gpt-5-mini', 'gpt-5', 'claude-4-sonnet']
🎯 Multi-Model Evaluation Results:
📊 Total Questions: 100
❌ Quality Failed: 25 (25.0%)
✅ Quality Passed: 75 (75.0%)
💰 Total Cost: $2.450
💰 Average Cost: $0.0245
```

### 对比评估
```bash
python run_baseline.py comparison
```

比较单模型vs多模型的评估结果和成本差异。

## 🔧 配置说明

### 支持的API类型

| api_type | 描述 | base_url示例 |
|----------|------|-------------|
| `openai` | OpenAI官方API | `https://api.openai.com/v1` |
| `azure` | Azure OpenAI | `https://your-resource.openai.azure.com` |
| `ollama` | 本地Ollama服务 | `http://localhost:11434/v1` |
| `groq` | Groq API | `https://api.groq.com/openai/v1` |

### 搜索引擎配置（可选）

```yaml
search:
  engines:
    google:
      api_key: "your_serper_api_key"  # Serper.dev API
  request_settings:
    timeout: 30
    max_results_per_query: 5
```

## 📡 API文档

### 主要接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 服务状态检查 |
| `/config/status` | GET | 配置文件状态检查 |
| `/upload` | POST | 上传数据文件 |
| `/test/start` | POST | 开始三模型评估 |
| `/test/{task_id}` | GET | 查询评估状态 |
| `/test/{task_id}/download-csv` | GET | 下载CSV报告 |

### 使用示例

```python
import requests

# 检查配置状态
response = requests.get('http://localhost:8000/config/status')
print(response.json())

# 上传文件
files = {'file': open('data.jsonl', 'rb')}
response = requests.post('http://localhost:8000/upload', files=files)
file_id = response.json()['file_id']

# 开始评估
response = requests.post('http://localhost:8000/test/start', 
                        json={'file_ids': [file_id]})
task_id = response.json()['task_id']

# 查询状态
response = requests.get(f'http://localhost:8000/test/{task_id}')
print(response.json())
```

## 🏗️ 项目结构

```
InteractComp/
├── benchmarks/           # 评估基准测试
│   ├── InteractComp.py  # 多模型评估逻辑
│   └── benchmark.py     # 基础评估框架
├── workflow/            # AI Agent工作流
│   ├── InteractComp.py  # 交互式推理Agent
│   ├── search_engine.py # 搜索引擎支持
│   └── user_agent.py    # 用户交互代理
├── utils/               # 工具模块
│   ├── async_llm.py     # 异步LLM调用
│   └── logs.py          # 日志系统
├── frontend/            # React前端
│   ├── src/App.jsx      # 主应用组件
│   └── package.json     # 前端依赖
├── config/              # 配置文件
│   └── config2.example.yaml
├── data/                # 示例数据
├── web_api.py           # FastAPI后端服务
├── run_baseline.py      # 命令行评估工具
└── requirements.txt     # Python依赖
```

## 🚀 部署说明

### 生产环境部署

1. **准备服务器环境**
```bash
# 安装Python 3.11+
# 安装Node.js 18+
# 安装Nginx
```

2. **构建和部署**
```bash
# 构建前端
cd frontend && npm run build

# 安装Python依赖
pip install -r requirements.txt

# 配置API Keys
cp config/config2.example.yaml config/config2.yaml
vim config/config2.yaml
```

3. **配置Nginx**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # 前端静态文件
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
    
    # API代理
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

4. **启动服务**
```bash
# 使用gunicorn启动后端（生产环境推荐）
gunicorn -w 4 -k uvicorn.workers.UvicornWorker web_api:app --bind 0.0.0.0:8000

# 或使用systemd管理服务
sudo systemctl enable interactcomp
sudo systemctl start interactcomp
```

### Docker部署（推荐）

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
# 构建镜像
docker build -t interactcomp .

# 运行容器
docker run -d -p 8000:8000 -v ./config:/app/config interactcomp
```

## ❓ 常见问题

### Q: 为什么需要三个模型？
A: 不同能力的模型可以更全面地评估标注质量。如果连最强的模型都答错，说明标注确实有挑战性。

### Q: 如何选择评估模型？
A: 推荐使用不同能力层级的模型：
- GPT-5-mini（快速模型）
- GPT-5（标准模型）
- Claude-4-Sonnet（推理模型）

### Q: 评估成本如何控制？
A: 
- 多模型评估时自动减少推理轮数（3轮）
- 支持并发控制参数
- 显示实时成本统计

### Q: 支持哪些数据格式？
A: 目前支持InteractComp格式的JSONL文件，包含question/answer/context字段。

### Q: 如何使用代理API？
A: 在config2.yaml中设置对应的base_url和api_key即可，支持one-api、new-api等代理服务。

### Q: 可以添加更多模型吗？
A: 可以，在config2.yaml中添加模型配置，并在代码中更新EVALUATION_MODELS列表。

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 联系

如有问题，请提交Issue或联系项目维护者。

---

**🎯 InteractComp - 让AI帮你评估标注质量！**