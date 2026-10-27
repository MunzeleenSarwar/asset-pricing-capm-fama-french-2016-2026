# Explaining Technology Stock Returns

Sample: January 2016 to August 2026, 128 months per stock, 640 stock-months.
Report built October 2026. The project is named for its data period.
August 2026 is the latest complete month in the French factor files
available at build time. October 2026 is an incomplete month and its
French factors are not published yet.

## Question

Does the Fama-French three-factor model explain the monthly excess returns of
large United States technology stocks better than the CAPM, and do
profitability, investment and momentum add anything on top of it?

## Answer in brief

Yes, for this sample, with limits. The three-factor model fits better than
the CAPM for every stock, and the gain is largest for Microsoft, where
adjusted R-squared rises from 0.387 to 0.559. The value factor is negative
for every stock, which fits a growth profile. The size factor is negative
for every stock, which fits a large company profile, but it is significant
only for Microsoft and Oracle in the three-factor model.

Adding profitability, investment and momentum does not change the main
result. Momentum is not significant for any stock at the 5 percent level.
Profitability is significant for Apple, Microsoft and Oracle in the
five-factor model, investment for no stock.

The joint test rejects zero alpha for all five stocks together under every
model, including the five-factor and Carhart models. A large part of these
returns is still not explained by the factors tested here. That leftover
alpha should not be read as proof of skill or mispricing.

## Sample

- Stocks: Apple (AAPL), Broadcom (AVGO), Microsoft (MSFT), Nvidia (NVDA),
  Oracle (ORCL)
- Frequency: monthly
- Period: January 2016 to August 2026, 128 months per stock,
  640 stock-months in total
- Returns: simple monthly returns from Yahoo Finance daily adjusted
  closing prices, reduced to month-end prices. Adjusted prices reflect
  splits and distributions.
- Factors: Kenneth R. French Data Library, Dartmouth. Three-factor file,
  five-factor 2x3 file, and momentum file. All returns and factors are in
  percentage points. Each excess return is the stock return minus the
  monthly risk-free rate from the French files.
- Data downloaded: October 2026. Factor and price vintages change over
  time, so a rerun on a later date can differ slightly from the numbers
  in the report.

## Models

| Model | Factors |
| --- | --- |
| CAPM | Market excess return |
| Fama-French three-factor (FF3) | Market, SMB, HML |
| Fama-French five-factor (FF5) | Market, SMB, HML, RMW, CMA |
| Carhart | Market, SMB, HML, MOM |

A negative SMB loading means the stock behaves more like a large company
stock. A negative HML loading means the stock behaves more like a growth
stock than a value stock.

Note on the five-factor model: the five-factor file builds SMB and HML on
a 2x3 sort, while the three-factor file uses a different sort. The
five-factor model therefore uses its own market, size and value factors
throughout and never mixes the two sets.

## Headline results

### CAPM and three-factor estimates

| Stock | CAPM alpha | CAPM beta | CAPM adj. R2 | FF3 alpha | FF3 beta | FF3 SMB | FF3 HML | FF3 adj. R2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AAPL | 0.941 | 1.124 | 0.410 | 0.884 | 1.159 | -0.230 | -0.479 | 0.465 |
| AVGO | 1.791 | 1.140 | 0.279 | 1.748 | 1.168 | -0.193 | -0.503 | 0.312 |
| MSFT | 0.886 | 0.914 | 0.387 | 0.693 | 1.024 | -0.636 | -0.548 | 0.559 |
| NVDA | 3.233 | 1.773 | 0.354 | 3.218 | 1.789 | -0.181 | -1.025 | 0.433 |
| ORCL | 0.223 | 1.199 | 0.293 | -0.046 | 1.350 | -0.841 | -0.434 | 0.366 |

Alphas and loadings are in percentage points per month. Full estimates,
standard errors and p-values are in `tables/`.

### Model fit

The three-factor model raises adjusted R-squared for every stock:
Apple +0.055, Broadcom +0.033, Microsoft +0.172, Nvidia +0.079,
Oracle +0.073. Nested F-tests reject the CAPM restrictions for every
stock at the 5 percent level. Adding momentum does not improve fit
for any stock at the 5 percent level, although Microsoft is close,
with a p-value of 0.057.

### Robustness checks

- **Robust standard errors.** HC1 and Newey-West (lag 3) standard errors
  for the three-factor model give the same significance pattern as OLS.
  No main conclusion depends on the standard error choice.
- **Joint alpha test (GRS).** The null that all five alphas are zero is
  rejected under every model: CAPM F = 2.919 (p = 0.016), FF3
  F = 3.434 (p = 0.006), FF5 F = 3.387 (p = 0.007), Carhart
  F = 3.411 (p = 0.007).
- **Subperiods.** Splitting the three-factor model at the end of 2019
  changes the picture. Nvidia's market beta falls from 2.365 to 1.615
  and its HML loading becomes much more negative, from -0.368 to -1.199.
  Oracle's HML loading changes sign, from 0.063 to -0.557. A single set
  of loadings for the full sample is a summary, not a stable
  description.
- **Rolling betas.** 36-month rolling CAPM betas range from about 0.90
  to 2.58 for Nvidia, 0.24 to 1.55 for Broadcom, and 0.66 to 2.24 for
  Oracle. At August 2026, the latest rolling betas are about 2.24 for
  Oracle, 1.55 for Broadcom, 1.87 for Nvidia, 1.11 for Microsoft and
  0.80 for Apple. Microsoft is the most stable of the five.
- **Out of sample.** Models fitted on 2016-2020 and tested on 2021 to
  August 2026 favour the three-factor model for Microsoft, Nvidia,
  Oracle and Broadcom, but not for Apple (0.349 versus 0.401 for the CAPM).
  Out-of-sample support is real but not uniform.
- **Influence.** Dropping months with a Cook's distance above 4/128
  lowers every alpha except Oracle, which becomes more negative:
  Nvidia from 3.218 to 2.569, Broadcom from 1.748 to 1.086, Apple from
  0.884 to 0.590, Microsoft from 0.693 to 0.518, Oracle from -0.046 to
  -0.242. No value loading changes sign.
- **Diagnostics.** Breusch-Pagan tests do not reject homoskedasticity
  for any CAPM or three-factor regression. Breusch-Godfrey tests do not
  find significant serial correlation at the 5 percent level.
  Residual normality is rejected for most models, which is one reason
  robust standard errors are reported. Variance inflation factors are
  between 1.01 and 1.14 for the three-factor model.

### What changed from the December 2025 sample

Extending the sample by eight months changes Oracle and Microsoft most.
Oracle alpha changes sign, from 0.245 to -0.046 percent per month, and
its cumulative growth falls from about 6.2 to 4.8. Microsoft fit falls,
with CAPM adjusted R-squared from 0.466 to 0.387 and three-factor fit
from 0.638 to 0.559, as its monthly volatility rises. Nvidia and
Broadcom alphas stay large and significant. The main conclusion,
that the three-factor model beats the CAPM but does not fully explain
these returns, is unchanged.

## How to run it

The main script is R. Run it from the project root directory, in RStudio
or with `Rscript scripts/asset_pricing_analysis.R`. It downloads the
prices and factors, builds the dataset, estimates all four models, and
writes every table and figure. It stops if any stock does not have
exactly 128 months, or if any factor value is missing after the merge.
It downloads to 1 September 2026 so that 31 August 2026 is included as
the month-end, while the analysis sample ends on 31 August 2026.

Required R packages: quantmod, xts, zoo, dplyr, tidyr, ggplot2,
lubridate, lmtest, sandwich, broom, modelsummary, tseries,
moments, readr, purrr. The car package is deliberately not required:
its dependency Deriv needs R 4.5 or later, and variance inflation
factors are calculated directly in the script instead.

Install them once before running. The script does not install packages
itself. When the R script is run, package versions are saved to
`results/session_info.txt`.

The August 2026 run in this folder was produced with
`scripts/analysis_aug2026.py`, which mirrors the R script, because R
was not installed on the work machine after a VM restart in October
2026. The report was built with `scripts/build_report_aug2026.py`.
R remains the main project language, and the R script was updated to
the same August 2026 sample.

Note on AIC and BIC: R counts the residual variance as a parameter, so
AIC and BIC here follow the R convention.

## Files

- `Asset_Pricing_Technology_Stocks_Report.pdf` - report, 8 pages,
  with a detailed executive summary, all three graphs, three heatmaps
  (adjusted R-squared, three-factor loadings, rolling betas), and
  short bold headings only
- `scripts/asset_pricing_analysis.R` - main analysis script, updated
  to August 2026
- `scripts/analysis_aug2026.py` - Python run that produced the current
  data, tables, figures and report numbers, mirroring the R script
- `scripts/build_report_aug2026.py` - report builder
- `data/` - monthly stock returns, French factors, final dataset
  (640 rows, one per stock-month)
- `tables/` - regression results, model comparison, F-tests,
  diagnostics, robust standard errors, GRS tests, subperiods,
  rolling betas, out-of-sample results, Cook's distance sensitivity
- `figures/` - cumulative growth (log scale), adjusted R-squared
  comparison, rolling CAPM betas, and heatmaps for adjusted R-squared,
  three-factor loadings and rolling betas

## Limitations

- The sample is five large companies that performed very well over
  this period. Nvidia grows about 274.9 times and Broadcom about 33.5
  times from a starting value of 1. Results do not generalise to
  technology stocks in general, to smaller companies, to other sectors,
  or to other countries.
- Loadings are assumed constant in the main models, and the subperiod
  and rolling beta results show that assumption does not hold well,
  especially for Nvidia and Oracle.
- The market factor is the French United States market factor, not a
  technology index. Part of what is called alpha may reflect technology
  sector movement that the broad market factor does not capture.
- Only 128 months per stock are available, so subperiod estimates use
  48 and 80 months and carry wide uncertainty.
- No costs, taxes or trading rules are included. Past factor loadings
  do not predict future returns.

This project is an analysis of past returns. It is not investment advice.

## Sources

- Yahoo Finance, daily adjusted closing prices for AAPL, AVGO, MSFT,
  NVDA, ORCL.
- Kenneth R. French Data Library, Dartmouth:
  F-F Research Data Factors, F-F Research Data 5 Factors 2x3,
  F-F Momentum Factor.
  https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html

## References

- Fama, E. and French, K. (1993). Common risk factors in the returns on
  stocks and bonds. Journal of Financial Economics, 33, 3-56.
- Fama, E. and French, K. (2015). A five-factor asset pricing model.
  Journal of Financial Economics, 116, 1-22.
- Carhart, M. (1997). On persistence in mutual fund performance.
  Journal of Finance, 52, 57-82.
- Gibbons, M., Ross, S. and Shanken, J. (1989). A test of the efficiency
  of a given portfolio. Econometrica, 57, 1121-1152.
- Sharpe, W. (1964). Capital asset prices: A theory of market equilibrium
  under conditions of risk. Journal of Finance, 19, 425-442.
