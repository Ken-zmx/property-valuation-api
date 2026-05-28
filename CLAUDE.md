# 房产估价智能体 — 项目规范

## 项目定位
基于 AI 的房产估价智能体系统，支持自然语言查询、智能估价、房贷计算、报告生成。

## 架构
- 后端：Python FastAPI（RESTful API）
- 前端：单 HTML SPA（零构建工具）
- Skill 架构：独立封装、统一接口、工作流编排

## 目录约定
```
backend/
├── skills/       # 技能模块（核心逻辑）
├── workflow/      # 工作流编排
├── data/          # 数据层
└── main.py        # API 入口
frontend/
└── index.html     # 前端 SPA
```

## Skill 接口规范
每个 Skill 必须实现：
```python
class BaseSkill:
    name: str
    description: str
    
    async def execute(self, params: dict) -> dict:
        """执行技能逻辑"""
        pass
```

## 工作流约定
- 编排器按 DAG 顺序调用技能
- 每个技能的输出作为下游技能输入的一部分
- 支持串行和并行执行

## 命名规范
- Python：snake_case
- API 端点：小写 + 下划线
- 数据字段：驼峰（前端接口层）

## 质量要求
- 代码改完必须验证
- 不绕开报错，找根本原因
- 注释只写"为什么"，不写"做了什么"
