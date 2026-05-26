"""PensionTaxReliefCalculator.co.uk Flask application."""
from __future__ import annotations
import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, abort, make_response, redirect, render_template, request, send_from_directory
from flask_limiter import Limiter
from calculator import active_tax_year, TAX_YEAR, calculate_pension_relief, PERSONAL_ALLOWANCE, BASIC_RATE_LIMIT, ANNUAL_ALLOWANCE
from scraper_guard import init_guard

load_dotenv()

_PUBLIC_PATHS = (
    "/sitemap.xml", "/robots.txt", "/ads.txt", "/favicon.ico",
    "/favicon-16x16.png", "/favicon-32x32.png", "/apple-touch-icon.png",
    "/site.webmanifest", "/health",
)
_HONEYPOT_BLOCKED: set = set()

app = Flask(__name__)

CANONICAL_HOST = os.getenv("CANONICAL_HOST", "pensiontaxreliefcalculator.co.uk").replace("https://","").replace("http://","")
CANONICAL_HOST = CANONICAL_HOST[4:] if CANONICAL_HOST.startswith("www.") else CANONICAL_HOST
SITE_URL = f"https://{CANONICAL_HOST}"
GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "G-NPENPNP6YG").strip()
ADSENSE_CLIENT = os.getenv("ADSENSE_CLIENT", "ca-pub-3932111812673824").strip()

limiter = Limiter(
    app=app,
    key_func=lambda: (request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr or ""),
    default_limits=["300 per minute"],
    storage_uri="memory://",
    strategy="fixed-window",
)

init_guard(app, _PUBLIC_PATHS, "/trap", _HONEYPOT_BLOCKED)


@app.before_request
def enforce_canonical():
    host = (request.host or "").split(":")[0].lower()
    if host == f"www.{CANONICAL_HOST}":
        t = f"{SITE_URL}{request.full_path if request.query_string else request.path}"
        return redirect(t.rstrip("?"), code=301)
    return None


@app.after_request
def cache_headers(r):
    p = request.path or ""
    if p.startswith("/static/"):
        r.headers["Cache-Control"] = "public, max-age=300"
    elif p in ("/favicon.ico","/site.webmanifest","/apple-touch-icon.png","/favicon-32x32.png","/favicon-16x16.png"):
        r.headers["Cache-Control"] = "public, max-age=86400"
    elif p == "/robots.txt":
        r.headers["Cache-Control"] = "public, max-age=60"
    elif r.mimetype == "text/html":
        r.headers["Cache-Control"] = "private, no-store, max-age=0, must-revalidate"
    r.headers.setdefault("X-Content-Type-Options","nosniff")
    r.headers.setdefault("X-Frame-Options","SAMEORIGIN")
    r.headers.setdefault("Referrer-Policy","strict-origin-when-cross-origin")
    r.headers.setdefault("Permissions-Policy","camera=(), microphone=(), geolocation=()")
    return r


def _ctx(**kw):
    return dict(site_url=SITE_URL, tax_year=active_tax_year(), now=datetime.utcnow(),
                ga_measurement_id=GA_MEASUREMENT_ID, adsense_client=ADSENSE_CLIENT, **kw)


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, "favicon.ico", mimetype="image/vnd.microsoft.icon")

@app.route("/favicon-32x32.png")
def favicon_32():
    return send_from_directory(app.static_folder, "favicon-32x32.png", mimetype="image/png")

@app.route("/favicon-16x16.png")
def favicon_16():
    return send_from_directory(app.static_folder, "favicon-16x16.png", mimetype="image/png")

@app.route("/apple-touch-icon.png")
def apple_touch_icon():
    return send_from_directory(app.static_folder, "apple-touch-icon.png", mimetype="image/png")

@app.route("/site.webmanifest")
def webmanifest():
    return send_from_directory(app.static_folder, "site.webmanifest", mimetype="application/manifest+json")

@app.route("/trap")
def trap():
    xff = request.headers.get("X-Forwarded-For", "")
    _HONEYPOT_BLOCKED.add(xff.split(",")[0].strip() if xff else (request.remote_addr or ""))
    abort(403)

@app.route("/health")
def health():
    return {"status": "ok"}, 200

@app.route("/robots.txt")
def robots():
    body = "\n".join([
        "User-agent: *",
        "Allow: /",
        "Disallow: /trap",
        "Disallow: /api/",
        "Disallow: /admin/",
        "",
        f"Sitemap: {SITE_URL}/sitemap.xml",
    ])
    r = make_response(body)
    r.content_type = "text/plain"
    return r


@app.route("/ads.txt")
def ads_txt():
    pub_id = ADSENSE_CLIENT.replace("ca-pub-", "").strip()
    body = f"google.com, pub-{pub_id}, DIRECT, f08c47fec0942fa0\n" if pub_id else ""
    resp = make_response(body)
    resp.mimetype = "text/plain"
    return resp


@app.route("/sitemap.xml")
def sitemap():
    now = datetime.utcnow().strftime("%Y-%m-%d")
    entries = [
        (f"{SITE_URL}/","1.0","weekly"),
        (f"{SITE_URL}/calculator","0.9","weekly"),
        (f"{SITE_URL}/methodology","0.7","monthly"),
        (f"{SITE_URL}/about","0.5","monthly"),
        (f"{SITE_URL}/privacy","0.3","yearly"),
        (f"{SITE_URL}/contact","0.3","yearly"),
        (f"{SITE_URL}/disclaimer","0.3","yearly"),
        (f"{SITE_URL}/claim-higher-rate-pension-tax-relief","0.6","monthly"),
        (f"{SITE_URL}/pension-tax-relief-self-assessment","0.6","monthly"),
        (f"{SITE_URL}/net-pay-arrangement-low-earners","0.6","monthly"),
        (f"{SITE_URL}/pension-contribution-net-cost","0.6","monthly"),
        (f"{SITE_URL}/pension-relief-over-100k","0.6","monthly"),
        (f"{SITE_URL}/pension-carry-forward","0.6","monthly"),
        (f"{SITE_URL}/tapered-annual-allowance","0.6","monthly"),
        (f"{SITE_URL}/money-purchase-annual-allowance","0.6","monthly"),
        (f"{SITE_URL}/pension-gross-vs-net-contributions","0.6","monthly"),
        (f"{SITE_URL}/pension-tax-relief-self-employed","0.6","monthly"),
        (f"{SITE_URL}/guides","0.6","monthly"),
        (f"{SITE_URL}/calculators","0.6","monthly"),
        (f"{SITE_URL}/higher-rate-pension-relief-calculator","0.7","monthly"),
        (f"{SITE_URL}/relief-at-source-calculator","0.7","monthly"),
        (f"{SITE_URL}/salary-sacrifice-pension-calculator","0.7","monthly"),
        (f"{SITE_URL}/annual-allowance-checker","0.7","monthly"),
        (f"{SITE_URL}/blog","0.6","weekly"),
    ] + [(f"{SITE_URL}/blog/{p['slug']}","0.6","monthly") for p in BLOG_POSTS] \
      + [(f"{SITE_URL}/pension-relief/{inc}","0.5","monthly") for inc in PENSION_INCOME_AMOUNTS]
    r = make_response(render_template("sitemap.xml", url_entries=entries, now=now))
    r.content_type = "application/xml"
    return r

@app.route("/")
def landing():
    calc = calculate_pension_relief(gross_income=60000, contribution_amount=5000, contribution_method="relief_at_source", region="england_wales_ni")
    faq = [
        {"q":"What is pension tax relief?","a":"Pension tax relief is a government incentive that reduces the cost of saving into a pension. For every £80 a basic-rate taxpayer pays into a pension, the government adds £20, making the gross contribution £100. Higher-rate taxpayers can claim an additional 20% back through Self Assessment, and additional-rate taxpayers an extra 25%."},
        {"q":"What is relief at source?","a":"Relief at source is the most common method for personal pensions and SIPPs. You pay the net amount (80% of the gross contribution) and your provider automatically claims basic-rate relief (20%) from HMRC. If you are a higher or additional-rate taxpayer, you claim the extra relief via your Self Assessment tax return."},
        {"q":"What is a net pay arrangement?","a":"Net pay arrangements are used by many workplace pension schemes. Your contribution is deducted from your salary before income tax is calculated, so you receive full tax relief automatically at your marginal rate without needing to make a Self Assessment claim. This means basic-rate taxpayers in net pay schemes pay the same amount as higher-rate taxpayers in percentage terms."},
        {"q":"How does salary sacrifice differ from pension tax relief?","a":"Salary sacrifice is not technically pension tax relief — it is a contractual arrangement where you give up part of your salary in exchange for employer pension contributions. Because your salary is reduced, you pay less income tax and National Insurance on the sacrificed amount. The employer also saves employer NI, and some pass this saving on to your pension."},
        {"q":"What is the annual allowance?","a":"The annual allowance for 2026/27 is £60,000 — the maximum you can contribute to pensions each year while still receiving tax relief. This covers all contributions including those from your employer. If you have already flexibly accessed your pension, the Money Purchase Annual Allowance of £10,000 may apply instead."},
        {"q":"Do Scottish taxpayers get different pension relief?","a":"Yes. Scottish taxpayers pay different income tax rates from the rest of the UK — there are six bands ranging from 19% (starter rate) up to 48% (top rate). For relief at source, providers still claim 20% basic rate relief from HMRC regardless of Scottish rates. Scottish taxpayers who pay higher rates must claim the additional relief through Self Assessment. The calculator handles Scottish rates."},
    ]
    return render_template("landing.html", **_ctx(
        title="Pension Tax Relief Calculator UK 2026/27 | Estimate Your Net Contribution Cost",
        meta_description="Use the pension tax relief calculator for 2026/27 to estimate relief at source, net pay or salary sacrifice treatment and your true contribution cost.",
        canonical_url=SITE_URL+"/",
        calc=calc,
        faq_items=faq,
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"}],
    ))

@app.route("/calculator")
def calculator_page():
    return render_template("calculator.html", **_ctx(
        title="Pension Tax Relief Calculator 2026/27 | UK Pension Relief Breakdown",
        meta_description="Free UK pension tax relief calculator for 2026/27. Enter income and contribution to get a full breakdown of relief at source, net pay and salary sacrifice.",
        canonical_url=SITE_URL+"/calculator",
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":"Calculator","url":SITE_URL+"/calculator"}],
    ))

@app.route("/methodology")
def methodology():
    return render_template("methodology.html", **_ctx(
        title="Methodology — How We Calculate UK Pension Tax Relief 2026/27",
        meta_description="How PensionTaxReliefCalculator.co.uk calculates pension relief: 2026/27 rates, relief at source, net pay, salary sacrifice, Scottish rates and annual allowance.",
        canonical_url=SITE_URL+"/methodology",
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":"Methodology","url":SITE_URL+"/methodology"}],
    ))

@app.route("/about")
def about():
    return render_template("about.html", **_ctx(
        title="About Pension Tax Relief Calculator — Free UK Pension Relief Tool",
        meta_description="About PensionTaxReliefCalculator.co.uk — a free, independent tool to estimate pension tax relief on UK pension contributions for 2026/27.",
        canonical_url=SITE_URL+"/about",
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":"About","url":SITE_URL+"/about"}],
    ))

@app.route("/privacy")
def privacy():
    return render_template("privacy.html", **_ctx(
        title="Privacy Policy — PensionTaxReliefCalculator.co.uk",
        meta_description="Privacy policy for PensionTaxReliefCalculator.co.uk. We don't store your financial data.",
        canonical_url=SITE_URL+"/privacy",
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":"Privacy","url":SITE_URL+"/privacy"}],
    ))

@app.route("/contact")
def contact():
    return render_template("contact.html", **_ctx(
        title="Contact — PensionTaxReliefCalculator.co.uk",
        meta_description="Get in touch with PensionTaxReliefCalculator.co.uk.",
        canonical_url=SITE_URL+"/contact",
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":"Contact","url":SITE_URL+"/contact"}],
    ))

@app.route("/disclaimer")
def disclaimer():
    return render_template("disclaimer.html", **_ctx(
        title="Disclaimer — PensionTaxReliefCalculator.co.uk",
        meta_description="Disclaimer for PensionTaxReliefCalculator.co.uk. Results are estimates only.",
        canonical_url=SITE_URL+"/disclaimer",
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":"Disclaimer","url":SITE_URL+"/disclaimer"}],
    ))

@app.route("/claim-higher-rate-pension-tax-relief")
def guide_higher_rate_relief():
    return render_template("claim-higher-rate-pension-tax-relief.html", **_ctx(
        title="How to Claim Higher Rate Pension Tax Relief 2026/27",
        meta_description="Learn when higher-rate pension tax relief may need to be claimed and how relief at source, net pay and Self Assessment differ.",
        canonical_url=SITE_URL+"/claim-higher-rate-pension-tax-relief",
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":"Claim Higher Rate Relief","url":SITE_URL+"/claim-higher-rate-pension-tax-relief"}],
    ))

@app.route("/pension-tax-relief-self-assessment")
def guide_self_assessment():
    return render_template("pension-tax-relief-self-assessment.html", **_ctx(
        title="Pension Tax Relief and Self Assessment 2026/27",
        meta_description="Understand how pension contributions can affect Self Assessment, higher-rate relief claims and adjusted net income.",
        canonical_url=SITE_URL+"/pension-tax-relief-self-assessment",
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":"Pension Relief and Self Assessment","url":SITE_URL+"/pension-tax-relief-self-assessment"}],
    ))

@app.route("/net-pay-arrangement-low-earners")
def guide_net_pay_low_earners():
    return render_template("net-pay-arrangement-low-earners.html", **_ctx(
        title="Net Pay Pension Arrangements and Low Earners | UK Guide",
        meta_description="Understand why net pay pension arrangements can affect low earners differently and how tax relief can depend on scheme type.",
        canonical_url=SITE_URL+"/net-pay-arrangement-low-earners",
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":"Net Pay and Low Earners","url":SITE_URL+"/net-pay-arrangement-low-earners"}],
    ))

@app.route("/pension-contribution-net-cost")
def guide_net_cost():
    return render_template("pension-contribution-net-cost.html", **_ctx(
        title="Pension Contribution Net Cost Calculator Guide 2026/27",
        meta_description="Learn how to estimate the real net cost of pension contributions after tax relief for different contribution methods.",
        canonical_url=SITE_URL+"/pension-contribution-net-cost",
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":"Pension Contribution Net Cost","url":SITE_URL+"/pension-contribution-net-cost"}],
    ))

@app.route("/pension-relief-over-100k")
def guide_over_100k():
    return render_template("pension-relief-over-100k.html", **_ctx(
        title="Pension Tax Relief Over £100k Income 2026/27",
        meta_description="Learn how pension contributions can interact with the Personal Allowance taper for people earning over £100,000.",
        canonical_url=SITE_URL+"/pension-relief-over-100k",
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":"Pension Relief Over £100k","url":SITE_URL+"/pension-relief-over-100k"}],
    ))

@app.route("/pension-carry-forward")
def guide_carry_forward():
    return render_template("pension-carry-forward.html", **_ctx(
        title="Pension Carry Forward 2026/27 — Contribute More Than the Annual Allowance",
        meta_description="Learn how pension carry forward lets you use unused annual allowance from the previous 3 tax years to make larger pension contributions in 2026/27.",
        canonical_url=SITE_URL+"/pension-carry-forward",
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":"Pension Carry Forward","url":SITE_URL+"/pension-carry-forward"}],
    ))

@app.route("/tapered-annual-allowance")
def guide_tapered_allowance():
    return render_template("tapered-annual-allowance.html", **_ctx(
        title="Tapered Annual Allowance 2026/27 — High Earner Pension Limit",
        meta_description="Understand the tapered annual allowance for 2026/27. How adjusted income and threshold income affect the pension annual allowance for high earners.",
        canonical_url=SITE_URL+"/tapered-annual-allowance",
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":"Tapered Annual Allowance","url":SITE_URL+"/tapered-annual-allowance"}],
    ))

@app.route("/money-purchase-annual-allowance")
def guide_mpaa():
    return render_template("money-purchase-annual-allowance.html", **_ctx(
        title="Money Purchase Annual Allowance (MPAA) 2026/27",
        meta_description="What is the MPAA? The £10,000 money purchase annual allowance applies once you flexibly access a pension. Learn what triggers it and what does not.",
        canonical_url=SITE_URL+"/money-purchase-annual-allowance",
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":"Money Purchase Annual Allowance","url":SITE_URL+"/money-purchase-annual-allowance"}],
    ))

@app.route("/pension-gross-vs-net-contributions")
def guide_gross_vs_net():
    return render_template("pension-gross-vs-net-contributions.html", **_ctx(
        title="Gross vs Net Pension Contributions Explained 2026/27",
        meta_description="What is the difference between gross and net pension contributions? How relief at source and net pay arrangements work — and what Scottish taxpayers need to know.",
        canonical_url=SITE_URL+"/pension-gross-vs-net-contributions",
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":"Gross vs Net Contributions","url":SITE_URL+"/pension-gross-vs-net-contributions"}],
    ))

@app.route("/pension-tax-relief-self-employed")
def guide_self_employed():
    return render_template("pension-tax-relief-self-employed.html", **_ctx(
        title="Pension Tax Relief for the Self-Employed 2026/27",
        meta_description="How self-employed people and limited company directors claim pension tax relief in 2026/27 — SIPP contributions, annual allowance limits and Self Assessment.",
        canonical_url=SITE_URL+"/pension-tax-relief-self-employed",
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":"Pension Relief for the Self-Employed","url":SITE_URL+"/pension-tax-relief-self-employed"}],
    ))

@app.route("/guides")
def guides_index():
    return render_template("guides.html", **_ctx(
        title="Pension Tax Relief Guides 2026/27 | PensionTaxReliefCalculator.co.uk",
        meta_description="In-depth guides to UK pension tax relief, annual allowance, carry forward and contribution strategies.",
        canonical_url=SITE_URL + "/guides",
    ))

@app.route("/calculators")
def calculators_index():
    return render_template("calculators.html", **_ctx(
        title="Pension Tax Relief Calculators 2026/27 | PensionTaxReliefCalculator.co.uk",
        meta_description="Free UK pension tax relief calculators for higher-rate taxpayers, salary sacrifice and annual allowance.",
        canonical_url=SITE_URL + "/calculators",
    ))

@app.route("/higher-rate-pension-relief-calculator")
def higher_rate_pension_relief_calculator():
    return render_template("higher-rate-pension-relief-calculator.html", **_ctx(
        title="Higher Rate Pension Relief Calculator 2026/27 | PensionTaxReliefCalculator.co.uk",
        meta_description="Estimate the extra pension tax relief available to higher and additional rate taxpayers in 2026/27.",
        canonical_url=SITE_URL + "/higher-rate-pension-relief-calculator",
    ))

@app.route("/relief-at-source-calculator")
def relief_at_source_calculator():
    return render_template("relief-at-source-calculator.html", **_ctx(
        title="Relief at Source Pension Calculator 2026/27 | PensionTaxReliefCalculator.co.uk",
        meta_description="See your provider's 20% top-up and calculate any extra relief to claim via Self Assessment.",
        canonical_url=SITE_URL + "/relief-at-source-calculator",
    ))

@app.route("/salary-sacrifice-pension-calculator")
def salary_sacrifice_pension_calculator():
    return render_template("salary-sacrifice-pension-calculator.html", **_ctx(
        title="Salary Sacrifice Pension Calculator 2026/27 | PensionTaxReliefCalculator.co.uk",
        meta_description="Estimate income tax and NI savings from a pension salary sacrifice arrangement in 2026/27.",
        canonical_url=SITE_URL + "/salary-sacrifice-pension-calculator",
    ))

@app.route("/annual-allowance-checker")
def annual_allowance_checker():
    return render_template("annual-allowance-checker.html", **_ctx(
        title="Pension Annual Allowance Checker 2026/27 | PensionTaxReliefCalculator.co.uk",
        meta_description="Check whether your pension contributions are within the £60,000 annual allowance for 2026/27.",
        canonical_url=SITE_URL + "/annual-allowance-checker",
    ))

PENSION_INCOME_AMOUNTS = [20000, 25000, 30000, 35000, 40000, 45000, 50000, 60000, 75000, 80000, 100000, 120000, 125000, 150000]

@app.route("/pension-relief/<int:income>")
def pension_relief_page(income: int):
    if income not in PENSION_INCOME_AMOUNTS:
        abort(404)
    # Calculate with 5% contribution (common scenario), relief at source
    contribution = round(income * 0.05 / 100) * 100  # round to nearest £100
    contribution = max(1000, min(contribution, 10000))  # cap between £1k and £10k
    calc_ras = calculate_pension_relief(gross_income=income, contribution_amount=contribution, contribution_method="relief_at_source", region="england_wales_ni")
    calc_ss = calculate_pension_relief(gross_income=income, contribution_amount=contribution, contribution_method="salary_sacrifice", region="england_wales_ni")
    return render_template("pension_relief_page.html", **_ctx(
        title=f"Pension Tax Relief on £{income:,} Income 2026/27 | Calculator",
        meta_description=f"How much pension tax relief on a £{income:,} gross income in 2026/27? With a £{contribution:,} contribution under relief at source, tax relief is £{calc_ras.total_relief:,.0f}. Salary sacrifice saves £{calc_ss.employee_ni_saving + calc_ss.net_cost_actual:.0f} less.",
        canonical_url=SITE_URL+f"/pension-relief/{income}",
        income=income,
        contribution=contribution,
        calc_ras=calc_ras,
        calc_ss=calc_ss,
        all_incomes=PENSION_INCOME_AMOUNTS,
        breadcrumbs=[{"name":"Home","url":SITE_URL+"/"},{"name":f"Pension relief at £{income:,}","url":SITE_URL+f"/pension-relief/{income}"}],
    ))


BLOG_POSTS = [
    {
        "slug": "pension-annual-allowance-2026",
        "title": "Pension Annual Allowance 2026/27 — £60,000 Limit Explained",
        "description": "How the £60,000 pension annual allowance works, what counts towards it, the money purchase annual allowance, tapering for high earners and how employer contributions interact.",
        "date": "26 May 2026",
        "date_iso": "2026-05-26",
        "reading_time": "7 min read",
        "sections": [
            {
                "heading": "What the Annual Allowance Is",
                "paragraphs": [
                    "The pension annual allowance for 2026/27 is £60,000. This is the maximum total pension input — across all your registered pension schemes combined — in a single tax year for which you can receive tax relief. The allowance was increased from £40,000 to £60,000 in April 2023 and has remained at £60,000 since. It covers employee contributions, employer contributions and DB accrual all added together.",
                    "There is a secondary constraint: you cannot contribute more than 100% of your relevant UK earnings (salary, trading income) in the year, even if your unused allowance would otherwise permit it. If you earn £35,000, the effective cap is £35,000 — not £60,000. This earnings cap applies to personal contributions only; employer contributions are not limited by the earnings cap, though they still count towards the £60,000 overall limit. If you exceed the annual allowance, the excess is added to your taxable income for the year, generating an annual allowance charge at your marginal rate. You can ask your scheme to pay the charge directly from your pension pot if the excess exceeds £2,000 — this is called 'scheme pays'.",
                ],
            },
            {
                "heading": "Money Purchase Annual Allowance (MPAA)",
                "paragraphs": [
                    "Once you flexibly access a defined contribution (money purchase) pension, the MPAA replaces the standard £60,000 allowance for future DC contributions. The MPAA is £10,000 — dramatically lower. Flexible access means taking income via flexi-access drawdown, receiving an uncrystallised funds pension lump sum (UFPLS), or purchasing a flexible annuity that includes an income guarantee with a cashback option.",
                    "Taking a tax-free lump sum (pension commencement lump sum) without entering drawdown does not trigger the MPAA. Nor does taking a small pot under £10,000, or commencing a lifetime annuity with no income flexibility. Once triggered, the MPAA cannot be reversed — it applies for the rest of your life. This makes the timing of accessing a pension pot critically important for anyone still working and wishing to continue making large pension contributions. The MPAA does not affect defined benefit accrual — only DC contributions.",
                ],
            },
            {
                "heading": "Tapering for High Earners",
                "paragraphs": [
                    "For high earners, the standard £60,000 allowance is tapered downwards. The taper applies when two conditions are both met: threshold income exceeds £200,000 AND adjusted income exceeds £260,000. Threshold income is broadly your taxable income excluding employer pension contributions. Adjusted income is threshold income plus employer pension contributions.",
                    "Where both conditions are met, the allowance reduces by £1 for every £2 of adjusted income above £260,000. The minimum tapered allowance is £10,000, reached at adjusted income of £360,000. An individual with adjusted income of £280,000 faces a reduced allowance of £60,000 − (£280,000 − £260,000) / 2 = £60,000 − £10,000 = £50,000. Carry forward from earlier years can be used against the tapered allowance, but it is particularly complex to calculate — professional advice is worthwhile for anyone near the taper thresholds.",
                ],
            },
            {
                "heading": "How Employer Contributions Interact",
                "paragraphs": [
                    "Employer pension contributions count fully towards the annual allowance. If your employer contributes £15,000 and you contribute £10,000 in the same year, your total pension input is £25,000 — well within the £60,000 limit. But if your employer makes a very large contribution — for example a one-off employer contribution to a SIPP of £50,000 — and you also contribute £15,000 personally, the total is £65,000, exceeding the allowance by £5,000 and triggering a charge.",
                    "For salary sacrifice arrangements, the sacrifice converts employee contributions into employer contributions — the employer makes the pension payment instead of the employee. This has no adverse effect on the annual allowance calculation: salary sacrifice employer contributions count the same as any other employer contribution. What salary sacrifice does do is reduce the employee's pensionable pay, which can affect certain defined benefit scheme calculations — an important point to check with your scheme if you participate in a DB arrangement.",
                ],
            },
        ],
        "faqs": [
            {"q": "What is the pension annual allowance for 2026/27?", "a": "£60,000, or 100% of your relevant UK earnings if lower. Exceeding this triggers an annual allowance charge at your marginal tax rate."},
            {"q": "What triggers the money purchase annual allowance?", "a": "Flexibly accessing a defined contribution pension — by entering flexi-access drawdown, taking a UFPLS, or certain flexible annuity purchases. The MPAA is £10,000 and cannot be reversed."},
            {"q": "Does the annual allowance include my employer's contributions?", "a": "Yes. Total pension inputs include employee contributions, employer contributions and defined benefit accrual. All count against the £60,000 limit."},
        ],
        "sources": [
            {"label": "HMRC: Pension annual allowance", "url": "https://www.gov.uk/pension-annual-allowance"},
            {"label": "HMRC: Money Purchase Annual Allowance", "url": "https://www.gov.uk/money-purchase-annual-allowance"},
        ],
    },
    {
        "slug": "carry-forward-pension-allowance",
        "title": "Carry Forward Pension Allowance — Three-Year Rule",
        "description": "Carry forward lets you use unused annual allowance from the previous three tax years to make larger pension contributions. Most valuable in bonus years, business sale years and for self-employed income spikes.",
        "date": "26 May 2026",
        "date_iso": "2026-05-26",
        "reading_time": "6 min read",
        "sections": [
            {
                "heading": "How Carry Forward Works",
                "paragraphs": [
                    "Carry forward allows you to use unused pension annual allowance from the three previous tax years when your contributions in the current year exceed the standard £60,000. To use carry forward: first, use the current year's full £60,000 allowance; then apply unused allowance from the earliest of the three prior years (2023/24), then 2024/25, then 2025/26. The unused allowance from each year is that year's annual allowance minus the total pension inputs in that year.",
                    "There are two essential conditions. First, you must have been a member of a registered UK pension scheme in each year whose allowance you wish to use — not necessarily making contributions, just enrolled. A basic workplace pension auto-enrolment counts. Second, your total contributions in the carry-forward year are still limited to 100% of your relevant UK earnings in that year. So if you earn £80,000, you cannot contribute more than £80,000 even if you have £180,000 of carry-forward available, unless the excess comes from employer contributions (which are not earnings-capped).",
                ],
            },
            {
                "heading": "Calculating Your Available Carry Forward",
                "paragraphs": [
                    "The annual allowance was £40,000 for 2022/23 and earlier years, then £60,000 from 2023/24 onwards. For carry forward in 2026/27, the three relevant prior years are 2023/24 (£60,000), 2024/25 (£60,000) and 2025/26 (£60,000). Available carry forward from each year = allowance for that year minus total pension inputs in that year (minimum zero).",
                    "Worked example: in 2023/24 you contributed £8,000 total (you and your employer); in 2024/25 £10,000; in 2025/26 £12,000. Available carry forward = (£60,000 − £8,000) + (£60,000 − £10,000) + (£60,000 − £12,000) = £52,000 + £50,000 + £48,000 = £150,000. Adding the current year's £60,000, you can contribute up to £210,000 in 2026/27 — subject to earning at least £60,000 in 2026/27 for the personal element, with employer contributions making up any difference.",
                ],
            },
            {
                "heading": "When Carry Forward Is Most Valuable",
                "paragraphs": [
                    "The highest-value applications are where a large income event occurs in a single year. An employee receiving a £100,000 bonus, a business owner taking significant dividends or salary in a profitable year, or a professional selling a business — all might have accumulated three years of minimal pension inputs combined with substantial carry-forward allowance. The tax saving from contributing a large sum in that year (at 40% or 45% income tax) is very substantial.",
                    "For self-employed or company-director individuals, carry forward enables front-loading pension contributions in good income years without breaching the annual allowance. A sole director who has had three quiet years with minimal company pension contributions might have £150,000+ of carry-forward available, all of which can be deployed in a single profitable year as employer pension contributions — reducing corporation tax and personal income simultaneously.",
                ],
            },
            {
                "heading": "The Constraints",
                "paragraphs": [
                    "Carry forward does not help if your earnings in the current year are low. If you have zero or minimal relevant UK earnings, the 100% earnings cap prevents personal contributions above that level — carry-forward allowance cannot override this. An individual on career break earning nothing cannot make a personal pension contribution above £3,600 (the minimum HMRC permits without earnings) even with substantial carry-forward available.",
                    "Carry forward is also unavailable for the money purchase annual allowance (MPAA). If you have triggered the MPAA by flexibly accessing a pension, your DC contribution limit is fixed at £10,000 per year with no carry-forward ability. If there is any possibility you will want to make large DC contributions in future, think carefully before taking flexible income from a pension pot.",
                ],
            },
        ],
        "faqs": [
            {"q": "How many years of pension allowance can I carry forward?", "a": "Three years. You can carry forward unused allowance from the three previous tax years only. Earlier years are lost permanently."},
            {"q": "Do I need to have contributed to a pension to carry forward?", "a": "No, but you must have been a member of a registered pension scheme in each year whose unused allowance you wish to use. Auto-enrolment membership counts even with zero contributions."},
            {"q": "Does carry forward work with the MPAA?", "a": "No. If you have triggered the money purchase annual allowance, carry forward cannot increase your DC contribution limit above £10,000."},
        ],
        "sources": [
            {"label": "HMRC: Carry forward of unused annual allowance", "url": "https://www.gov.uk/hmrc-internal-manuals/pensions-tax-manual/ptm055400"},
            {"label": "HMRC: Annual allowance for pension savings", "url": "https://www.gov.uk/pension-annual-allowance"},
        ],
    },
    {
        "slug": "pension-relief-above-100k",
        "title": "Pension Tax Relief Over £100,000 — Restore Your Personal Allowance",
        "description": "Income between £100,000 and £125,140 attracts an effective 60% marginal tax rate. Pension contributions reduce adjusted net income, restoring the personal allowance and generating exceptional tax savings.",
        "date": "26 May 2026",
        "date_iso": "2026-05-26",
        "reading_time": "7 min read",
        "sections": [
            {
                "heading": "The £100k Trap",
                "paragraphs": [
                    "The personal allowance (£12,570 for 2026/27) is gradually withdrawn for individuals whose adjusted net income (ANI) exceeds £100,000. The allowance reduces by £1 for every £2 of ANI above £100,000. It reaches zero at £125,140. While the allowance is being withdrawn, every £2 of additional income triggers £1 of lost personal allowance, meaning that £2 of income is taxed twice — once normally and once because the allowance reduction exposes previously exempt income to tax at 40%. The effective marginal tax rate in the £100,000–£125,140 band is therefore 60%, not 40%.",
                    "This is sometimes called the '60% trap' or the '£100k tax trap'. An employee earning exactly £100,000 who receives a £1,000 pay rise pays 40% income tax on the £1,000 (£400) plus an effective additional 20% on the lost allowance (£500 of previously allowance-sheltered income becomes taxable at 40% = £200). Total extra tax: £600 on a £1,000 income increase — a 60% effective rate.",
                ],
            },
            {
                "heading": "How Pension Contributions Reduce Adjusted Net Income",
                "paragraphs": [
                    "Pension contributions — whether under relief at source, net pay arrangement, or salary sacrifice — reduce adjusted net income. Under relief at source, the gross contribution reduces ANI directly. Under salary sacrifice, the sacrificed salary never enters ANI in the first place. Either way, a £10,000 pension contribution for someone with £110,000 ANI reduces ANI to £100,000, restoring the full personal allowance.",
                    "The ANI reduction is the key mechanism. HMRC uses ANI to calculate the personal allowance, the High Income Child Benefit Charge, and 30-hour free childcare eligibility. Pension contributions are one of the few reliefs that reduce ANI — gift aid donations are another. Other expenses and deductions do not reduce ANI in the same way.",
                ],
            },
            {
                "heading": "Worked Example: £115,000 Income, £15,000 Pension Contribution",
                "paragraphs": [
                    "Consider someone with £115,000 salary and no pension contributions. Their ANI is £115,000. Personal allowance tapered to: £12,570 − (£115,000 − £100,000) / 2 = £12,570 − £7,500 = £5,070. Taxable income: £115,000 − £5,070 = £109,930. Income tax at 40% on the portion above the basic-rate band (£50,270): 40% × (£109,930 − £37,700) = 40% × £72,230 = £28,892 (plus basic-rate tax on the £37,700).",
                    "Now add a £15,000 gross pension contribution (relief at source). ANI drops to £100,000. Personal allowance restored to full £12,570 — saving 40% × (£12,570 − £5,070) = 40% × £7,500 = £3,000. Additionally, the £15,000 that falls within the 40% band saves 40% × £15,000 = £6,000 in income tax directly. Part of this falls within the PA-withdrawal zone (the 60% effective rate zone), so the actual saving is greater. Total income tax saving from the £15,000 contribution: approximately £9,000. Net cost of a £15,000 pension contribution: approximately £6,000. That is a 60% effective subsidy from the tax system.",
                ],
            },
            {
                "heading": "The Annual Allowance Cap",
                "paragraphs": [
                    "You cannot make unlimited pension contributions to escape the £100k trap. The pension annual allowance of £60,000 (or 100% of earnings if lower) applies. For someone with persistent income between £100,000 and £125,140, the maximum annual contribution in the current year is £60,000. Carry-forward allowance from prior years can increase this if unused allowance is available — potentially allowing a one-off very large contribution in a year when income is particularly high.",
                    "For regular earners consistently in the £100,000–£125,140 range, the strategy is straightforward: contribute enough to pension each year to bring ANI to exactly £100,000, restoring the full personal allowance. This is often a contribution of between £5,000 and £25,140 depending on exact income. Any contribution above that amount still saves at the standard 40% rate on the excess, which is still highly efficient.",
                ],
            },
        ],
        "faqs": [
            {"q": "What is the effective tax rate on income between £100,000 and £125,140?", "a": "60%. Each extra £2 of income triggers 40p income tax on that £2, plus 40p tax on the £1 of personal allowance lost — a combined 60p on every £2, or 60% effective marginal rate."},
            {"q": "How much pension contribution do I need to restore my personal allowance?", "a": "Enough to bring your adjusted net income (ANI) to £100,000. If your income is £110,000, you need a £10,000 pension contribution. If it is £115,000, you need £15,000. The contribution can be salary sacrifice, relief at source or net pay."},
            {"q": "Does the annual allowance limit how much I can contribute?", "a": "Yes. The maximum is £60,000 (or 100% of earnings) per year, plus any carry-forward from the previous three years. You cannot make unlimited contributions even to avoid the personal allowance taper."},
        ],
        "sources": [
            {"label": "HMRC: Adjusted net income", "url": "https://www.gov.uk/guidance/adjusted-net-income"},
            {"label": "HMRC: Personal Allowance tapering", "url": "https://www.gov.uk/income-tax-rates/income-over-100000"},
        ],
    },
    {
        "slug": "sipp-tax-relief-explained",
        "title": "SIPP Tax Relief Explained — Self-Invested Personal Pensions",
        "description": "How relief at source works in a SIPP, how higher-rate taxpayers claim additional relief via Self Assessment, key differences from workplace pensions, and how drawdown is taxed.",
        "date": "26 May 2026",
        "date_iso": "2026-05-26",
        "reading_time": "7 min read",
        "sections": [
            {
                "heading": "How Relief at Source Works in a SIPP",
                "paragraphs": [
                    "All SIPPs operate under the relief at source (RaS) method. When you contribute to your SIPP, you pay 80% of the gross amount — the provider automatically claims 20% basic-rate tax relief from HMRC and adds it to your pension pot. So if you pay £800, your SIPP receives £1,000. The provider handles this claim on your behalf; you do not need to do anything to receive the 20% basic-rate top-up.",
                    "This automatic 20% top-up applies to all SIPP contributions, regardless of whether you actually pay income tax. A non-taxpayer or low earner below the personal allowance still receives the 20% top-up on contributions up to £3,600 gross per year (£2,880 net). For contributions above that level, relevant UK earnings are required. HMRC has the right to reclaim relief if your earnings are insufficient, but in practice this is rarely pursued for modest contributions.",
                ],
            },
            {
                "heading": "SIPP vs Workplace Pension",
                "paragraphs": [
                    "A SIPP is a personal pension — you set it up directly with a provider, you choose the investments (from the provider's available range), and you pay all charges. The investment universe in a SIPP is typically much broader than a workplace scheme: you can hold listed shares, ETFs, bonds, commercial property (in some SIPPs) and a wide range of funds. Charges vary significantly between providers, from flat fees (better for large pots) to percentage-based fees (cheaper initially but expensive as the pot grows).",
                    "Workplace pensions are operated by your employer. Under auto-enrolment, employers must contribute at least 3% of qualifying earnings (employees at least 5%) — a minimum 8% total. Many employers offer additional matching. Workplace pensions may use net pay arrangement or salary sacrifice rather than relief at source, which affects the administration. The investment options in workplace schemes are typically more limited than in a SIPP, but the employer contribution is a significant and often irreplaceable benefit that a self-directed SIPP cannot replicate.",
                ],
            },
            {
                "heading": "Higher-Rate Additional Relief Claim",
                "paragraphs": [
                    "If you pay income tax at 40% (higher rate) or 45% (additional rate), you are entitled to relief above the automatic 20% that the provider claims. To get this additional relief, you must file a Self Assessment tax return and enter your gross SIPP contributions for the year. HMRC then extends the basic-rate band by the gross contribution amount — effectively taxing less of your income at 40% or 45% — and refunds or reduces your tax liability accordingly.",
                    "For a higher-rate taxpayer who contributes £10,000 net to a SIPP: the provider claims £2,500 basic-rate relief, giving £12,500 gross in the pension. The higher-rate taxpayer then claims an additional 20% on £12,500 via Self Assessment = £2,500. Total relief: £5,000 (40% of £12,500). Net cost: £10,000 − £2,500 = £7,500. For an additional-rate (45%) taxpayer: additional claim is 25% on £12,500 = £3,125. Total relief: £5,625 (45%). Net cost: £10,000 − £3,125 = £6,875.",
                ],
            },
            {
                "heading": "Drawdown from a SIPP",
                "paragraphs": [
                    "When you access your SIPP in retirement, you are entitled to take 25% of the fund as a tax-free pension commencement lump sum (PCLS), subject to the lump sum allowance (£268,275 since the lifetime allowance was abolished in April 2024). The remaining 75% is drawn as taxable income — charged at your marginal rate when withdrawn. You can choose how much to draw each year, giving flexibility to manage your tax position in retirement.",
                    "Most people draw from their SIPP gradually in drawdown, taking enough to use up the personal allowance each year tax-free and drawing modest additional amounts at basic rate. Timing drawdown thoughtfully — avoiding taking large sums in years when other income is high — can reduce the overall tax paid in retirement substantially. For those with defined benefit pensions and state pension that already fill or approach the personal allowance, SIPP drawdown in excess of this will be fully taxable at the relevant rate.",
                ],
            },
        ],
        "faqs": [
            {"q": "How much do I actually pay into my SIPP per pound of contribution?", "a": "You pay 80p and your SIPP receives £1 (the provider claims 20% from HMRC). A higher-rate taxpayer who then claims additional relief via Self Assessment effectively pays 60p per £1 in the pension."},
            {"q": "Can I have both a SIPP and a workplace pension?", "a": "Yes. Contributions to both count towards your combined annual allowance of £60,000. Many people contribute to both — using the workplace pension for employer matching and the SIPP for additional contributions with wider investment choice."},
            {"q": "Is there a minimum I can contribute to a SIPP?", "a": "Most providers have a minimum, often £50–£100 per month or a lump sum minimum. There is no HMRC minimum — though you need relevant UK earnings to contribute more than £3,600 gross per year."},
        ],
        "sources": [
            {"label": "HMRC: Tax on your private pension contributions", "url": "https://www.gov.uk/tax-on-your-private-pension/pension-tax-relief"},
            {"label": "HMRC: Self-invested personal pensions", "url": "https://www.gov.uk/self-invested-personal-pensions"},
        ],
    },
    {
        "slug": "salary-sacrifice-vs-relief-at-source",
        "title": "Salary Sacrifice vs Relief at Source — Which Saves More?",
        "description": "Salary sacrifice saves income tax and National Insurance. Relief at source saves income tax only. The difference is the NI saving — plus some important edge cases where the comparison changes.",
        "date": "26 May 2026",
        "date_iso": "2026-05-26",
        "reading_time": "7 min read",
        "sections": [
            {
                "heading": "The Key Difference",
                "paragraphs": [
                    "The fundamental distinction between salary sacrifice and relief at source (or net pay arrangement) is National Insurance. Under salary sacrifice, your gross salary is formally reduced — income tax and employee NI are both calculated on the lower figure. You save tax and NI on every pound sacrificed. Under relief at source or net pay arrangement, your gross salary is unchanged — you pay NI on the full salary and only receive tax relief on the pension contribution. No NI saving arises.",
                    "For most employed people who have access to salary sacrifice, this makes salary sacrifice strictly more efficient than RaS or NPA for pension contributions. The NI saving is not trivial: at the main employee rate of 8%, a £5,000 salary sacrifice saves £400 in employee NI in addition to the income tax saving. Over a working lifetime at that contribution level, this amounts to substantial additional pension contributions at no extra cost to the employee.",
                ],
            },
            {
                "heading": "The NI Saving in Salary Sacrifice",
                "paragraphs": [
                    "Employee NI for 2026/27 is 8% on earnings between the primary threshold (£12,570) and the upper earnings limit (£50,270), and 2% on earnings above the upper limit. A salary sacrifice of £5,000 for someone earning £35,000 saves 8% × £5,000 = £400 in employee NI and 20% × £5,000 = £1,000 in income tax — a total personal saving of £1,400, compared to a £1,000 saving under a RaS or NPA pension contribution.",
                    "Employers save 15% secondary NI on the sacrificed amount. On a £5,000 sacrifice, the employer saves £750. Many employers share this saving back into the employee's pension — known as NI matching or passthrough. Where available, this can add a further £375–£750 to the pension contribution at no cost to the employee, making salary sacrifice with employer NI passthrough markedly more valuable than any other contribution method.",
                ],
            },
            {
                "heading": "When Relief at Source May Be Preferable",
                "paragraphs": [
                    "There are specific situations where RaS or NPA is more appropriate than salary sacrifice despite the NI cost. Student loan repayments under Plans 1, 2, 4 and 5 are calculated on gross employment income above the relevant threshold. Under salary sacrifice, the sacrificed salary is removed from the gross pay figure, reducing student loan repayments. This may or may not be desirable depending on whether the borrower is on track to repay the full loan before the write-off date. For those who will repay in full, reducing repayments extends the repayment period and increases total interest — a worse outcome.",
                    "Benefits in kind and certain employment rights are sometimes calculated on contractual salary. Income protection insurance, death-in-service cover, enhanced redundancy payments and statutory maternity pay may all be based on contractual salary rather than gross pay. Salary sacrifice reduces contractual salary, potentially reducing these benefits. If your employer calculates these benefits on the post-sacrifice figure, you need to weigh the NI saving against the reduction in insurance cover or SMP. Check your employment contract carefully.",
                ],
            },
            {
                "heading": "Practical Guidance on Which to Choose",
                "paragraphs": [
                    "For most employees with access to salary sacrifice: choose salary sacrifice. The NI saving alone justifies it for the vast majority of workers, and the employer NI passthrough (where available) adds further value. The exceptions — student loan edge cases, SMP calculations near threshold — affect a minority of workers and should be modelled individually.",
                    "For self-employed and company directors who cannot use salary sacrifice: use a SIPP under relief at source. Ensure you file Self Assessment to claim higher-rate additional relief if your income is above £50,270. Company directors can also use employer pension contributions paid directly from the company, which provide the equivalent of salary sacrifice efficiency — the company pays into the pension instead of paying a taxable salary or dividend.",
                ],
            },
        ],
        "faqs": [
            {"q": "Why is salary sacrifice better than relief at source for most employees?", "a": "Because salary sacrifice also saves National Insurance (8% at main rate), in addition to the income tax saving. Under relief at source, no NI saving applies — only the income tax relief."},
            {"q": "Does salary sacrifice affect student loan repayments?", "a": "Yes, it reduces them — because repayments are calculated on gross pay, and salary sacrifice reduces gross pay. Whether this is beneficial depends on your repayment plan and whether you expect to repay the full loan before write-off."},
            {"q": "Can I use both salary sacrifice and a SIPP?", "a": "Yes. Contributions to both count towards the annual allowance (£60,000 combined). Many people use salary sacrifice for their workplace pension and a SIPP for additional contributions and wider investment choice."},
        ],
        "sources": [
            {"label": "HMRC: Salary sacrifice for employees", "url": "https://www.gov.uk/salary-sacrifice-and-the-effects-on-pensions"},
            {"label": "HMRC: Tax on private pension contributions", "url": "https://www.gov.uk/tax-on-your-private-pension/pension-tax-relief"},
        ],
    },
    {
        "slug": "pension-tax-relief-scotland-2026",
        "title": "Pension Tax Relief in Scotland 2026/27: Scottish Income Tax Rates and Relief Explained",
        "description": "Scottish taxpayers have five income tax bands, which affects how much pension tax relief they receive and whether they need to claim additional relief via Self Assessment. Here is the full picture.",
        "date": "22 May 2026",
        "date_iso": "2026-05-22",
        "reading_time": "6 min read",
        "faqs": [
            {"q": "Do Scottish taxpayers get relief at source at 20% or at their Scottish rate?", "a": "Relief at source is always applied at 20% basic rate by the pension provider, regardless of the taxpayer's location. Scottish taxpayers who pay higher rates than 20% — including the 19% starter rate (which is below 20%) — must reconcile the difference through Self Assessment. HMRC has a separate process for starter-rate taxpayers who have been over-credited."},
            {"q": "How does a Scottish intermediate-rate taxpayer claim the extra 1% relief?", "a": "A Scottish taxpayer in the 21% intermediate band who uses a relief at source pension has already received 20% through the provider top-up. To claim the additional 1%, they must file a Self Assessment return and include the gross pension contribution. HMRC will calculate the additional relief and either reduce the tax bill or issue a repayment."},
            {"q": "What is the Scottish higher rate in 2026/27?", "a": "Scotland's higher rate is 42% in 2026/27, applying to income between £43,663 and £75,000. This is 2 percentage points higher than the rUK higher rate of 40%. A Scottish higher-rate taxpayer contributing to a pension under net pay arrangement or salary sacrifice receives 42% relief automatically; under relief at source they must claim the extra 22% (42% − 20%) via Self Assessment."},
        ],
        "sections": [
            {
                "heading": "Scotland's income tax bands in 2026/27",
                "paragraphs": [
                    "Scotland has its own income tax rates set by the Scottish Parliament. For 2026/27 there are five bands: 19% starter rate (£12,571–£15,397), 20% basic rate (£15,398–£27,491), 21% intermediate rate (£27,492–£43,662), 42% higher rate (£43,663–£75,000), and 45% top rate above £75,000. National Insurance rates and the personal allowance (£12,570) are set at Westminster and apply uniformly across the UK.",
                    "These Scottish rates directly affect how much pension tax relief a Scottish taxpayer receives, and how they receive it. Under relief at source, the provider always claims 20% from HMRC — regardless of where in the UK the taxpayer lives. Under a net pay arrangement, contributions come off gross salary before Scottish income tax is applied, so relief is given automatically at the correct Scottish marginal rate. Under salary sacrifice, gross salary is reduced and the full Scottish marginal rate applies.",
                ],
            },
            {
                "heading": "Relief at source: the Scottish complication",
                "paragraphs": [
                    "For Scottish taxpayers using a relief at source pension (typical for SIPPs and many personal pensions), the provider tops up every £80 paid in to £100, claiming 20% from HMRC. This is correct for taxpayers in the 20% basic band. But it over-credits starter-rate (19%) taxpayers who should only receive 19% — though HMRC generally does not claw this back from individuals. For those in the 21% intermediate band, the provider gives 20% but the taxpayer is entitled to 21%, so they must claim the extra 1% via Self Assessment.",
                    "For Scottish higher-rate (42%) taxpayers, the provider gives 20% automatically and the taxpayer must claim the remaining 22% (42% − 20%) via Self Assessment. For top-rate (45%) taxpayers, the extra 25% must be claimed. These claims are made on the SA100 tax return under the pension contributions section — the gross contribution is entered and HMRC calculates the relief due.",
                ],
            },
            {
                "heading": "Net pay arrangement: correct Scottish relief automatically",
                "paragraphs": [
                    "Workplace pension schemes that operate under a net pay arrangement are much simpler for Scottish taxpayers. Contributions are deducted from gross salary before payroll calculates income tax, so if your marginal rate is 21%, 42% or 45%, you receive that rate of relief automatically without any Self Assessment claim. This is the main administrative advantage of NPA for Scottish higher earners.",
                    "The drawback for NPA schemes historically was that earners below the personal allowance received no tax relief (since they pay no tax), and low earners received less relief relative to RaS equivalents. The government introduced a top-up mechanism from 2024/25 to address this, though administration by employers has been uneven.",
                ],
            },
            {
                "heading": "Worked example: Scottish intermediate-rate taxpayer at £32,000",
                "paragraphs": [
                    "A Scottish taxpayer earning £32,000 is in the 21% intermediate band (earnings between £27,492 and £43,662). They contribute £4,000 net to a relief at source pension. The provider tops this up by 20% to £5,000 gross. To claim the additional 1%, the taxpayer includes £5,000 gross on their Self Assessment return. HMRC applies 21% − 20% = 1% extra relief: 1% × £5,000 = £50 additional relief. Total effective relief: 21% × £5,000 = £1,050 on a £4,000 net contribution. Net cost: £4,000 − £50 = £3,950 (after claiming).",
                    "For comparison, a Scottish higher-rate taxpayer at £50,000 contributing £4,000 net gets: provider tops up to £5,000; they claim 42% − 20% = 22% extra via SA: 22% × £5,000 = £1,100. Total relief: 42% × £5,000 = £2,100. Net cost of a £5,000 pension contribution: £4,000 − £1,100 = £2,900. At that effective cost, higher-rate pension contributions are genuinely compelling.",
                ],
            },
            {
                "heading": "Salary sacrifice and Scottish rates",
                "paragraphs": [
                    "Salary sacrifice is the cleanest method for Scottish taxpayers because the full Scottish marginal rate applies to the sacrificed amount without any Self Assessment claim. The sacrifice reduces gross pay, and since Scottish income tax bands are applied to gross pay, the saving is automatic. There is no risk of forgetting to claim via Self Assessment. Combined with the NI saving (UK-wide at 8% main rate), salary sacrifice remains the most efficient method for employed Scottish workers whose employer offers it.",
                ],
            },
        ],
        "sources": [
            {"label": "Scottish Government: Income Tax rates 2026/27", "url": "https://www.gov.scot/policies/taxes/income-tax/"},
            {"label": "HMRC: Scottish Income Tax", "url": "https://www.gov.uk/scottish-income-tax"},
            {"label": "HMRC: Tax on private pension contributions", "url": "https://www.gov.uk/tax-on-your-private-pension/pension-tax-relief"},
        ],
    },
    {
        "slug": "pension-annual-allowance-charge-explained",
        "title": "Pension Annual Allowance 2026/27: £60,000 Limit, What Counts and How to Avoid a Charge",
        "description": "The annual allowance for 2026/27 is £60,000, or 100% of your earnings — whichever is lower. Exceeding it triggers an annual allowance charge. Here is what counts towards it and how to plan around it.",
        "date": "22 May 2026",
        "date_iso": "2026-05-22",
        "reading_time": "6 min read",
        "faqs": [
            {"q": "Does the annual allowance include employer contributions?", "a": "Yes. The annual allowance covers all pension inputs — your own contributions, employer contributions and any contributions made by a third party on your behalf. For defined contribution (DC) schemes, the allowance is the total of all contributions in the tax year. For defined benefit (DB) schemes, it is calculated as the annual increase in the pension accrual value multiplied by a factor of 16, plus any lump sum increase."},
            {"q": "What happens if I exceed the annual allowance?", "a": "Exceeding the annual allowance triggers an annual allowance charge, added to your income tax liability for that year. The charge is calculated at your marginal income tax rate on the excess. So if you exceed by £10,000 and you are a 40% taxpayer, the charge is £4,000. You can ask your pension scheme to pay the charge from your pension pot, known as 'scheme pays'."},
            {"q": "What is the tapered annual allowance?", "a": "High earners with adjusted income over £260,000 face a tapered annual allowance, reduced by £1 for every £2 of adjusted income above that threshold. The minimum tapered allowance is £10,000, reached at £360,000 adjusted income. If your income is below £260,000 the standard £60,000 allowance applies."},
        ],
        "sections": [
            {
                "heading": "The standard annual allowance for 2026/27",
                "paragraphs": [
                    "The annual allowance (AA) for 2026/27 is £60,000. This is the maximum you can contribute to all registered pension schemes in a tax year while still receiving tax relief. The allowance was increased from £40,000 to £60,000 in April 2023 as part of the Spring Budget 2023 changes, which also abolished the lifetime allowance. The AA applies to the combined total of all contributions across all your pension schemes, including workplace pensions, SIPPs and any other registered pension.",
                    "There is a secondary limit: contributions in any year are also capped at 100% of your relevant UK earnings (salary, self-employment income, etc.). If you earn £30,000, you can contribute up to £30,000 in that year even though the nominal AA is £60,000. You cannot contribute more than your earnings even if unused carry-forward allowance is available, except through employer contributions which are not subject to the earnings cap.",
                ],
            },
            {
                "heading": "What counts towards the annual allowance",
                "paragraphs": [
                    "For defined contribution (DC) schemes — which includes most workplace pensions, SIPPs and personal pensions — the total pension input is all contributions made in the pension input period (the tax year), regardless of who paid them. Employee contributions, employer contributions and contributions from any third party all count. For a salary sacrifice arrangement, the employer contribution replacing the sacrificed salary counts as a pension input.",
                    "For defined benefit (DB) schemes — final salary or career average schemes — the calculation is more complex. HMRC uses a formula: the pension input is 16 × (closing pension accrual − opening pension accrual), adjusted for inflation, plus any pension commencement lump sum increase. DB pension accrual can be surprisingly high for senior public sector workers or those in private DB schemes, and it is worth calculating this before making additional contributions to a DC scheme in the same year.",
                ],
            },
            {
                "heading": "The money purchase annual allowance (MPAA)",
                "paragraphs": [
                    "Once you flexibly access a defined contribution pension — by taking an income via flexi-access drawdown, taking an uncrystallised funds pension lump sum, or annuitising part of the fund — you trigger the Money Purchase Annual Allowance of £10,000. This replaces the standard £60,000 AA for future DC contributions and cannot be increased by carry forward. The MPAA does not apply to DB accrual.",
                    "Taking a tax-free cash lump sum from a pension without entering drawdown does not trigger the MPAA. Small pots of under £10,000 can also be taken as a lump sum without triggering it. If you have already flexibly accessed a DC pension, take care before making significant new DC contributions — the £10,000 MPAA limit is much harder to manage.",
                ],
            },
            {
                "heading": "The annual allowance charge",
                "paragraphs": [
                    "If your total pension inputs exceed the annual allowance in a tax year, the excess is added to your income for tax purposes and charged at your marginal rate. The charge is reported and paid through Self Assessment. You can ask your pension scheme to pay the charge directly from your pension pot rather than from your take-home pay — this is known as mandatory scheme pays (where the excess is over £2,000 and total contributions exceed £60,000) or voluntary scheme pays. Your pension pot is reduced accordingly.",
                    "For those close to the limit, the annual allowance checker tool can help you assess whether your inputs for 2026/27 are on track to trigger a charge. If they are, you may be able to use carry forward from earlier years to absorb the excess legitimately.",
                ],
            },
        ],
        "sources": [
            {"label": "HMRC: Annual allowance for pension savings", "url": "https://www.gov.uk/pension-annual-allowance"},
            {"label": "HMRC: Pension input periods and pension input amounts", "url": "https://www.gov.uk/hmrc-internal-manuals/pensions-tax-manual/ptm050000"},
        ],
    },
    {
        "slug": "pension-carry-forward-explained",
        "title": "Pension Carry Forward 2026/27: How to Use Three Years of Unused Annual Allowance",
        "description": "Carry forward lets you contribute more than £60,000 in a single tax year by using unused annual allowance from the three previous years. Useful for bonus earners, business owners and anyone whose income fluctuates.",
        "date": "22 May 2026",
        "date_iso": "2026-05-22",
        "reading_time": "6 min read",
        "faqs": [
            {"q": "Do I need to have been contributing to a pension to use carry forward?", "a": "You must have been a member of a registered pension scheme in each of the three previous tax years to use that year's unused allowance. You do not need to have actually made contributions — simply being enrolled in a workplace pension, even if making no contributions, qualifies you. It is worth keeping a note of your membership dates for all schemes."},
            {"q": "Can I carry forward allowance from before the £60,000 increase?", "a": "Yes. The annual allowance was £40,000 in 2022/23 and prior years. If you are using carry forward from 2023/24, the allowance was £60,000. From 2022/23 it was £40,000. The available carry forward is the actual allowance for that year minus actual pension inputs in that year."},
            {"q": "Is there a limit to how much I can carry forward?", "a": "In theory you can carry forward up to three years of full unused allowance — up to £180,000 (3 × £60,000) if you made no contributions in those years. However, your total contributions in the carry-forward year are still capped at 100% of your relevant UK earnings in that year. So if you earned £80,000, you cannot contribute more than £80,000 in total regardless of available carry forward."},
        ],
        "sections": [
            {
                "heading": "What carry forward is and when it is useful",
                "paragraphs": [
                    "Carry forward is a rule that allows you to use unused annual allowance from the three previous tax years when your pension inputs in the current year exceed the standard £60,000 limit. It is particularly valuable for people whose income is irregular — business owners taking large dividends in good years, employees receiving significant bonuses, or professionals who have recently moved into higher earning roles. Without carry forward, anyone who wants to make a large one-off pension contribution is constrained to £60,000 regardless of their history.",
                    "The mechanics are straightforward. First, use the current year's full allowance (£60,000 for 2026/27). Then apply carry forward from the earliest of the three previous years first (2023/24), then 2024/25, then 2025/26. The carry-forward amount from each year is that year's annual allowance minus total pension inputs in that year. Unused allowance from years before the three-year window is lost permanently.",
                ],
            },
            {
                "heading": "Calculating your available carry forward",
                "paragraphs": [
                    "To calculate carry forward, you need to know: (1) the annual allowance for each of the past three tax years — £60,000 for 2023/24, 2024/25 and 2025/26; and (2) your total pension inputs for each of those years (employee contributions + employer contributions for DC, or the DB accrual calculation for DB). Available carry forward from each year = annual allowance − pension inputs, subject to a minimum of zero.",
                    "For example, if in 2023/24 you had total pension inputs of £10,000, in 2024/25 £15,000, and in 2025/26 £20,000, your available carry forward is: £50,000 + £45,000 + £40,000 = £135,000. Adding the current year's £60,000 allowance, you can contribute up to £195,000 in 2026/27 — subject to the 100% earnings cap.",
                ],
            },
            {
                "heading": "Practical uses: bonuses, sale proceeds and business distributions",
                "paragraphs": [
                    "Carry forward is particularly effective when a large income event creates tax exposure. An employee receiving a £50,000 bonus on top of a £60,000 salary, who has accumulated £120,000 of carry-forward allowance, could sacrifice the entire bonus into a pension plus £60,000 of salary — a total contribution of £110,000, within the combined current-year-plus-carry-forward limit. The income tax and NI saving on the bonus at 40%/2% rates is very substantial.",
                    "For owner-managed businesses, carry forward enables large employer pension contributions in profitable years — reducing both personal tax and corporation tax (employer pension contributions are a deductible business expense). A sole director with three years of minimal pension inputs might accumulate close to £180,000 of carry-forward allowance, all deployable in a single year if earnings permit.",
                ],
            },
            {
                "heading": "Scheme pays and the annual allowance charge interaction",
                "paragraphs": [
                    "If you use carry forward correctly, there should be no annual allowance charge because your total inputs remain within the combined allowance. The risk arises if carry forward is miscalculated — for example if pension inputs in earlier years were higher than assumed, or if membership of a DB scheme was overlooked. Always obtain your pension input amounts from your scheme administrators rather than estimating, as DB inputs in particular can be unexpectedly large.",
                ],
            },
        ],
        "sources": [
            {"label": "HMRC: Carry forward of unused annual allowance", "url": "https://www.gov.uk/hmrc-internal-manuals/pensions-tax-manual/ptm055400"},
            {"label": "HMRC: Annual allowance for pension savings", "url": "https://www.gov.uk/pension-annual-allowance"},
        ],
    },
    {
        "slug": "pension-tax-relief-self-employed-2026",
        "title": "Pension Tax Relief for the Self-Employed in 2026/27: SIPPs, RaS and Claiming Higher-Rate Relief",
        "description": "Self-employed people cannot use salary sacrifice and must use personal pensions or SIPPs. Relief at source gives 20% automatically; higher-rate relief requires a Self Assessment claim. Here is how it works.",
        "date": "22 May 2026",
        "date_iso": "2026-05-22",
        "reading_time": "6 min read",
        "faqs": [
            {"q": "Can self-employed people use salary sacrifice?", "a": "No. Salary sacrifice is only available to employed workers, as it requires an employer to amend the employment contract and make pension contributions in place of salary. Sole traders, partners and owner-managed company directors drawing only dividends cannot use salary sacrifice. A director who draws a salary from their company could theoretically use salary sacrifice, but this requires the company to operate the scheme."},
            {"q": "What is the best pension for a self-employed person?", "a": "A Self-Invested Personal Pension (SIPP) gives maximum flexibility and investment choice. Stakeholder pensions are a low-cost alternative with capped charges. Both operate under relief at source. The 'best' pension depends on investment preferences, cost sensitivity and whether you want the ability to hold commercial property or other alternative assets."},
            {"q": "Can a limited company director make employer pension contributions?", "a": "Yes, and this is often very tax-efficient. A limited company can make employer pension contributions directly to a director's pension. These contributions are a deductible business expense, reducing corporation tax. They also avoid income tax and National Insurance that would apply if the money were paid as salary or dividend. This is one of the most tax-efficient routes out of a limited company for owner-directors."},
        ],
        "sections": [
            {
                "heading": "How relief at source works for the self-employed",
                "paragraphs": [
                    "Most self-employed people use personal pensions or SIPPs that operate under relief at source (RaS). When you make a contribution, you pay the net amount and your pension provider automatically claims 20% basic-rate relief from HMRC, adding it to your pension pot. This means every £80 you contribute becomes £100 in the pension. The relief is received whether or not you actually pay 20% income tax — though HMRC has the right to reclaim relief if your income is below the personal allowance.",
                    "The annual allowance for self-employed people is the same as for employees: £60,000 or 100% of net relevant earnings, whichever is lower. Net relevant earnings for the self-employed means trading income, property income and certain other sources — not dividends, which do not qualify as relevant earnings. This means a company director drawing only dividends cannot make personal pension contributions that attract tax relief, though the company can make employer contributions.",
                ],
            },
            {
                "heading": "Claiming higher-rate relief via Self Assessment",
                "paragraphs": [
                    "If you pay 40% or 45% income tax, you are entitled to more than the 20% basic-rate relief that is automatically applied under RaS. To claim the additional relief, you must file a Self Assessment tax return and enter your gross pension contributions (the amount in the pension, including the provider's 20% top-up) in the relevant section. HMRC will either reduce your tax liability or, if you have already paid, issue a repayment.",
                    "For a self-employed higher-rate taxpayer contributing £16,000 net per year: the provider tops up to £20,000 gross. Via Self Assessment, they claim 40% − 20% = 20% additional relief on £20,000 = £4,000. Total relief: 40% × £20,000 = £8,000. Net cost of the £20,000 pension contribution: £16,000 − £4,000 = £12,000. This is the same outcome as a higher-rate employed taxpayer using net pay arrangement, but it requires an annual Self Assessment filing.",
                ],
            },
            {
                "heading": "Scottish self-employed taxpayers",
                "paragraphs": [
                    "Scottish self-employed taxpayers face the same complication as Scottish employed workers on relief at source: the provider claims 20% regardless, but Scottish rates may differ. Intermediate-rate (21%) Scottish taxpayers claim an extra 1% via Self Assessment. Higher-rate (42%) taxpayers claim the extra 22%. Top-rate (45%) taxpayers claim the extra 25%. All of these claims are made through the same Self Assessment process, with the gross pension contribution entered on the SA100.",
                ],
            },
            {
                "heading": "Company pension contributions for owner-directors",
                "paragraphs": [
                    "Owner-managed limited company directors have a particularly powerful tool: employer pension contributions paid directly from the company. These are not limited by the director's personal salary (unlike personal RaS contributions which need relevant earnings) as long as HMRC regards them as being wholly and exclusively for the purposes of the trade. The contributions reduce the company's taxable profits, saving corporation tax at 19–25%.",
                    "The director also avoids the dividend income tax and National Insurance that would apply if the same money were extracted as additional pay. Combined with carry-forward allowance from prior years, a profitable director can extract very substantial sums from the company in a tax-efficient way. Always take professional advice on the wholly-and-exclusively test and the interaction with the annual allowance.",
                ],
            },
        ],
        "sources": [
            {"label": "HMRC: Tax on private pension contributions", "url": "https://www.gov.uk/tax-on-your-private-pension/pension-tax-relief"},
            {"label": "HMRC: Self Assessment — pension payments SA100", "url": "https://www.gov.uk/self-assessment-tax-returns"},
            {"label": "HMRC: Corporation Tax relief for employer pension contributions", "url": "https://www.gov.uk/hmrc-internal-manuals/business-income-manual/bim46000"},
        ],
    },
    {
        "slug": "does-pension-reduce-tax-bill",
        "title": "Does a Pension Contribution Reduce Your Tax Bill? Yes — And Often by More Than You Think",
        "description": "Pension contributions reduce your adjusted net income, which in turn affects your personal allowance, child benefit charges, childcare eligibility and student loan thresholds. The effective saving often exceeds the headline tax rate.",
        "date": "22 May 2026",
        "date_iso": "2026-05-22",
        "reading_time": "6 min read",
        "faqs": [
            {"q": "Does a pension contribution reduce income for child benefit purposes?", "a": "Yes. Pension contributions reduce adjusted net income (ANI). The High Income Child Benefit Charge is calculated on ANI. If your ANI is between £60,000 and £80,000, reducing it via pension contributions reduces the clawback. If you reduce ANI below £60,000, the HICBC is eliminated entirely."},
            {"q": "Do pension contributions affect my student loan repayments?", "a": "For Plan 1 and Plan 2 loans, repayments are calculated on total income above the threshold. Salary sacrifice reduces gross pay and therefore the income figure used for student loan calculations — reducing or eliminating repayments. Personal pension contributions under RaS or NPA do not reduce the income figure for student loan purposes."},
            {"q": "What is adjusted net income?", "a": "Adjusted net income (ANI) is your total income (employment, self-employment, property, dividends, etc.) minus gross personal pension contributions and gift aid donations. It is the figure HMRC uses for various threshold tests including: personal allowance tapering above £100k, HICBC above £60k, 30-hour childcare eligibility at £100k, and student loan thresholds."},
        ],
        "sections": [
            {
                "heading": "The direct tax saving: income tax and NI",
                "paragraphs": [
                    "A pension contribution reduces your taxable income. Under a net pay arrangement or salary sacrifice, the reduction is direct — your gross pay before tax is lower, so income tax and NI are assessed on a smaller figure. Under relief at source, you contribute from post-tax income and HMRC credits the relief back. In all cases, the income tax saving is at your marginal rate: 20% for basic rate, 40% for higher rate, 45% for additional rate (or the equivalent Scottish rates).",
                    "Salary sacrifice also reduces the NI charge, unlike RaS or NPA. At the main rate of 8% (earnings between £12,570 and £50,270), a £1,000 sacrifice saves £80 in NI on top of the income tax saving. At the 2% rate above the upper earnings limit, the NI saving is £20 per £1,000. The combined income tax plus NI saving is the most commonly cited benefit of pension contributions — but it is not the whole story.",
                ],
            },
            {
                "heading": "The personal allowance trap: effective 60% rate at £100k–£125,140",
                "paragraphs": [
                    "If your income is between £100,000 and £125,140, you are in the personal allowance tapering zone. The personal allowance (£12,570) is reduced by £1 for every £2 of ANI above £100,000. In this band your effective marginal income tax rate is 60%, because earning an extra £1 costs you 40p income tax plus 20p more income tax on the lost personal allowance (40p × 50p of each £1 going to restore the allowance).",
                    "A pension contribution that reduces ANI from within this band saves at the effective 60% rate. Someone with income of £110,000 who contributes £10,000 to a pension (reducing ANI to £100,000) saves 60% × £10,000 = £6,000 in income tax. That is a £6,000 saving for a pension contribution that costs only £4,000 net (since the £10,000 gross contribution was funded partly by the tax saving). The pension contribution effectively pays for 60% of itself in tax savings alone.",
                ],
            },
            {
                "heading": "Child benefit and 30-hour childcare eligibility",
                "paragraphs": [
                    "Two government-administered benefits are gated behind ANI thresholds that pension contributions can influence. The High Income Child Benefit Charge (HICBC) begins at £60,000 ANI and withdraws child benefit at 1% per £200 above that level, reaching full withdrawal at £80,000. Pension contributions that reduce ANI from above to below £60,000 eliminate the charge entirely. Contributions that reduce ANI from within the £60,000–£80,000 range proportionally reduce the charge.",
                    "The 30-hour free childcare offer for 3–4 year olds requires all earners in the household to have ANI below £100,000. Exceeding this threshold by even £1 loses the additional 15 hours per week — potentially worth £5,000–£10,000 per year in avoided childcare fees. A pension contribution that brings ANI below £100,000 therefore saves far more than the income tax on the contribution amount alone. This makes contributions near the £100,000 threshold among the highest-return pension investments available.",
                ],
            },
            {
                "heading": "Worked example: £105,000 income, one pre-school child",
                "paragraphs": [
                    "Parent with ANI of £105,000 and one child aged 3 using 30 hours free childcare. They make £7,000 gross pension contribution (net pay or salary sacrifice), reducing ANI to £98,000. Benefits: (1) Personal allowance restored — £105,000 has £2,500 PA taper: saving at effective 60% on £5,000 excess = £3,000 saving from full £5,000 restoration. Actually: PA at £105k is reduced by £2,500 so £10,070 PA instead of £12,570 — restoring to full saves: £2,500 × 40% = £1,000. Plus the 60% rate on £5,000 of the contribution above £100k saves 60% × £5,000 = £3,000. (2) 30-hour childcare retained: £5,000–£8,000 in avoided childcare fees. Total benefit of £7,000 contribution significantly exceeds the contribution cost.",
                ],
            },
        ],
        "sources": [
            {"label": "HMRC: Tax and National Insurance — pensions", "url": "https://www.gov.uk/tax-on-your-private-pension/pension-tax-relief"},
            {"label": "HMRC: High Income Child Benefit Charge", "url": "https://www.gov.uk/child-benefit-tax-charge"},
            {"label": "GOV.UK: 30 hours free childcare eligibility", "url": "https://www.gov.uk/30-hours-free-childcare"},
        ],
    },
    {
        "slug": "pension-contribution-limits-explained",
        "title": "Pension Contribution Limits 2026/27: Annual Allowance, MPAA and Lump Sum Allowance",
        "description": "The £60,000 annual allowance, £10,000 MPAA, £268,275 lump sum allowance and the end of the lifetime allowance — all the limits that govern how much you can put into and take out of a pension.",
        "date": "22 May 2026",
        "date_iso": "2026-05-22",
        "reading_time": "7 min read",
        "faqs": [
            {"q": "Was the lifetime allowance abolished?", "a": "Yes. The lifetime allowance (LTA) was abolished from 6 April 2024. Before that date, the LTA was the maximum fund value you could build up in registered pensions without incurring a tax charge (£1,073,100 for 2023/24). The LTA charge was abolished in 2023 and the LTA itself from April 2024. It was replaced by two new lump sum limits: the lump sum allowance (£268,275) and the lump sum and death benefit allowance (£1,073,100)."},
            {"q": "What is the lump sum allowance?", "a": "The lump sum allowance (LSA) of £268,275 is the maximum amount you can take as a tax-free lump sum from your pensions over your lifetime (from 6 April 2024). It replaces the 25% tax-free element under the old LTA. If your 25% of your pension pot exceeds £268,275, the excess is taxed as income. Most people will never reach this limit."},
            {"q": "What triggers the MPAA?", "a": "The Money Purchase Annual Allowance (£10,000) is triggered when you flexibly access a defined contribution pension — typically by taking income from flexi-access drawdown, receiving an uncrystallised funds pension lump sum (UFPLS), or annuitising with an enhanced annuity that includes an income guarantee. Taking a tax-free lump sum only (without drawdown), taking a small pot (under £10,000), or taking a DB pension does not trigger the MPAA."},
        ],
        "sections": [
            {
                "heading": "The annual allowance: £60,000 standard, £10,000 MPAA",
                "paragraphs": [
                    "The standard annual allowance (AA) for 2026/27 is £60,000. This is the maximum total pension input — your contributions, employer contributions and DB accrual — that you can make in a tax year and still receive tax relief. Exceeding the AA triggers an annual allowance charge at your marginal income tax rate. You can reduce or eliminate this charge by using carry-forward allowance from the previous three years.",
                    "If you have flexibly accessed a DC pension, the Money Purchase Annual Allowance (MPAA) of £10,000 applies to future DC contributions instead of the standard £60,000. The MPAA cannot be increased by carry forward. This creates a significant planning constraint — once triggered, you can only contribute £10,000 per year to DC pensions. DB accrual is unaffected. The MPAA was increased from £4,000 to £10,000 in April 2023.",
                ],
            },
            {
                "heading": "The tapered annual allowance for high earners",
                "paragraphs": [
                    "For those with adjusted income over £260,000, the annual allowance is tapered downwards. The taper reduces the AA by £1 for every £2 of adjusted income above £260,000 (adjusted income = all income plus employer pension contributions). The minimum AA under tapering is £10,000, reached at £360,000 adjusted income. Threshold income (all income excluding employer pension contributions) must also exceed £200,000 for the taper to apply — if threshold income is below £200,000, the full £60,000 AA applies regardless of adjusted income.",
                    "Planning around the tapered AA is complex because employer pension contributions increase adjusted income. For those near the threshold, a large employer contribution can push adjusted income above £260,000 and reduce the available AA. Scheme pays may be necessary if the allowance is unknowingly breached.",
                ],
            },
            {
                "heading": "Post-LTA limits: lump sum allowance and LSDBA",
                "paragraphs": [
                    "Since the lifetime allowance was abolished in April 2024, two new limits control tax-free lump sums. The lump sum allowance (LSA) of £268,275 is the maximum tax-free cash you can take across all lump sum events in your lifetime. If the total of all your pension commencement lump sums (PCLS) and uncrystallised funds pension lump sums (UFPLS) taken as tax-free amounts exceeds £268,275, the excess is taxed at your marginal income tax rate when received.",
                    "The lump sum and death benefit allowance (LSDBA) of £1,073,100 is a separate limit covering both lump sums you take yourself and lump sum death benefits paid to your beneficiaries. For most people these limits are academic — a fund of around £1 million is required to approach the LSA (assuming a standard 25% PCLS calculation). But for those with very large pension funds — built up over decades, or through DB scheme commutation — the LSA is a real constraint worth planning around.",
                ],
            },
            {
                "heading": "Relevant UK earnings cap on personal contributions",
                "paragraphs": [
                    "Personal pension contributions are also capped at 100% of your relevant UK earnings in the tax year. Relevant earnings include employment income and self-employment profits, but not dividends, rental income or interest. If you earn £40,000 in a year, you can only contribute £40,000 (or £60,000 minus employer contributions, whichever is lower) to receive tax relief. This cap applies to personal contributions only — employer contributions are not subject to the earnings cap, though they still count towards the annual allowance.",
                ],
            },
        ],
        "sources": [
            {"label": "HMRC: Annual allowance for pension savings", "url": "https://www.gov.uk/pension-annual-allowance"},
            {"label": "HMRC: Lump sum allowance", "url": "https://www.gov.uk/hmrc-internal-manuals/pensions-tax-manual/ptm088100"},
            {"label": "HMRC: Money Purchase Annual Allowance", "url": "https://www.gov.uk/money-purchase-annual-allowance"},
        ],
    },
]

BLOG_BY_SLUG = {p["slug"]: p for p in BLOG_POSTS}


@app.route("/blog")
def blog_index():
    return render_template("blog_index.html", **_ctx(
        title="Pension Tax Relief Guides UK 2026/27 | PensionTaxReliefCalculator",
        meta_description="In-depth UK pension tax relief guides covering annual allowance, carry forward, higher-rate relief, self-employed pensions and salary sacrifice.",
        canonical_url=SITE_URL + "/blog",
        posts=BLOG_POSTS,
        breadcrumbs=[
            {"name": "Home", "url": SITE_URL + "/"},
            {"name": "Blog", "url": SITE_URL + "/blog"},
        ],
    ))


@app.route("/blog/<slug>")
def blog_post_view(slug: str):
    post = BLOG_BY_SLUG.get(slug)
    if not post:
        abort(404)
    return render_template("blog_post.html", **_ctx(
        title=post["title"],
        meta_description=post["description"],
        canonical_url=SITE_URL + f"/blog/{slug}",
        post=post,
        examples=[],
        article_faqs=post.get("faqs", []),
        reference_facts=None,
        sources=post.get("sources", []),
        breadcrumbs=[
            {"name": "Home", "url": SITE_URL + "/"},
            {"name": "Blog", "url": SITE_URL + "/blog"},
            {"name": post["title"], "url": SITE_URL + f"/blog/{slug}"},
        ],
    ))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=False)
