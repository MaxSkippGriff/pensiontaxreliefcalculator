"""Pension Tax Relief Calculator — 2026/27 tax year constants and logic."""

from __future__ import annotations
import datetime
from dataclasses import dataclass
from typing import Literal


def active_tax_year() -> str:
    today = datetime.date.today()
    return "2026/27" if today >= datetime.date(2026, 4, 6) else "2025/26"


TAX_YEAR = "2026/27"

# Income tax thresholds 2026/27 (England, Wales, NI)
PERSONAL_ALLOWANCE = 12_570
BASIC_RATE_LIMIT = 50_270
HIGHER_RATE_LIMIT = 125_140
BASIC_RATE = 0.20
HIGHER_RATE = 0.40
ADDITIONAL_RATE = 0.45
BASIC_RATE_BAND = BASIC_RATE_LIMIT - PERSONAL_ALLOWANCE  # £37,700

# Scottish income tax 2026/27 — GROSS income upper thresholds (PA of £12,570 included)
# Taxable bands per user spec: starter £0–£3,967 / basic £3,968–£16,956 /
#   intermediate £16,957–£31,092 / higher £31,093–£62,430 / advanced £62,431–£125,140
# Source: https://www.gov.uk/government/publications/rates-and-allowances-income-tax
SCOTTISH_STARTER_UPPER = 16_537   # gross: 12,570 + 3,967 — 2026/27
SCOTTISH_BASIC_UPPER = 29_526     # gross: 12,570 + 16,956 — 2026/27
SCOTTISH_INTERMEDIATE_UPPER = 43_662  # gross: 12,570 + 31,092 — 2026/27
SCOTTISH_HIGHER_UPPER = 75_000    # gross: 12,570 + 62,430 — 2026/27
SCOTTISH_ADVANCED_UPPER = 125_140  # gross: PA=0 at this income — 2026/27
SCOTTISH_STARTER_RATE = 0.19
SCOTTISH_BASIC_RATE = 0.20
SCOTTISH_INTERMEDIATE_RATE = 0.21
SCOTTISH_HIGHER_RATE = 0.42
SCOTTISH_ADVANCED_RATE = 0.45
SCOTTISH_TOP_RATE = 0.48

# Pension limits
ANNUAL_ALLOWANCE = 60_000
MONEY_PURCHASE_ANNUAL_ALLOWANCE = 10_000

# Employer NI (2026/27) — for salary sacrifice NI saving calculation
EMPLOYER_NI_RATE = 0.15
EMPLOYER_NI_THRESHOLD = 5_000

# Employee NI (2026/27)
EMPLOYEE_NI_RATE_1 = 0.08   # On earnings £12,570–£50,270
EMPLOYEE_NI_RATE_2 = 0.02   # On earnings above £50,270
EMPLOYEE_NI_THRESHOLD = 12_570
EMPLOYEE_NI_UPPER = 50_270


@dataclass(frozen=True)
class PensionReliefResult:
    gross_contribution: float
    net_cost_basic_taxpayer: float
    net_cost_actual: float
    basic_rate_relief: float
    higher_rate_extra_relief: float
    additional_rate_extra_relief: float
    total_relief: float
    employer_ni_saving: float   # only for salary sacrifice
    employee_ni_saving: float   # only for salary sacrifice
    effective_cost: float
    marginal_rate: float
    contribution_method: str
    region: str


def _r(v: float) -> float:
    return round(float(v), 2)


def _marginal_rate_england(gross_income: float, contribution: float) -> float:
    """Return marginal income tax rate for England/Wales/NI."""
    taxable = max(0.0, gross_income - contribution - PERSONAL_ALLOWANCE)
    # PA tapers above £100k
    pa = PERSONAL_ALLOWANCE
    total_for_pa = gross_income
    if total_for_pa > 100_000:
        pa = max(0.0, PERSONAL_ALLOWANCE - (total_for_pa - 100_000) / 2.0)
    taxable = max(0.0, gross_income - contribution - pa)
    if taxable <= 0:
        return 0.0
    elif taxable <= BASIC_RATE_BAND:
        return BASIC_RATE
    elif gross_income - contribution <= HIGHER_RATE_LIMIT:
        return HIGHER_RATE
    else:
        return ADDITIONAL_RATE


def _marginal_rate_scotland(gross_income: float, contribution: float) -> float:
    """Return marginal income tax rate for Scotland (approximate)."""
    taxable = max(0.0, gross_income - contribution - PERSONAL_ALLOWANCE)
    if taxable <= 0:
        return 0.0
    elif gross_income - contribution <= SCOTTISH_STARTER_UPPER:
        return SCOTTISH_STARTER_RATE
    elif gross_income - contribution <= SCOTTISH_BASIC_UPPER:
        return SCOTTISH_BASIC_RATE
    elif gross_income - contribution <= SCOTTISH_INTERMEDIATE_UPPER:
        return SCOTTISH_INTERMEDIATE_RATE
    elif gross_income - contribution <= SCOTTISH_HIGHER_UPPER:
        return SCOTTISH_HIGHER_RATE
    elif gross_income - contribution <= SCOTTISH_ADVANCED_UPPER:
        return SCOTTISH_ADVANCED_RATE
    else:
        return SCOTTISH_TOP_RATE


def calculate_pension_relief(
    gross_income: float,
    contribution_amount: float,
    contribution_method: Literal["relief_at_source", "net_pay", "salary_sacrifice"] = "relief_at_source",
    region: Literal["england_wales_ni", "scotland"] = "england_wales_ni",
) -> PensionReliefResult:
    """
    Calculate pension tax relief for 2026/27.
    contribution_amount: the GROSS pension contribution amount (employer+employee total for salary sacrifice).
    For relief_at_source: you pay net, provider claims basic rate back. Gross = net / 0.80.
    For net_pay: deducted before tax, so full income tax relief is automatic.
    For salary_sacrifice: reduces gross salary, saves income tax AND employee/employer NI.
    """
    income = max(0.0, float(gross_income))
    contrib = max(0.0, float(contribution_amount))

    if region == "scotland":
        marginal_rate = _marginal_rate_scotland(income, contrib if contribution_method == "salary_sacrifice" else 0)
    else:
        marginal_rate = _marginal_rate_england(income, contrib if contribution_method == "salary_sacrifice" else 0)

    # Basic rate relief is always 20% of gross contribution
    basic_relief = _r(contrib * BASIC_RATE)

    # Higher/additional rate extra relief is the difference between marginal and basic
    extra_relief_rate = max(0.0, marginal_rate - BASIC_RATE)
    higher_relief = _r(contrib * extra_relief_rate)
    additional_relief = 0.0  # Additional rate: marginal already includes this

    total_relief = _r(basic_relief + higher_relief)

    # Net cost to user
    if contribution_method == "relief_at_source":
        # User pays net (80% of gross), provider claims 20% from HMRC
        net_cost = _r(contrib * (1 - BASIC_RATE))  # £800 for a £1,000 contribution
        # Higher-rate taxpayer claims extra via Self Assessment
        net_cost_actual = _r(contrib - total_relief)
    elif contribution_method == "net_pay":
        # Contribution deducted before tax — full income tax rate relief automatic
        net_cost = _r(contrib * (1 - marginal_rate))
        net_cost_actual = net_cost
    else:  # salary_sacrifice
        # Employer pays all pension; employee receives lower salary
        net_cost = _r(contrib * (1 - marginal_rate))
        net_cost_actual = net_cost

    # NI savings (salary sacrifice only)
    employer_ni_saving = 0.0
    employee_ni_saving = 0.0
    if contribution_method == "salary_sacrifice":
        # Employer NI saving
        employer_ni_saving = _r(contrib * EMPLOYER_NI_RATE)
        # Employee NI saving depends on earnings band
        if income > EMPLOYEE_NI_UPPER:
            eni_below = max(0.0, min(contrib, income - EMPLOYEE_NI_UPPER)) * EMPLOYEE_NI_RATE_2
            eni_above = max(0.0, contrib - max(0.0, income - EMPLOYEE_NI_UPPER)) * EMPLOYEE_NI_RATE_1
            employee_ni_saving = _r(eni_below + eni_above)
        elif income > EMPLOYEE_NI_THRESHOLD:
            employee_ni_saving = _r(min(contrib, income - EMPLOYEE_NI_THRESHOLD) * EMPLOYEE_NI_RATE_1)
        else:
            employee_ni_saving = 0.0

    effective_cost = _r(net_cost_actual - employee_ni_saving)

    return PensionReliefResult(
        gross_contribution=_r(contrib),
        net_cost_basic_taxpayer=_r(contrib * 0.80),
        net_cost_actual=_r(net_cost_actual),
        basic_rate_relief=basic_relief,
        higher_rate_extra_relief=higher_relief,
        additional_rate_extra_relief=additional_relief,
        total_relief=total_relief,
        employer_ni_saving=employer_ni_saving,
        employee_ni_saving=employee_ni_saving,
        effective_cost=effective_cost,
        marginal_rate=_r(marginal_rate * 100),
        contribution_method=contribution_method,
        region=region,
    )
