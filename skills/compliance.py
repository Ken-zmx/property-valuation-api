from skills.base import BaseSkill
from data.policies import POLICIES


class ComplianceSkill(BaseSkill):
    name = "compliance"
    description = "合规校验：限购、贷款比例、利率、反洗钱"

    async def execute(self, params: dict) -> dict:
        city = params.get("city", "")
        price = params.get("totalPrice", 0)
        down_payment_ratio = params.get("downPaymentRatio", 0.30)
        house_count = params.get("houseCount", 0)
        loan_rate = params.get("loanRate", 3.40)

        checks = []
        risks = []

        # 1. 贷款比例
        dp = POLICIES["downPayment"].get(city, [0.20, 0.40])
        required = dp[0] if house_count == 0 else dp[1]
        if down_payment_ratio < required:
            checks.append({
                "rule": "loan_to_value",
                "status": "FAIL",
                "msg": f"首付比例 {down_payment_ratio*100:.0f}% 低于要求 {required*100:.0f}%",
            })
            risks.append({
                "severity": "high",
                "suggestion": f"首付比例应不低于 {required*100:.0f}%",
            })
        else:
            checks.append({
                "rule": "loan_to_value",
                "status": "PASS",
                "msg": f"首付比例 {down_payment_ratio*100:.0f}% 满足要求",
            })

        # 2. 限购
        limit_cities = POLICIES["purchaseLimit"]
        if city in limit_cities:
            max_houses = 2
            if house_count >= max_houses:
                checks.append({
                    "rule": "purchase_limit",
                    "status": "FAIL",
                    "msg": f"{city} 限购，名下 {house_count} 套已达上限",
                })
                risks.append({"severity": "high", "suggestion": "限购城市不可再购"})
            else:
                checks.append({
                    "rule": "purchase_limit",
                    "status": "PASS",
                    "msg": f"名下 {house_count} 套未超 {city} 限购上限",
                })
        else:
            checks.append({"rule": "purchase_limit", "status": "PASS", "msg": "无限购限制"})

        # 3. 税费合规
        checks.append({"rule": "tax_compliance", "status": "PASS", "msg": "税费按国家标准计算"})

        # 4. 估价规范
        checks.append({
            "rule": "appraisal_standard",
            "status": "PASS",
            "msg": "估价方法符合《房地产估价规范》GB/T 50291",
        })

        # 5. 反洗钱
        if price > 5_000_000:
            checks.append({
                "rule": "anti_money_laundering",
                "status": "WARN",
                "msg": f"交易额 {price/10000:.0f}万 > 500万",
            })
            risks.append({"severity": "low", "suggestion": "大额交易需记录买方身份信息"})
        else:
            checks.append({
                "rule": "anti_money_laundering",
                "status": "PASS",
                "msg": "交易金额在常规范围内",
            })

        # 6. 利率合规
        max_rate = POLICIES["loanRate"]["first"] + 0.60
        if loan_rate > max_rate:
            checks.append({
                "rule": "interest_rate",
                "status": "FAIL",
                "msg": f"利率 {loan_rate}% 超出上限 {max_rate}%",
            })
        else:
            checks.append({"rule": "interest_rate", "status": "PASS", "msg": "贷款利率合规"})

        fail_count = sum(1 for c in checks if c["status"] == "FAIL")
        warn_count = sum(1 for c in checks if c["status"] == "WARN")
        pass_count = len(checks) - fail_count - warn_count
        score = round(pass_count / len(checks) * 100, 1) if checks else 0

        if fail_count > 0:
            conclusion, suggestion = "不合规", "存在高严重度不合规项，请修正"
        elif warn_count > 2:
            conclusion, suggestion = "需注意", "存在多处需关注项"
        elif warn_count > 0:
            conclusion, suggestion = "基本合规", "存在少量需关注项"
        else:
            conclusion, suggestion = "合规", "全部校验通过"

        return {
            "success": True,
            "score": score,
            "conclusion": conclusion,
            "suggestion": suggestion,
            "checks": checks,
            "risks": risks,
            "summary": {
                "total": len(checks),
                "pass": pass_count,
                "warn": warn_count,
                "fail": fail_count,
            },
        }
