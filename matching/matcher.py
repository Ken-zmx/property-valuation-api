"""小区名称模糊匹配引擎。

5 级匹配：
  1. 完全相等 → exact
  2. 包含关系 → exact
  3. 编辑距离相似度 ≥ 阈值 → fuzzy + "猜您想搜"
  4. 拼音匹配 (pypinyin) → fuzzy + "猜您想搜"
  5. 无匹配 → none + "未检索到该小区"
"""

from difflib import SequenceMatcher
from typing import Optional

try:
    from pypinyin import lazy_pinyin
    HAS_PINYIN = True
except ImportError:
    HAS_PINYIN = False


def _char_similarity(a: str, b: str) -> float:
    """字符级相似度，对中文短字符串效果较好。"""
    return SequenceMatcher(None, a, b).ratio()


def _levenshtein_ratio(s1: str, s2: str) -> float:
    """Levenshtein 距离归一化相似度。"""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(2)]
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        dp[i % 2][0] = i
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i % 2][j] = min(
                dp[(i - 1) % 2][j] + 1,
                dp[i % 2][j - 1] + 1,
                dp[(i - 1) % 2][j - 1] + cost,
            )
    return 1.0 - dp[m % 2][n] / max(m, n)


class CommunityMatcher:
    """小区名称匹配器。"""

    FUZZY_THRESHOLD = 0.65

    def __init__(self, communities_by_city: dict):
        """communities_by_city: {city: {district: [community_dict, ...]}}"""
        self.communities_by_city = communities_by_city

    def _flatten_communities(self, city: str, district: Optional[str] = None) -> list[dict]:
        """展开指定城市（+区域）下所有小区为扁平列表。"""
        city_data = self.communities_by_city.get(city, {})
        result = []
        if district and district in city_data:
            result.extend(city_data[district])
        elif not district:
            for dist_comms in city_data.values():
                result.extend(dist_comms)
        return result

    def match(self, keyword: str, city: str, district: Optional[str] = None) -> dict:
        """核心匹配方法。

        返回:
            {
                "status": "exact" | "fuzzy" | "none",
                "msg": str,
                "community": dict | None,
                "suggestion": str | None  (fuzzy 时填充)
            }
        """
        keyword = keyword.strip()
        if not keyword:
            return {"status": "none", "msg": "请输入小区名称", "community": None, "suggestion": None}

        communities = self._flatten_communities(city, district)
        if not communities:
            return {"status": "none", "msg": "该城市暂无小区数据", "community": None, "suggestion": None}

        names = [c["name"] for c in communities]

        # ── Level 1: 完全相等 ──
        for c in communities:
            if c["name"] == keyword:
                return {"status": "exact", "msg": "匹配成功", "community": c, "suggestion": None}

        # ── Level 2: 包含关系 ──
        for c in communities:
            if keyword in c["name"] or c["name"] in keyword:
                return {"status": "fuzzy", "msg": f"猜您想搜：{c['name']}", "community": c, "suggestion": c["name"]}

        # ── Level 3: Levenshtein 相似度 ──
        best_score = 0.0
        best_match = None
        for c in communities:
            score = _levenshtein_ratio(keyword, c["name"])
            if score > best_score:
                best_score = score
                best_match = c

        if best_score >= self.FUZZY_THRESHOLD and best_match:
            return {
                "status": "fuzzy",
                "msg": f"猜您想搜：{best_match['name']}",
                "community": best_match,
                "suggestion": best_match["name"],
            }

        # ── Level 4: 拼音匹配 ──
        if HAS_PINYIN:
            kw_pinyin = "".join(lazy_pinyin(keyword))
            kw_initials = "".join([p[0] if p else "" for p in lazy_pinyin(keyword)])
            for c in communities:
                name_pinyin = "".join(lazy_pinyin(c["name"]))
                name_initials = "".join([p[0] if p else "" for p in lazy_pinyin(c["name"])])
                if kw_pinyin == name_pinyin or kw_initials == name_initials:
                    return {
                        "status": "fuzzy",
                        "msg": f"猜您想搜：{c['name']}",
                        "community": c,
                        "suggestion": c["name"],
                    }

        # ── Level 5: 无匹配 ──
        return {"status": "none", "msg": "未检索到该小区", "community": None, "suggestion": None}


def match_community(keyword: str, city: str, district: Optional[str] = None) -> dict:
    """便捷函数：在全局 COMMUNITIES 数据中匹配。"""
    from data.communities import COMMUNITIES
    matcher = CommunityMatcher(COMMUNITIES)
    return matcher.match(keyword, city, district)
