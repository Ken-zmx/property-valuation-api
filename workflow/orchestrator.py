"""工作流编排器 — 按 DAG 顺序调用 4 个 Skill。"""

from skills.data_retrieval import DataRetrievalSkill
from skills.mortgage import MortgageSkill
from skills.compliance import ComplianceSkill
from skills.report import ReportSkill


class Orchestrator:
    def __init__(self):
        self.data_retrieval = DataRetrievalSkill()
        self.mortgage = MortgageSkill()
        self.compliance = ComplianceSkill()
        self.report = ReportSkill()

    async def run(self, city: str, district: str = "", keyword: str = "",
                  area: float = 100, house_count: int = 0, query: str = "") -> dict:
        """执行完整估价工作流。

        顺序: data_retrieval → mortgage → compliance → report
        data_retrieval 失败时直接返回错误。
        """
        user_request = {
            "city": city,
            "district": district,
            "keyword": keyword,
            "area": area,
            "houseCount": house_count,
            "propertyType": "住宅",
        }

        # Step 1: 数据检索（含匹配）
        retrieval_params = {
            "city": city,
            "district": district,
            "area": area,
            "keyword": keyword,
        }
        retrieval_result = await self.data_retrieval.execute(retrieval_params)

        if not retrieval_result.get("success"):
            return {
                "success": False,
                "error": retrieval_result.get("error", "估价失败"),
                "matchStatus": retrieval_result.get("matchStatus", "none"),
                "matchMsg": retrieval_result.get("matchMsg", ""),
                "matchSuggestion": retrieval_result.get("matchSuggestion"),
            }

        # Step 2: 房贷税费
        mortgage_result = await self.mortgage.execute({
            "city": city,
            "totalPrice": retrieval_result["totalPrice"],
            "area": area,
            "houseCount": house_count,
            "yearsOwned": 5,
            "onlyHouse": True,
            "loanTerm": 30,
        })

        # Step 3: 合规校验
        compliance_result = await self.compliance.execute({
            "city": city,
            "totalPrice": retrieval_result["totalPrice"],
            "downPaymentRatio": mortgage_result["downPaymentRatio"] / 100,
            "houseCount": house_count,
            "loanRate": mortgage_result["loanRate"],
        })

        # Step 4: 报告生成
        report_result = await self.report.execute({
            "valuation": retrieval_result,
            "mortgage": mortgage_result,
            "compliance": compliance_result,
            "userRequest": user_request,
        })

        return {
            "success": True,
            "parsed": {
                "city": city,
                "district": district,
                "keyword": keyword,
                "area": area,
                "houseCount": house_count,
                "confidence": 0.85 if retrieval_result.get("matchStatus") == "exact" else 0.7,
            },
            "valuation": retrieval_result,
            "mortgage": mortgage_result,
            "compliance": compliance_result,
            "report": report_result,
        }
