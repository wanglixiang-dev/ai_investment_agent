# Resume Project Description

## English Version

**Multi-Agent Investment Research System**  
Built an AI-powered investment research platform that generates structured equity research reports from market data, news, and SEC filing context. Implemented a FastAPI backend with LangGraph workflow orchestration, OpenAI Responses API tool calling, yfinance-based stock and news tools, local SEC filing RAG, SQLAlchemy persistence, Redis caching, Docker Compose, GitHub Actions CI, and a lightweight web UI.

**Resume Bullets**

- Developed a multi-step LangGraph research workflow with explicit nodes for market data retrieval, news sentiment analysis, SEC filing context retrieval, and report generation.
- Integrated OpenAI tool calling with backend tools for stock quotes and news analysis, enabling LLM-driven research workflows with structured tool execution traces.
- Built yfinance-powered stock and news data tools with Redis-backed cache-aside caching to reduce repeated external data requests and improve resilience.
- Implemented local SEC filing RAG using document chunking and keyword-based retrieval, then injected retrieved filing context into final investment reports.
- Designed SQLAlchemy persistence for saved reports, workflow traces, data sources, and errors, supporting SQLite locally and PostgreSQL via Docker Compose.
- Added FastAPI routes, OpenAPI documentation, Markdown report export, health checks, Docker Compose services, and GitHub Actions CI with a pytest suite.
- Built a lightweight browser UI served by FastAPI for generating reports, viewing workflow traces, and opening Markdown exports.

**Tech Stack**

Python, FastAPI, LangGraph, OpenAI API, SQLAlchemy, PostgreSQL, Redis, Docker Compose, GitHub Actions, yfinance, Pytest, HTML/CSS/JavaScript

## 中文版本

**Multi-Agent Investment Research System**  
构建了一个 AI 投资研究系统，能够结合股票行情、新闻分析和 SEC 财报上下文生成结构化投资研究报告。项目使用 FastAPI 搭建后端，使用 LangGraph 编排多步骤 Agent 工作流，集成 OpenAI Tool Calling、yfinance 股票与新闻工具、本地 SEC Filing RAG、SQLAlchemy 持久化、Redis 缓存、Docker Compose、GitHub Actions CI，并提供轻量前端页面。

**简历要点**

- 使用 LangGraph 设计多节点投资研究工作流，覆盖行情获取、新闻情绪分析、SEC 财报上下文检索和报告生成。
- 集成 OpenAI Responses API Tool Calling，将股票行情和新闻分析封装为可被 LLM 调用的后端工具。
- 基于 yfinance 实现股票数据和新闻分析工具，并使用 Redis cache-aside 模式缓存外部数据请求。
- 实现本地 SEC Filing RAG，支持文档切块、关键词检索和报告上下文注入。
- 使用 SQLAlchemy 设计报告持久化层，保存最终报告、执行步骤、数据源和错误信息，支持 SQLite 本地开发与 PostgreSQL Docker 环境。
- 提供 FastAPI REST API、OpenAPI 文档、Markdown 报告导出、健康检查、Docker Compose 和 GitHub Actions CI。
- 实现轻量 Web UI，支持输入 ticker 生成研究报告、查看工作流 trace 和打开 Markdown 导出结果。

**技术栈**

Python, FastAPI, LangGraph, OpenAI API, SQLAlchemy, PostgreSQL, Redis, Docker Compose, GitHub Actions, yfinance, Pytest, HTML/CSS/JavaScript
