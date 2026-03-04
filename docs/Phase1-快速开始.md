# Phase1 OpenClaw 集成 - 快速开始

## 5 分钟快速验证

### 前提条件

- OpenClaw Gateway 运行在 `localhost:19001`
- Python 3.10+ 已安装
- Node.js 18+ 已安装

### 步骤 1: 配置环境变量

```bash
cd backend
cp .env.example .env
```

编辑 `.env`，添加：

```bash
OPENCLAW_GATEWAY_URL=http://localhost:19001
OPENCLAW_ENABLED=True
```

### 步骤 2: 启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 步骤 3: 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 步骤 4: 验证集成

1. 访问 http://localhost:5173
2. 查看右上角 OpenClaw 状态指示器
3. 🟢 绿色 = 成功！

---

## 运行测试

### 单元测试

```bash
cd backend
pytest tests/core/test_openclaw_client.py -v
pytest tests/api/v1/test_openclaw.py -v
```

### 集成测试

```bash
cd backend
export OPENCLAW_GATEWAY_URL=http://localhost:19001
pytest tests/integration/test_openclaw_integration.py -v -m integration
```

---

## API 快速测试

### 健康检查（无需认证）

```bash
curl http://localhost:8000/api/v1/openclaw/health
```

预期响应：

```json
{
  "status": "healthy",
  "version": "2026.2.6-3",
  "gateway_url": "http://localhost:19001"
}
```

---

## 故障排查

### OpenClaw 连接失败？

1. 检查 Gateway 是否运行：
   ```bash
   curl http://localhost:19001/health
   ```

2. 检查环境变量：
   ```bash
   echo $OPENCLAW_GATEWAY_URL
   ```

3. 查看后端日志：
   ```bash
   tail -f backend/logs/app.log
   ```

---

## 下一步

- 📖 完整部署指南: [Phase1-部署指南.md](./Phase1-部署指南.md)
- 🧪 用户验收测试: [Phase1-用户故事与验收测试.md](./Phase1-用户故事与验收测试.md)
- 🔍 代码审查报告: [Phase1-代码审查报告.md](./Phase1-代码审查报告.md)

---

**快速开始版本**: v1.0
**最后更新**: 2026-03-03
