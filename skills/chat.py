"""AI 对话 Skill — DeepSeek API 驱动的智能估价助手。"""

import json
import os
from skills.base import BaseSkill
from workflow.orchestrator import Orchestrator

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

SYSTEM_PROMPT = """你是智估价 AI，一个专业的房产估价助手。你可以帮助用户：
1. 查询特定小区的房价信息
2. 计算房贷月供和税费
3. 对比不同小区的价格
4. 推荐符合预算的房源

当前支持的搜索方式：用户可以直接说"帮我看看深圳南山华润城润府100平的价格"，或者"我在北京预算800万想买海淀区的房子有什么推荐"。

当用户提问后，请先判断是否需要调用估价工具。如果需要，只输出一段 JSON（不要输出别的内容），格式如下：
{"action":"valuate","city":"深圳","district":"南山区","keyword":"华润城润府","area":100,"houseCount":0}

city 必须从以下列表选择：深圳、北京、上海、广州、杭州、成都、武汉、南京、重庆、天津
district 是该城市的区域，如不确定可为空字符串
keyword 是小区名称，从用户问题中提取，如没有明确小区名可为空字符串
area 是面积（平米），如没有提到默认为100
houseCount 是房屋套数，首套房为0，二套房为1，默认为0

如果用户只是闲聊（打招呼、问功能等），输出：
{"action":"chat","reply":"你的回复内容"}

注意：只输出 JSON，不要有任何其他文字。"""


class ChatSkill(BaseSkill):
    name = "chat"
    description = "AI 对话助手，理解自然语言并调用估价工具生成智能回复"

    def __init__(self):
        self.orchestrator = Orchestrator()

    def _call_deepseek(self, messages: list) -> str:
        """调用 DeepSeek API，返回模型输出文本。"""
        if not DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY 未设置")

        from openai import OpenAI
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()

    async def execute(self, params: dict) -> dict:
        user_message = params.get("message", "")
        if not user_message:
            return {"success": False, "error": "请输入您的问题"}

        # Step 1: 让 DeepSeek 理解意图，提取估价参数
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        try:
            raw = self._call_deepseek(messages)
            # 清理可能的 markdown 代码块标记
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
                if raw.endswith("```"):
                    raw = raw[:-3]
            intent = json.loads(raw)
        except Exception as e:
            return {
                "success": False,
                "error": f"AI 理解失败，请换个方式描述您的需求。({str(e)})",
                "raw": raw if 'raw' in dir() else "",
            }

        # Step 2: 根据意图处理
        action = intent.get("action", "chat")

        if action == "chat":
            return {"success": True, "type": "chat", "reply": intent.get("reply", "你好！有什么可以帮你的吗？")}

        if action == "valuate":
            city = intent.get("city", "")
            district = intent.get("district", "")
            keyword = intent.get("keyword", "")
            area = intent.get("area", 100)
            house_count = intent.get("houseCount", 0)

            # 跑估价流程
            result = await self.orchestrator.run(
                city=city,
                district=district,
                keyword=keyword,
                area=area,
                house_count=house_count,
                query=user_message,
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "type": "valuate",
                    "error": result.get("matchMsg", result.get("error", "估价失败")),
                    "valuation": result,
                }

            # Step 3: 用估价结果让 DeepSeek 生成自然语言回复
            summary = self._build_summary(result)
            reply_messages = [
                {"role": "system", "content": "你是智估价 AI 助手。根据下面的估价数据，用自然语言回复用户。要友好、专业、简洁，用中文。可以补充一些购买建议。"},
                {"role": "user", "content": f"用户问题：{user_message}\n\n估价结果：\n{summary}\n\n请生成一段友好回复。"},
            ]

            try:
                reply = self._call_deepseek(reply_messages)
            except Exception:
                reply = self._format_result(result)

            return {
                "success": True,
                "type": "valuate",
                "reply": reply,
                "valuation": result,
            }

        return {"success": False, "error": "未知操作"}

    def _build_summary(self, result: dict) -> str:
        v = result.get("valuation", {})
        m = result.get("mortgage", {})
        c = result.get("compliance", {})

        lines = [
            f"城市：{v.get('city', '')}",
            f"区域：{v.get('district', '')}",
            f"小区：{v.get('detail', {}).get('name', '未知') if v.get('detail') else '未匹配具体小区'}",
            f"面积：{result.get('parsed', {}).get('area', 100)}㎡",
            f"估价单价：{v.get('unitPrice', 0):.0f} 元/㎡",
            f"估价总价：{v.get('totalPrice', 0):.0f} 元（约{(v.get('totalPrice', 0)/10000):.0f}万）",
            f"区域均价：{v.get('basePrice', 0):.0f} 元/㎡",
            f"房龄：{v.get('yearsOld', 5)}年",
        ]

        if m.get("success"):
            mt = m.get("mortgage", {})
            tax = m.get("taxes", {})
            lines.append(f"首付：{m.get('downPayment', 0):.0f} 元（{m.get('downPaymentRatio', 0):.0f}%）")
            lines.append(f"月供：{mt.get('totalMonthly', 0):.0f} 元（公积金{mt.get('fundMonthly', 0):.0f} + 商贷{mt.get('commercialMonthly', 0):.0f}）")
            lines.append(f"税费合计：{tax.get('total', 0):.0f} 元")

        if c.get("success"):
            lines.append(f"合规检查：{c.get('conclusion', '')}")

        return "\n".join(lines)

    def _format_result(self, result: dict) -> str:
        v = result.get("valuation", {})
        m = result.get("mortgage", {})
        tp = v.get("totalPrice", 0)
        up = v.get("unitPrice", 0)
        community = v.get("detail", {}).get("name", "该小区") if v.get("detail") else "该小区"

        parts = [
            f"🏠 {community} | {v.get('city', '')}{v.get('district', '')}",
            f"💰 估价总价：{tp:.0f} 元（约{tp/10000:.0f}万）| 单价：{up:.0f} 元/㎡",
        ]

        if m.get("success"):
            mt = m.get("mortgage", {})
            parts.append(f"📊 首付{m.get('downPayment', 0):.0f}元 | 月供{mt.get('totalMonthly', 0):.0f}元")
            parts.append(f"🧾 税费合计{m.get('taxes', {}).get('total', 0):.0f}元")

        return "\n".join(parts)
