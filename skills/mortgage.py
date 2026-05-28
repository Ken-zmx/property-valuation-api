from skills.base import BaseSkill
from data.policies import POLICIES


class MortgageSkill(BaseSkill):
    name = "mortgage"
    description = "房贷月供（公积金+商贷组合）和税费计算"

    async def execute(self, params: dict) -> dict:
        city = params.get("city", "")
        price = params.get("totalPrice", 0)
        area = params.get("area", 100)
        house_count = params.get("houseCount", 0)
        years_owned = params.get("yearsOwned", 5)
        only_house = params.get("onlyHouse", True)
        loan_term = params.get("loanTerm", 30)

        dp = POLICIES["downPayment"].get(city, [0.20, 0.40])
        dp_ratio = dp[0] if house_count == 0 else min(len(dp) - 1, max(0, house_count))
        dp_ratio = dp[dp_ratio] if isinstance(dp_ratio, int) else dp_ratio
        # 简化：首套用 dp[0]，非首套用 dp[1]
        dp_ratio = dp[0] if house_count == 0 else dp[1]

        down_payment = price * dp_ratio
        loan_amount = price - down_payment

        rate_key = "first" if house_count == 0 else "second"
        loan_rate = POLICIES["loanRate"][rate_key]
        monthly_rate = loan_rate / 100 / 12
        months = loan_term * 12

        fund_max = POLICIES["fundMax"].get(city, 100) * 10000
        fund_amt = min(fund_max, loan_amount)
        fund_rate = POLICIES["fundRate"] / 100 / 12

        if fund_amt > 0 and fund_rate > 0:
            fund_monthly = fund_amt * fund_rate * (1 + fund_rate) ** months / ((1 + fund_rate) ** months - 1)
        else:
            fund_monthly = 0

        comm_amt = loan_amount - fund_amt
        if comm_amt > 0 and monthly_rate > 0:
            comm_monthly = comm_amt * monthly_rate * (1 + monthly_rate) ** months / ((1 + monthly_rate) ** months - 1)
        else:
            comm_monthly = 0

        total_monthly = fund_monthly + comm_monthly
        total_interest = (fund_monthly * months - fund_amt) + (comm_monthly * months - comm_amt)

        # 税费
        tax = POLICIES["tax"]
        if house_count == 0:
            deed_tax = price * (tax["deedFirst90below"] if area <= 90 else tax["deedFirst90above"])
        elif house_count == 1:
            deed_tax = price * tax["deedSecond"]
        else:
            deed_tax = price * tax["deedThird"]

        income_tax = 0 if (years_owned >= 5 and only_house) else price * tax["incomeTax"]
        vat = price / 1.05 * 0.05 if years_owned < 2 else 0
        agency_fee = price * tax["agencyFee"]
        total_tax = deed_tax + income_tax + vat + agency_fee

        return {
            "success": True,
            "downPaymentRatio": dp_ratio * 100,
            "downPayment": round(down_payment, 2),
            "loanAmount": round(loan_amount, 2),
            "loanRate": loan_rate,
            "loanTerm": loan_term,
            "mortgage": {
                "fundAmount": round(fund_amt, 2),
                "fundMonthly": round(fund_monthly, 2),
                "commercialAmount": round(comm_amt, 2),
                "commercialMonthly": round(comm_monthly, 2),
                "totalMonthly": round(total_monthly, 2),
                "totalInterest": round(total_interest, 2),
            },
            "taxes": {
                "deedTax": round(deed_tax, 2),
                "incomeTax": round(income_tax, 2),
                "vat": round(vat, 2),
                "agencyFee": round(agency_fee, 2),
                "total": round(total_tax, 2),
            },
            "totalUpfront": round(down_payment + total_tax, 2),
        }
