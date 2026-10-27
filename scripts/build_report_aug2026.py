"""Build the August 2026 report.
Formatting rule, kept from the previous rebuild: bold is used only for
short headings, the title, and short table headers. No paragraph of body
text is bold, and no heading is a full sentence. Body text is regular,
plain language, no first person. Author name appears only at the top.
This version restores all three graphs that were cut from the short
3-page version: cumulative growth, adjusted R-squared comparison, and
rolling CAPM betas. The executive summary still comes first.
"""
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

BASE = "/home/hatch/workspace/your_files/asset-pricing-capm-fama-french-2016-2026"
OUT = f"{BASE}/Asset_Pricing_Technology_Stocks_Report.pdf"
BLACK = HexColor("#000000")
GREY = HexColor("#444444")

styles = getSampleStyleSheet()
body = ParagraphStyle("body", parent=styles["Normal"], fontName="Times-Roman",
                      fontSize=11, leading=15.5, textColor=BLACK, alignment=TA_JUSTIFY, spaceAfter=7)
heading = ParagraphStyle("heading", parent=styles["Normal"], fontName="Times-Bold",
                         fontSize=12.5, leading=15, textColor=BLACK, spaceBefore=14, spaceAfter=5)
title_s = ParagraphStyle("title", parent=styles["Normal"], fontName="Times-Bold",
                         fontSize=20, leading=23, textColor=BLACK, spaceAfter=6)
subtitle = ParagraphStyle("subtitle", parent=styles["Normal"], fontName="Times-Roman",
                          fontSize=12, leading=16, textColor=BLACK, spaceAfter=3)
note = ParagraphStyle("note", parent=styles["Normal"], fontName="Times-Italic",
                      fontSize=9, leading=12, textColor=GREY, spaceBefore=3, spaceAfter=10)
cell = ParagraphStyle("cell", parent=styles["Normal"], fontName="Times-Roman",
                      fontSize=9, leading=11, textColor=BLACK)
cell_c = ParagraphStyle("cellc", parent=cell, alignment=1)
cell_b = ParagraphStyle("cellb", parent=styles["Normal"], fontName="Times-Bold",
                        fontSize=9, leading=11, textColor=BLACK, alignment=1)

def P(t, s=body): return Paragraph(t, s)
def star(p):
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "+" if p < 0.10 else ""

def make_table(header, rows, widths):
    data = [[Paragraph(h, cell_b) for h in header]]
    for r in rows:
        data.append([Paragraph(str(c), cell_c) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, BLACK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t

mc = pd.read_csv(f"{BASE}/tables/model_comparison.csv")
ff3 = pd.read_csv(f"{BASE}/tables/ff3_results.csv")

order = ["CAPM", "FF3", "FF5", "Carhart"]
fit_rows = []
for tk in ["AAPL", "AVGO", "MSFT", "NVDA", "ORCL"]:
    row = [tk]
    for m in order:
        v = mc[(mc["Stock"] == tk) & (mc["Model"] == m)]["Adj_R2"].iloc[0]
        row.append(f"{v:.3f}")
    fit_rows.append(row)

ff3_rows = []
for _, r in ff3.iterrows():
    ff3_rows.append([r["Stock"], f"{r['Alpha']:.3f}{star(r['Alpha_p'])}",
                     f"{r['MKT_RF']:.3f}{star(r['MKT_RF_p'])}",
                     f"{r['SMB']:.3f}{star(r['SMB_p'])}",
                     f"{r['HML']:.3f}{star(r['HML_p'])}",
                     f"{r['Adj_R2']:.3f}"])

story = []
story.append(P("Explaining Technology Stock Returns", title_s))
story.append(P("Does the Fama-French model explain large technology stocks better than the CAPM?", subtitle))
story.append(P("Munzeleen Sarwar", subtitle))
story.append(P("Monthly data, January 2016 to August 2026. Report built October 2026.", subtitle))
story.append(Spacer(1, 8))

story.append(P("Executive summary", heading))
story.append(P("<b>Objective and scope:</b> This report tests whether the Fama-French three-factor model explains the monthly excess returns of five large United States technology stocks better than the Capital Asset Pricing Model (CAPM), and whether profitability, investment and momentum add further explanatory power. The sample covers Apple, Broadcom, Microsoft, Nvidia and Oracle over January 2016 to August 2026, 128 monthly observations per stock and 640 stock-months in total. Excess return is defined as the monthly stock return minus the monthly risk-free rate. The sample is deliberately narrow: five large companies that performed strongly over this period. The results therefore describe these stocks in this period, and do not generalise to technology stocks in general, to smaller companies, or to other sectors."))
story.append(P("<b>Method:</b> Monthly returns are calculated from Yahoo Finance daily adjusted closing prices, reduced to month-end prices, and merged with factor data from the Kenneth R. French Data Library. Four models are estimated separately for each stock by ordinary least squares: the CAPM, using the market excess return only; the Fama-French three-factor model, adding size (SMB) and value (HML); the Fama-French five-factor model, adding profitability (RMW) and investment (CMA); and the Carhart model, adding momentum (MOM) to the three-factor model. The five-factor model uses its own market, size and value factors from the five-factor file, which are built on a different sort from the three-factor file, and the two sets are never mixed. Model performance is judged by adjusted R-squared, nested F-tests, and out-of-sample fit. Robustness is assessed with heteroskedasticity-robust (HC1) and Newey-West standard errors, a Gibbons-Ross-Shanken (GRS) joint test of all five alphas, subperiod estimates, 36-month rolling CAPM betas, an out-of-sample test, and a Cook's distance sensitivity check."))
story.append(P("<b>Main findings on fit:</b> The three-factor model improves fit over the CAPM for every stock. Adjusted R-squared rises from 0.410 to 0.465 for Apple, 0.279 to 0.312 for Broadcom, 0.387 to 0.559 for Microsoft, 0.354 to 0.433 for Nvidia, and 0.293 to 0.366 for Oracle. Microsoft shows the largest gain, although both its CAPM and three-factor fit are lower than in the December 2025 sample, reflecting higher monthly volatility in the extended sample. Nested F-tests reject the CAPM restrictions for every stock at the 5 percent level. The five-factor and Carhart models add almost nothing on top of the three-factor model. The highest adjusted R-squared in the full comparison is 0.587, for Microsoft under the five-factor model, against 0.559 under the three-factor model. Momentum is not significant for any stock at the 5 percent level, investment is not significant for any stock, and profitability is significant only for Apple, Microsoft and Oracle in the five-factor model."))
story.append(P("<b>Main findings on loadings and alphas:</b> Market loadings are positive and highly significant for every stock under the three-factor model, ranging from 1.024 for Microsoft to 1.789 for Nvidia. Size loadings are negative for every stock, consistent with large company stocks, but significant only for Microsoft and Oracle. Value loadings are negative for every stock and significant for all five, consistent with growth stocks, with the most negative loading for Nvidia at minus 1.025. Three-factor alphas, in percentage points per month, are 3.218 for Nvidia, 1.748 for Broadcom, 0.884 for Apple, 0.693 for Microsoft, and minus 0.046 for Oracle. Only the Nvidia and Broadcom alphas are significant at the 5 percent level. Oracle alpha changes sign relative to the December 2025 sample, from 0.245 to minus 0.046, and is not significant. The GRS test rejects the hypothesis that all five alphas are jointly zero under every model, with a three-factor statistic of 3.434 and a p-value of 0.006."))
story.append(P("<b>Robustness and interpretation:</b> The main result survives the robustness checks, but the loadings are not stable. In the subperiod split, Nvidia market beta falls from 2.365 in 2016 to 2019 to 1.615 in 2020 to 2026, while its value loading becomes much more negative, from minus 0.368 to minus 1.199. Oracle value loading changes sign, from 0.063 to minus 0.557. Rolling 36-month CAPM betas range from about 0.90 to 2.58 for Nvidia and 0.66 to 2.24 for Oracle, and at August 2026 the latest rolling betas are about 2.24 for Oracle, 1.87 for Nvidia, 1.55 for Broadcom, 1.11 for Microsoft and 0.80 for Apple. Out of sample, models fitted on 2016 to 2020 and tested on 2021 to August 2026 favour the three-factor model for Broadcom, Microsoft, Nvidia and Oracle, but not for Apple. Dropping influential months shrinks every alpha, for example Nvidia from 3.218 to 2.569, but does not change any value loading sign. The conclusion is therefore twofold. Size and value materially improve the explanation of these returns relative to the market alone, but even the best model leaves more than 40 percent of monthly variation unexplained for every stock, and the remaining alphas should not be interpreted as evidence of skill, mispricing, or a trading opportunity. No costs, taxes or trading rules are included in this analysis, and past loadings do not predict future returns."))

story.append(P("Question", heading))
story.append(P("Does the Fama-French three-factor model explain the monthly excess returns of Apple, Broadcom, Microsoft, Nvidia and Oracle better than the CAPM? Excess return means the stock return minus the risk-free rate for that month."))

story.append(P("Method", heading))
story.append(P("Daily adjusted closing prices from Yahoo Finance were reduced to month-end prices, and simple monthly returns were calculated from them. Adjusted prices reflect splits and distributions. Factor data come from the Kenneth R. French Data Library: the three-factor file, the five-factor file, and the momentum file. August 2026 is the latest complete month in those factor files. Each model was estimated separately for each stock by ordinary least squares. A negative size loading means a stock behaves more like a large company stock. A negative value loading means a stock behaves more like a growth stock than a value stock. The intercept in each regression is called alpha. It is the average monthly excess return left after the factors in the model are taken into account."))
story.append(P("Checks were added so the main result does not rest on one choice. Standard errors were also calculated with heteroskedasticity-robust and Newey-West methods. Loadings were checked in two subperiods, 2016 to 2019 and 2020 to 2026, and with 36-month rolling betas. Models fitted on 2016 to 2020 were tested on 2021 to August 2026. Months with a large influence on the results were dropped as a sensitivity check. A joint test was used for all five alphas together. Full numbers for every check are in the tables folder."))

story.append(P("Results", heading))
story.append(P("Figure 1 shows how much 1 invested in each stock would have grown. It is on a log scale, because Nvidia would otherwise hide the other lines. By August 2026, 1 invested at the start of 2016 would have grown to about 274.9 for Nvidia, 33.5 for Broadcom, 13.4 for Apple, 10.5 for Microsoft and 4.8 for Oracle. Oracle falls from about 6.2 at the end of 2025 to 4.8 by August 2026, which is part of why its results change in the longer sample."))
story.append(Image(f"{BASE}/figures/cumulative_growth.png", width=16.5*cm, height=9.2*cm))
story.append(P("Figure 1. Cumulative growth of 1 invested, on a log scale. The chart describes the sample. It is not a recommendation.", note))
story.append(P("Table 1 shows model fit. Higher adjusted R-squared means a better fit after allowing for the number of factors."))
story.append(make_table(["Stock", "CAPM", "FF3", "FF5", "Carhart"], fit_rows,
                        [3.0*cm, 3.2*cm, 3.2*cm, 3.2*cm, 3.2*cm]))
story.append(P("Table 1. Adjusted R-squared by model. FF3 is the three-factor model, FF5 is the five-factor model, and Carhart adds momentum to FF3.", note))
story.append(Image(f"{BASE}/figures/adjusted_r2_comparison.png", width=16.5*cm, height=9.2*cm))
story.append(P("Figure 2. Adjusted R-squared by model and stock. The three-factor model improves on the CAPM for every stock. The five-factor and Carhart models add almost nothing on top of it.", note))
story.append(P("Microsoft still shows the largest gain, from 0.387 under the CAPM to 0.559 under the three-factor model, but both values are lower than in the December 2025 sample, where they were 0.466 and 0.638. Microsoft became more volatile in the longer sample, with a monthly standard deviation of 6.61 percent, up from 5.89 percent, and a largest monthly gain of 24.58 percent. Nvidia gains from 0.354 to 0.433, Apple from 0.410 to 0.465, Oracle from 0.293 to 0.366, and Broadcom from 0.279 to 0.312. A formal test that size and value add nothing is rejected for every stock at the 5 percent level. Adding momentum does not improve fit for any stock at the 5 percent level, although Microsoft is close, with a p-value of 0.057."))
story.append(P("Table 2 shows the three-factor estimates. Stars show significance: + below 0.10, * below 0.05, ** below 0.01, *** below 0.001."))
story.append(make_table(["Stock", "Alpha", "Market", "Size", "Value", "Adj. R2"], ff3_rows,
                        [2.5*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.5*cm]))
story.append(P("Table 2. Three-factor estimates, in percentage points per month. Alpha is the intercept. Market, Size and Value are the loadings on the market, size and value factors.", note))
story.append(P("Market loadings are positive and highly significant for every stock. Nvidia has the highest market loading, at 1.789, and Oracle is now higher than before, at 1.350. Size loadings are negative for every stock, but significant only for Microsoft and Oracle. Value loadings are negative for every stock, and significant for all five. Nvidia has the most negative value loading, at minus 1.025. The pattern fits large growth companies."))
story.append(P("Alpha changes in the longer sample. It remains positive and significant for Broadcom and Nvidia, and largest for Nvidia, at 3.218 percent per month. Apple and Microsoft alphas are now only marginally significant, at 0.884 and 0.693 percent per month. Oracle alpha changes sign, from 0.245 percent per month in the December 2025 sample to minus 0.046 percent per month now, and is not significant. The five-factor and Carhart models do not remove the Nvidia and Broadcom alphas. Profitability is significant for Apple, Microsoft and Oracle in the five-factor model, investment is not significant for any stock, and momentum is not significant for any stock at the 5 percent level. The joint test rejects zero alpha for all five stocks together under every model, with a p-value of 0.006 under the three-factor model."))
story.append(P("Figure 3 shows why a single set of loadings for the full sample should be read with care. Rolling 36-month market betas move a great deal over time. Nvidia ranges from about 0.90 to 2.58, Oracle from about 0.66 to 2.24, and Broadcom from about 0.24 to 1.55. At August 2026, the latest rolling betas are about 2.24 for Oracle, 1.55 for Broadcom, 1.87 for Nvidia, 1.11 for Microsoft and 0.80 for Apple. Microsoft is the most stable of the five."))
story.append(Image(f"{BASE}/figures/rolling_capm_beta.png", width=16.5*cm, height=9.2*cm))
story.append(P("Figure 3. 36-month rolling CAPM betas. The dashed line is a beta of one. The first rolling window ends in December 2018.", note))
story.append(P("Other checks point the same way as before. Robust standard errors give the same significance pattern as ordinary standard errors for the three-factor model. In the subperiod split, Nvidia's market loading falls from 2.365 in 2016 to 2019 to 1.615 in 2020 to 2026, while its value loading becomes much more negative, from minus 0.368 to minus 1.199. Oracle's value loading changes sign, from 0.063 to minus 0.557. Out of sample, models fitted on 2016 to 2020 and tested on 2021 to August 2026 favour the three-factor model for Broadcom, Microsoft, Nvidia and Oracle, but not for Apple, where the CAPM scores 0.401 against 0.349 for the three-factor model. Dropping influential months shrinks every alpha, for example Nvidia from 3.218 to 2.569 and Broadcom from 1.748 to 1.086, and makes Oracle alpha more negative, from minus 0.046 to minus 0.242, but it does not change any value loading sign."))

story.append(P("Heatmaps", heading))
story.append(P("The same three results are shown again here as heatmaps, because colour makes the pattern across stocks easier to see at a glance. The numbers are printed on each cell, so the colour is a guide, not a replacement for the values."))
story.append(P("Figure 4 shows adjusted R-squared by stock and model. Every cell is on the same scale, so darker blue means a better fit. Microsoft is the darkest row, Broadcom the lightest, and the three-factor, five-factor and Carhart columns look almost the same."))
story.append(Image(f"{BASE}/figures/adj_r2_heatmap.png", width=15.5*cm, height=9.7*cm))
story.append(P("Figure 4. Adjusted R-squared heatmap. Darker blue means a better fit.", note))
story.append(P("Figure 5 shows the three-factor loadings. Blue is positive, red is negative, and white is near zero. Market loadings are blue for all five stocks, size and value loadings are red for all five, and Nvidia's alpha stands out in dark blue. Nvidia's alpha stretches the colour scale, so the smaller loadings look paler than they are."))
story.append(Image(f"{BASE}/figures/ff3_loadings_heatmap.png", width=15.5*cm, height=9.7*cm))
story.append(P("Figure 5. Three-factor loadings heatmap, in percentage points per month. The scale is centred on zero.", note))
story.append(P("Figure 6 shows rolling 36-month CAPM betas over time, with one row per stock and one column per rolling window. Red means a high beta, blue means a low beta. Nvidia is red early, cooler in the middle, and red again later. Oracle turns red at the right edge, in 2026. Microsoft stays in the middle range throughout."))
story.append(Image(f"{BASE}/figures/rolling_beta_heatmap.png", width=16.5*cm, height=8.2*cm))
story.append(P("Figure 6. Rolling beta heatmap. The first rolling window ends in December 2018 and the last ends in August 2026.", note))

story.append(P("What this does not prove", heading))
story.append(P("Three limits matter most. First, the sample is five large companies that rose strongly over this period. Results from such a sample do not generalise to technology stocks in general, to smaller companies, or to other sectors. Second, loadings are not stable, as Figure 3 shows. A single set of loadings for the full sample is a summary, not a stable description. Third, adjusted R-squared stays below 0.60 for every stock and below 0.50 for four of the five stocks. Most monthly variation is still stock-specific. No costs, taxes or trading rules are included, and past loadings do not predict future returns. This report is an analysis of past returns. It is not investment advice."))

story.append(P("Data and replication", heading))
story.append(P("The main script is scripts/asset_pricing_analysis.R. Run it from the project root. It downloads prices from Yahoo Finance and factors from the French Data Library, builds the dataset, estimates all four models, and writes the tables and figures. The script stops if any stock does not have exactly 128 months, or if any factor value is missing after the merge. The August 2026 run in this folder was produced with scripts/analysis_aug2026.py, which mirrors the R script, because R was not installed on the work machine after a VM restart in October 2026. The R script itself was updated to the same August 2026 sample, with the same end-date rule: download to 1 September 2026 so that 31 August 2026 is included as the month-end. Sources: Yahoo Finance daily adjusted prices for AAPL, AVGO, MSFT, NVDA and ORCL; Kenneth R. French Data Library, three-factor, five-factor 2x3, and momentum files, downloaded October 2026."))
story.append(P("References. Fama, E. and French, K. (1993). Common risk factors in the returns on stocks and bonds. Journal of Financial Economics, 33, 3-56. Fama, E. and French, K. (2015). A five-factor asset pricing model. Journal of Financial Economics, 116, 1-22. Carhart, M. (1997). On persistence in mutual fund performance. Journal of Finance, 52, 57-82. Gibbons, M., Ross, S. and Shanken, J. (1989). A test of the efficiency of a given portfolio. Econometrica, 57, 1121-1152. Sharpe, W. (1964). Capital asset prices: A theory of market equilibrium under conditions of risk. Journal of Finance, 19, 425-442.", note))

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2*cm, bottomMargin=2*cm,
                        title="Explaining Technology Stock Returns", author="Munzeleen Sarwar")
doc.build(story)
print("Wrote", OUT)
