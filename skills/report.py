import datetime
import random
from skills.base import BaseSkill


class ReportSkill(BaseSkill):
    name = "report"
    description = "生成符合国家规范的房产估价报告"

    async def execute(self, params: dict) -> dict:
        valuation = params.get("valuation", {})
        mortgage = params.get("mortgage", {})
        compliance = params.get("compliance", {})
        user_request = params.get("userRequest", {})

        now = datetime.datetime.now()
        date_str = f"{now.year}年{now.month}月{now.day}日"
        report_id = (
            f"RE-{now.year}{now.month:02d}{now.day:02d}-{random.randint(0, 9999):04d}"
        )

        city = user_request.get("city", "")
        district = user_request.get("district", "")
        keyword = user_request.get("keyword", "")
        area = user_request.get("area", 100)
        house_count = user_request.get("houseCount", 0)

        unit_price = valuation.get("unitPrice", 0)
        total_price = valuation.get("totalPrice", 0)
        base_price = valuation.get("basePrice", 0)
        diff = unit_price - base_price
        diff_ratio = (diff / base_price * 100) if base_price > 0 else 0

        required_income = (mortgage.get("mortgage", {}).get("totalMonthly", 0)) * 2

        if abs(diff_ratio) < 5:
            opinion = "市场价格平稳。"
            conclusion_text = f"估价单价与区域均价持平"
        elif diff_ratio > 0:
            opinion = "该小区价格高于区域平均水平。"
            conclusion_text = f"估价单价高于区域均价 {abs(diff_ratio):.1f}%"
        else:
            opinion = "该小区性价比较高。"
            conclusion_text = f"估价单价低于区域均价 {abs(diff_ratio):.1f}%"

        return {
            "success": True,
            "reportId": report_id,
            "reportDate": date_str,
            "purpose": "为房产交易提供价值参考依据",
            "subjectProperty": {
                "name": keyword or "未知小区",
                "location": f"{city}{district}",
                "area": f"{area}㎡",
                "type": "住宅",
                "years": f"{valuation.get('yearsOld', 5)}年",
            },
            "method": "市场比较法（Market Comparison Approach）",
            "result": {
                "totalPrice": total_price,
                "unitPrice": unit_price,
                "currency": "人民币",
            },
            "marketAnalysis": {
                "cityAvgPrice": base_price,
                "districtAvgPrice": base_price,
                "diffRatio": round(diff_ratio, 1),
                "conclusion": conclusion_text,
            },
            "comparables": [
                {"name": c["name"], "price": c["price"], "years": 2026 - c.get("built", 2020)}
                for c in valuation.get("comparables", [])[:3]
            ],
            "mortgageAdvice": {
                "downPayment": mortgage.get("downPayment", 0),
                "monthlyPayment": mortgage.get("mortgage", {}).get("totalMonthly", 0),
                "requiredIncome": round(required_income, 2),
            },
            "compliance": {
                "score": compliance.get("score", 0),
                "conclusion": compliance.get("conclusion", ""),
            },
            "opinion": f"经评估，{city}该住宅物业单价为 {unit_price:.0f} 元/㎡，" + opinion + f"总价 {total_price:.0f} 元。",
            "disclaimer": "本报告仅供参考，不构成投资建议。报告基于公开数据和市场调研生成，实际交易价格可能因具体房屋状况存在差异。",
        }
