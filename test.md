# BettaFish 快速测试与验证指南

本文档总结了 BettaFish 系统的快速测试模式（Fast Test Mode），旨在帮助开发者在不消耗大量 Token 和时间的情况下，快速验证系统的核心流程、组件连接以及基本功能。此文档也可作为未来自动化测试脚本的设计参考。

## 1. 测试模式概述

为了平衡开发效率与功能验证，系统提供了两种测试配置：

### 1.1 纯快速测试模式 (Fast Test Mode)
- **配置项**: `FAST_TEST_MODE = True`
- **行为**:
  - **跳过** 所有的外部 API 调用（包括 LLM 推理、网络搜索、数据库繁重查询）。
  - **返回** 预设的 Mock（模拟）数据。
  - **目的**: 极速验证系统各组件（Insight, Media, Query, Report, Forum）的消息传递、数据流转和 UI 渲染是否正常。
  - **耗时**: 极短（通常几秒钟）。

### 1.2 连通性验证模式 (Connectivity Check)
- **配置项**: `FAST_TEST_MODE = True` 且 `TEST_SEARCH_AND_ANALYSIS = True`
- **行为**:
  - **执行** 真实的轻量级工具调用（例如：执行一次真实的 Google/Bocha 搜索，或一次简单的数据库查询）。
  - **跳过** 耗时的 LLM 深度分析和长文本生成。
  - **目的**: 在快速测试的基础上，额外验证外部工具（搜索 API、数据库连接）的连通性和凭证有效性。
  - **耗时**: 短（取决于网络搜索响应速度）。

---

## 2. 如何配置

你可以通过 Web 界面或直接修改配置文件来启用测试模式。

### 方式 A: Web 界面配置 (推荐)
1. 启动 BettaFish 系统 (`docker-compose up -d`).
2. 访问 Web UI (默认 `http://localhost:5002`).
3. 点击右上角的 **"LLM 配置"** 按钮。
4. 滚动到 **"快速测试模式"** (Fast Test Mode) 区域。
5. 设置 **"开启快速测试"** 为 `开启`。
6. (可选) 设置 **"测试搜索与分析"** 为 `开启` 以验证工具连接。
7. 点击 **"保存配置"**。

### 方式 B: 环境变量配置 (.env)
直接编辑项目根目录下的 `.env` 文件：

```bash
# 开启快速测试模式
FAST_TEST_MODE=True

# (可选) 开启连通性验证
TEST_SEARCH_AND_ANALYSIS=True
```

*注意：修改 .env 文件后通常需要重启应用或在 Web 界面点击“刷新配置”才能生效。*

---

## 3. 执行测试

### 3.1 手动测试
1. 确保系统已启动且配置已生效。
2. 在 Web 首页的搜索框中输入任意测试关键词（例如 "测试流程"）。
3. 点击搜索。
4. **观察结果**:
   - 如果配置正确，你应该会在几秒钟内看到三个 Engine 返回简短的模拟分析结果。
   - Report Engine 应该会生成一份基于 `FastTestTemplate.md` 的简短测试报告。

### 3.2 自动化测试 (API)
可以使用 HTTP 请求直接触发测试流程，适合集成到 CI/CD 或自动化脚本中。

**测试接口**: `POST /api/search`

**Curl 示例**:
```bash
curl -X POST http://localhost:5002/api/search \
     -H "Content-Type: application/json" \
     -d '{"query": "自动化测试指令"}'
```

**预期响应**:
```json
{
  "success": true,
  "query": "自动化测试指令",
  "results": {
    "insight": { ... },
    "media": { ... },
    "query": { ... }
  }
}
```

---

## 4. 验证点检查清单

在自动化测试脚本中，可以通过检查以下点来判断测试是否通过：

1.  **HTTP 状态码**: `/api/search` 接口返回 `200`。
2.  **响应结构**: 返回的 JSON 中包含 `insight`, `media`, `query` 三个字段。
3.  **Mock 标记**:
    - 在纯快速模式下，返回的内容应包含预设的 Mock 文本（如 "This is a MOCK insight analysis"）。
4.  **工具日志 (仅连通性模式)**:
    - 检查日志中是否包含 `execute_search_tool` 的成功调用记录，且未抛出 API Key 错误。

## 5. 故障排查

- **现象**: 仍然在这个过程花费了很长时间。
  - **检查**: 确认 `FAST_TEST_MODE` 是否真正生效（Web UI 显示为开启，或 `.env` 中为 True）。
  
- **现象**: 连通性测试报错。
  - **检查**: 如果 `TEST_SEARCH_AND_ANALYSIS` 开启但报错，请检查 `TAVILY_API_KEY`, `BOCHA_WEB_SEARCH_API_KEY` 或数据库连接配置是否正确。
