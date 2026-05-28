import random
from skills.base import BaseSkill
from data.cities import DISTRICT_PRICES
from data.communities import COMMUNITIES
from matching.matcher import CommunityMatcher


class DataRetrievalSkill(BaseSkill):
    name = "data_retrieval"
    description = "检索城市均价、小区数据，执行关键词匹配和可比案例筛选"

    def __init__(self):
        self.matcher = CommunityMatcher(COMMUNITIES)

    async def execute(self, params: dict) -> dict:
        city = params.get("city", "")
        district = params.get("district", "")
        area = params.get("area", 100)
        keyword = params.get("keyword", "")

        prices = DISTRICT_PRICES.get(city, {})
        base_price = prices.get(district) if district else prices.get("_default", 0)

        communities = COMMUNITIES.get(city, {})
        district_communities = communities.get(district, []) if district else []
        if not district_communities:
            for d in communities:
                district_communities.extend(communities[d])

        # ── 关键词匹配 ──
        match_result = None
        if keyword:
            match_result = self.matcher.match(keyword, city, district)

        if match_result and match_result["status"] == "none":
            return {
                "success": False,
                "error": match_result["msg"],
                "matchStatus": "none",
                "matchMsg": match_result["msg"],
                "matchSuggestion": match_result["suggestion"],
            }

        matched_community = match_result["community"] if match_result else None
        match_status = match_result["status"] if match_result else None
        match_msg = match_result["msg"] if match_result else None
        match_suggestion = match_result["suggestion"] if match_result else None

        # ── 计算估价 ──
        age_adjust = -0.003 * 5
        area_adjust = 0.05 if area > 120 else (-0.05 if area < 70 else 0)

        if matched_community:
            unit_price = matched_community["price"]
            years_old = 2026 - matched_community["built"]
        else:
            unit_price = base_price
            years_old = 5

        adjusted_unit = unit_price * (1 + age_adjust + area_adjust)
        total_price = adjusted_unit * area

        # 可比案例
        all_district = district_communities or []
        comparables = all_district[:4] if all_district else []
        comparables_out = []
        for c in comparables:
            comparables_out.append({
                "name": c["name"],
                "price": c["price"],
                "built": c["built"],
                "matchScore": round(random.random() * 0.2 + 0.75, 2),
            })

        return {
            "success": True,
            "city": city,
            "district": district,
            "basePrice": base_price,
            "unitPrice": round(adjusted_unit, 2),
            "totalPrice": round(total_price, 2),
            "comparables": comparables_out,
            "matchedCount": len(all_district),
            "yearsOld": years_old,
            "matchStatus": match_status,
            "matchMsg": match_msg,
            "matchSuggestion": match_suggestion,
        }
