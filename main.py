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
    ] + [(f"{SITE_URL}/pension-relief/{inc}","0.5","monthly") for inc in [20000, 25000, 30000, 35000, 40000, 45000, 50000, 60000, 75000, 100000, 120000, 150000]]
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

PENSION_INCOME_AMOUNTS = [20000, 25000, 30000, 35000, 40000, 45000, 50000, 60000, 75000, 100000, 120000, 150000]

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=False)
