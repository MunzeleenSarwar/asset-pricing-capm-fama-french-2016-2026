# ============================================================
# Explaining Technology Stock Returns:
# CAPM versus Fama-French Three-Factor, Five-Factor and Carhart Models
#
# Improved version of an earlier analysis. Changes from the original:
#   - No student ID, course code or assignment framing in outputs.
#   - No install.packages() call inside the script. Install packages
#     once from the list in README.md, then run this script.
#   - No duplicated diagnostic block. Section numbers run in order.
#   - The script stops if any stock does not have exactly 128 months,
#     or if any merged factor value is missing, instead of dropping
#     rows silently.
#   - Added: Fama-French five-factor model, Carhart momentum model,
#     heteroskedasticity-robust (HC1) and Newey-West (lag 3) standard
#     errors, a joint GRS test of all five alphas, subperiod estimates,
#     36-month rolling CAPM betas, an out-of-sample check, and a
#     Cook's distance sensitivity check.
#   - sessionInfo() is saved so the run can be reproduced.
#   - The car package is NOT required. Its dependency Deriv needs
#     R >= 4.5, which blocks the script on R 4.3. Variance inflation
#     factors are calculated directly below as 1 / (1 - R-squared),
#     which is exactly what car::vif() returns for an OLS model.
#
# Run from the project root directory. Inputs are downloaded fresh
# from Yahoo Finance and the Kenneth R. French Data Library.
# Outputs go to data/, tables/ and figures/.
# Sample: monthly, January 2016 to August 2026 (128 months).
# August 2026 is the latest complete month in the French factor files
# available at the time of this update. October 2026 is not used:
# it is an incomplete month and its French factors are not published yet.
# All returns and factors are in percentage points.
#
# August 2026 update: the sample end, all month counts, the second
# subperiod label, the out-of-sample test period and the Cook's
# distance threshold were all moved from December 2025 / 120 months
# to August 2026 / 128 months. Nothing else in the method changed.
# ============================================================

required_packages <- c(
  "quantmod", "xts", "zoo", "dplyr", "tidyr", "ggplot2", "lubridate",
  "lmtest", "sandwich", "broom", "modelsummary", "tseries",
  "moments", "readr", "purrr"
)
missing_packages <- required_packages[!(required_packages %in% installed.packages()[, "Package"])]
if (length(missing_packages) > 0) {
  stop("Install these packages first, then rerun: ",
       paste(missing_packages, collapse = ", "))
}
invisible(lapply(required_packages, library, character.only = TRUE))

# ---- 1. Settings ------------------------------------------------
tickers <- c("AAPL", "AVGO", "MSFT", "NVDA", "ORCL")
start_date <- as.Date("2015-12-01")   # one extra month, so Jan 2016 returns exist
# Download one day past the sample end. quantmod/Yahoo treats the
# `to` date as excluding the final session, so ending the download on
# the last sample day would use the previous trading day as the
# month-end and would misstate that month's return for every stock.
# The analysis sample below still ends on 2026-08-31, so no
# September 2026 return enters the analysis.
end_date <- as.Date("2026-09-01")
analysis_start <- as.Date("2016-01-01")
analysis_end <- as.Date("2026-08-31")

dir.create("data", showWarnings = FALSE)
dir.create("tables", showWarnings = FALSE)
dir.create("figures", showWarnings = FALSE)
dir.create("results", showWarnings = FALSE)

# ---- 2. Download stock prices -----------------------------------
getSymbols(tickers, src = "yahoo", from = start_date, to = end_date,
           auto.assign = TRUE, warnings = FALSE)

get_monthly_adjusted <- function(ticker) {
  monthly_price <- to.monthly(Ad(get(ticker)), indexAt = "lastof", OHLC = FALSE)
  colnames(monthly_price) <- ticker
  monthly_price
}
monthly_prices_xts <- do.call(merge, lapply(tickers, get_monthly_adjusted))

# Simple monthly percentage returns, restricted to the analysis sample.
# stats::lag is used explicitly: dplyr also defines lag(), and loading
# dplyr after xts otherwise masks it for xts objects.
monthly_returns_xts <- na.omit(100 * (monthly_prices_xts / stats::lag(monthly_prices_xts) - 1))
monthly_returns_xts <- monthly_returns_xts[paste0(analysis_start, "/", analysis_end)]
stock_returns_wide <- data.frame(Date = as.Date(index(monthly_returns_xts)),
                                 coredata(monthly_returns_xts))
names(stock_returns_wide) <- c("Date", tickers)
stopifnot(nrow(stock_returns_wide) == 128, !anyNA(stock_returns_wide))
write.csv(stock_returns_wide, "data/monthly_stock_returns_wide.csv", row.names = FALSE)

# ---- 3. Download and clean French factor data -------------------
# Helper: read one French ZIP file and keep only monthly (YYYYMM) rows.
read_french_zip <- function(url, new_names) {
  zip_file <- tempfile(fileext = ".zip")
  extract_dir <- tempfile()
  dir.create(extract_dir)
  download.file(url, destfile = zip_file, mode = "wb", quiet = TRUE)
  unzip(zip_file, exdir = extract_dir)
  csv_file <- list.files(extract_dir, pattern = "\\.CSV$|\\.csv$", full.names = TRUE)[1]
  lines <- readLines(csv_file, warn = FALSE)
  monthly_lines <- lines[grepl("^\\s*[0-9]{6}\\s*,", lines)]
  raw <- do.call(rbind, strsplit(monthly_lines, split = ","))
  out <- as.data.frame(raw, stringsAsFactors = FALSE)[, seq_along(new_names)]
  names(out) <- new_names
  out <- out %>%
    mutate(across(everything(), trimws)) %>%
    mutate(across(-YYYYMM, as.numeric),
           Date = ceiling_date(as.Date(paste0(YYYYMM, "01"), format = "%Y%m%d"),
                               unit = "month") - days(1)) %>%
    filter(Date >= analysis_start, Date <= analysis_end) %>%
    select(-YYYYMM)
  out
}

ff3 <- read_french_zip(
  "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip",
  c("YYYYMM", "MKT_RF", "SMB", "HML", "RF"))
ff5 <- read_french_zip(
  "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip",
  c("YYYYMM", "MKT_RF5", "SMB5", "HML5", "RMW", "CMA", "RF5"))
mom <- read_french_zip(
  "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_CSV.zip",
  c("YYYYMM", "MOM"))

# Note: the five-factor file builds SMB and HML on a 2x3 sort, while the
# three-factor file uses a different sort. FF5 therefore uses its own
# MKT_RF5, SMB5 and HML5 throughout, and is never mixed with FF3 factors.
# RF and RF5 are the same series in this sample; the check below confirms it.
stopifnot(isTRUE(all.equal(ff3$RF, ff5$RF5)))
factors <- ff3 %>% left_join(ff5 %>% select(-RF5), by = "Date") %>% left_join(mom, by = "Date")
stopifnot(nrow(factors) == 128, !anyNA(factors))
write.csv(factors, "data/fama_french_factors.csv", row.names = FALSE)

# ---- 4. Build the analysis dataset ------------------------------
analysis_data <- stock_returns_wide %>%
  mutate(YearMonth = format(Date, "%Y-%m")) %>%
  pivot_longer(cols = all_of(tickers), names_to = "Ticker", values_to = "Stock_Return") %>%
  left_join(factors %>% mutate(YearMonth = format(Date, "%Y-%m")) %>% select(-Date),
            by = "YearMonth") %>%
  mutate(Excess_Return = Stock_Return - RF)
stopifnot(nrow(analysis_data) == 640, !anyNA(analysis_data))
stopifnot(all(analysis_data %>% count(Ticker) %>% pull(n) == 128))
write.csv(analysis_data, "data/final_asset_pricing_dataset.csv", row.names = FALSE)

# ---- 5. Descriptive statistics ----------------------------------
descriptive_statistics <- analysis_data %>%
  group_by(Ticker) %>%
  summarise(Observations = n(), Mean_Return = mean(Stock_Return),
            SD = sd(Stock_Return), Minimum = min(Stock_Return),
            Maximum = max(Stock_Return), Mean_Excess_Return = mean(Excess_Return),
            .groups = "drop")
write.csv(descriptive_statistics, "tables/descriptive_statistics.csv", row.names = FALSE)

factor_statistics <- factors %>%
  summarise(across(c(MKT_RF, SMB, HML, RF, RMW, CMA, MOM),
                   list(Mean = mean, SD = sd, Minimum = min, Maximum = max)))
write.csv(factor_statistics, "tables/factor_descriptive_statistics.csv", row.names = FALSE)
write.csv(round(cor(factors %>% select(MKT_RF, SMB, HML, RF)), 3),
          "tables/factor_correlation_matrix.csv")

# ---- 6. Estimate the four models --------------------------------
fit_models <- function(formula) {
  analysis_data %>% split(.$Ticker) %>% lapply(function(d) lm(formula, data = d))
}
capm_models <- fit_models(Excess_Return ~ MKT_RF)
ff3_models <- fit_models(Excess_Return ~ MKT_RF + SMB + HML)
ff5_models <- fit_models(Excess_Return ~ MKT_RF5 + SMB5 + HML5 + RMW + CMA)
carhart_models <- fit_models(Excess_Return ~ MKT_RF + SMB + HML + MOM)

modelsummary(capm_models, output = "tables/capm_ols_results.html",
             title = "CAPM Regression Results", stars = TRUE, statistic = "({std.error})")
modelsummary(ff3_models, output = "tables/fama_french_ols_results.html",
             title = "Fama-French Three-Factor Regression Results", stars = TRUE,
             statistic = "({std.error})")

# ---- 7. Model fit comparison ------------------------------------
extract_fit <- function(model, ticker, model_name) {
  s <- summary(model)
  data.frame(Ticker = ticker, Model = model_name, Observations = nobs(model),
             R_Squared = s$r.squared, Adjusted_R_Squared = s$adj.r.squared,
             Residual_Standard_Error = s$sigma, AIC = AIC(model), BIC = BIC(model))
}
model_comparison <- bind_rows(
  lapply(names(capm_models), function(t) extract_fit(capm_models[[t]], t, "CAPM")),
  lapply(names(ff3_models), function(t) extract_fit(ff3_models[[t]], t, "Fama-French")),
  lapply(names(ff5_models), function(t) extract_fit(ff5_models[[t]], t, "Fama-French 5")),
  lapply(names(carhart_models), function(t) extract_fit(carhart_models[[t]], t, "Carhart")))
write.csv(model_comparison, "tables/model_comparison.csv", row.names = FALSE)

# ---- 8. Nested F-tests ------------------------------------------
f_test <- function(restricted, unrestricted) {
  test <- anova(restricted, unrestricted)
  data.frame(F_Statistic = test$F[2], P_Value = test$`Pr(>F)`[2])
}
model_f_tests <- bind_rows(lapply(tickers, function(t) {
  bind_rows(
    f_test(capm_models[[t]], ff3_models[[t]]) %>% mutate(Ticker = t, Test = "CAPM vs FF3"),
    f_test(ff3_models[[t]], carhart_models[[t]]) %>% mutate(Ticker = t, Test = "FF3 vs Carhart")
  )
}))
write.csv(model_f_tests, "tables/model_f_tests.csv", row.names = FALSE)

# ---- 9. Diagnostics ---------------------------------------------
# One block per test, each written to its own file. The original script
# repeated the Breusch-Pagan block and never wrote the Breusch-Godfrey
# results to a file; both problems are fixed here.
diagnostic_for <- function(models, test_fun) {
  bind_rows(lapply(tickers, function(t) {
    test <- test_fun(models[[t]])
    data.frame(Ticker = t, Statistic = as.numeric(test$statistic), P_Value = test$p.value)
  }))
}
bp_capm <- diagnostic_for(capm_models, bptest) %>% mutate(Model = "CAPM")
bp_ff3 <- diagnostic_for(ff3_models, bptest) %>% mutate(Model = "Fama-French")
write.csv(bind_rows(bp_capm, bp_ff3), "tables/breusch_pagan_results.csv", row.names = FALSE)

bg_capm <- diagnostic_for(capm_models, function(m) bgtest(m, order = 3)) %>% mutate(Model = "CAPM")
bg_ff3 <- diagnostic_for(ff3_models, function(m) bgtest(m, order = 3)) %>% mutate(Model = "Fama-French")
write.csv(bind_rows(bg_capm, bg_ff3), "tables/breusch_godfrey_results.csv", row.names = FALSE)

jb_capm <- diagnostic_for(capm_models, function(m) jarque.bera.test(residuals(m))) %>% mutate(Model = "CAPM")
jb_ff3 <- diagnostic_for(ff3_models, function(m) jarque.bera.test(residuals(m))) %>% mutate(Model = "Fama-French")
write.csv(bind_rows(jb_capm, jb_ff3), "tables/jarque_bera_results.csv", row.names = FALSE)

# VIF for each regressor: 1 / (1 - R-squared) from regressing that
# variable on the other regressors. Identical for every stock here
# because the regressors are the same factor series for all stocks.
vif_for_model <- function(model) {
  vars <- names(coef(model))[-1]
  X <- model.matrix(model)[, vars, drop = FALSE]
  sapply(vars, function(v) {
    others <- X[, setdiff(vars, v), drop = FALSE]
    fit <- lm(X[, v] ~ others)
    1 / (1 - summary(fit)$r.squared)
  })
}
vif_results <- bind_rows(lapply(tickers, function(t) {
  v <- vif_for_model(ff3_models[[t]])
  data.frame(Ticker = t, Variable = names(v), VIF = as.numeric(v))
}))
write.csv(vif_results, "tables/vif_results.csv", row.names = FALSE)

# ---- 10. Robust standard errors for the three-factor model ------
# sandwich is loaded in the original script but never used. Here HC1
# (heteroskedasticity-robust) and Newey-West (lag 3) errors are reported
# next to the OLS errors, so a reader can see whether any conclusion
# depends on the standard-error choice.
robust_se <- bind_rows(lapply(tickers, function(t) {
  m <- ff3_models[[t]]
  broom::tidy(m) %>%
    mutate(Ticker = t, OLS_SE = std.error,
           HC1_SE = sqrt(diag(vcovHC(m, type = "HC1"))),
           NW3_SE = sqrt(diag(NeweyWest(m, lag = 3, prewhite = FALSE)))) %>%
    select(Ticker, Term = term, Estimate = estimate, OLS_SE, HC1_SE, NW3_SE, P_Value = p.value)
}))
write.csv(robust_se, "tables/ff3_robust_se.csv", row.names = FALSE)

# ---- 11. Joint GRS test of all five alphas ----------------------
# GRS statistic: (T - N - K) / N * (alpha' Sigma^-1 alpha) /
# (1 + fbar' Omega^-1 fbar), distributed F(N, T - N - K) under the null
# that every alpha is zero. Sigma is the residual covariance matrix
# with divisor (T - K - 1); Omega is the factor covariance matrix.
grs_test <- function(models, factor_matrix) {
  alphas <- sapply(models, function(m) coef(m)[1])
  resid_mat <- sapply(models, residuals)
  T <- nrow(resid_mat); N <- ncol(resid_mat); K <- ncol(factor_matrix)
  Sigma <- crossprod(resid_mat) / (T - K - 1)
  fbar <- colMeans(factor_matrix)
  Omega <- cov(factor_matrix) * (T - 1) / T  # population (divisor T) version
  stat <- (T - N - K) / N * (t(alphas) %*% solve(Sigma) %*% alphas) /
    as.numeric(1 + t(fbar) %*% solve(Omega) %*% fbar)
  data.frame(GRS_F = as.numeric(stat), P_Value = pf(stat, N, T - N - K, lower.tail = FALSE),
             df1 = N, df2 = T - N - K)
}
factor_wide <- factors %>% select(MKT_RF, SMB, HML)
grs_results <- bind_rows(
  grs_test(capm_models, as.matrix(factors$MKT_RF)) %>% mutate(Model = "CAPM"),
  grs_test(ff3_models, as.matrix(factor_wide)) %>% mutate(Model = "FF3"),
  grs_test(ff5_models, as.matrix(factors %>% select(MKT_RF5, SMB5, HML5, RMW, CMA))) %>% mutate(Model = "FF5"),
  grs_test(carhart_models, as.matrix(factors %>% select(MKT_RF, SMB, HML, MOM))) %>% mutate(Model = "Carhart"))
write.csv(grs_results, "tables/grs_joint_alpha_tests.csv", row.names = FALSE)

# ---- 12. Subperiod estimates (FF3) -------------------------------
subperiod_fit <- function(data_subset, label) {
  bind_rows(lapply(tickers, function(t) {
    m <- lm(Excess_Return ~ MKT_RF + SMB + HML,
            data = data_subset %>% filter(Ticker == t))
    broom::tidy(m) %>% mutate(Ticker = t, Period = label) %>%
      select(Period, Ticker, Term = term, Estimate = estimate, P_Value = p.value)
  }))
}
ff3_subperiods <- bind_rows(
  subperiod_fit(analysis_data %>% filter(Date < as.Date("2020-01-01")), "2016-2019"),
  subperiod_fit(analysis_data %>% filter(Date >= as.Date("2020-01-01")), "2020-2026"))
write.csv(ff3_subperiods, "tables/ff3_subperiods.csv", row.names = FALSE)

# ---- 13. Rolling 36-month CAPM betas ----------------------------
rolling_beta <- bind_rows(lapply(tickers, function(t) {
  d <- analysis_data %>% filter(Ticker == t) %>% arrange(Date)
  betas <- sapply(36:nrow(d), function(i) {
    coef(lm(Excess_Return ~ MKT_RF, data = d[(i - 35):i, ]))[2]
  })
  data.frame(Date = d$Date[36:nrow(d)], Ticker = t, Rolling_beta_36m = betas)
}))
write.csv(rolling_beta, "tables/rolling_capm_beta_36m.csv", row.names = FALSE)

# ---- 14. Out-of-sample check ------------------------------------
# Fit on 2016-2020, predict 2021 to August 2026 (68 months).
# Out-of-sample R-squared is
# 1 - SSE / sum(actual excess returns squared), so a model that only
# predicts the mean excess return scores zero, and a worse model scores
# below zero. This is not a trading test: no costs are included.
oos <- bind_rows(lapply(tickers, function(t) {
  train <- analysis_data %>% filter(Ticker == t, Date < as.Date("2021-01-01"))
  test <- analysis_data %>% filter(Ticker == t, Date >= as.Date("2021-01-01"))
  bind_rows(
    { m <- lm(Excess_Return ~ MKT_RF, data = train)
      pred <- predict(m, newdata = test)
      data.frame(Ticker = t, Model = "CAPM",
                 OOS_R2 = 1 - sum((test$Excess_Return - pred)^2) / sum(test$Excess_Return^2)) },
    { m <- lm(Excess_Return ~ MKT_RF + SMB + HML, data = train)
      pred <- predict(m, newdata = test)
      data.frame(Ticker = t, Model = "FF3",
                 OOS_R2 = 1 - sum((test$Excess_Return - pred)^2) / sum(test$Excess_Return^2)) }
  )
}))
write.csv(oos, "tables/out_of_sample.csv", row.names = FALSE)

# ---- 15. Cook's distance sensitivity (FF3) -----------------------
cook_sensitivity <- bind_rows(lapply(tickers, function(t) {
  m <- ff3_models[[t]]
  d <- cooks.distance(m)
  keep <- d <= 4 / 128
  stock_data <- analysis_data %>% filter(Ticker == t) %>% arrange(Date)
  m2 <- lm(Excess_Return ~ MKT_RF + SMB + HML, data = stock_data[keep, ])
  data.frame(Ticker = t, Max_Cook = max(d),
             Max_Cook_month = stock_data$Date[which.max(d)],
             Dropped = sum(!keep), Alpha_full = coef(m)[1], Alpha_dropped = coef(m2)[1],
             HML_full = coef(m)[4], HML_dropped = coef(m2)[4])
}))
write.csv(cook_sensitivity, "tables/ff3_cook_sensitivity.csv", row.names = FALSE)

# ---- 16. Figures ------------------------------------------------
cumulative_data <- analysis_data %>%
  arrange(Ticker, Date) %>%
  group_by(Ticker) %>%
  mutate(Growth_of_One = cumprod(1 + Stock_Return / 100)) %>%
  ungroup()
ggplot(cumulative_data, aes(x = Date, y = Growth_of_One, colour = Ticker)) +
  geom_line() + scale_y_log10() +
  labs(title = "Cumulative growth of 1 invested, 2016-2026 (log scale)",
       x = "Date", y = "Growth of 1 invested (log scale)", colour = "Stock") +
  theme_minimal()
ggsave("figures/cumulative_growth.png", width = 9, height = 5, dpi = 300)

ggplot(model_comparison, aes(x = Ticker, y = Adjusted_R_Squared, fill = Model)) +
  geom_col(position = "dodge") +
  labs(title = "Model fit by stock: adjusted R-squared",
       x = "Stock", y = "Adjusted R-squared", fill = "Model") +
  theme_minimal()
ggsave("figures/adjusted_r2_comparison.png", width = 9, height = 5, dpi = 300)

ggplot(rolling_beta, aes(x = Date, y = Rolling_beta_36m, colour = Ticker)) +
  geom_line() + geom_hline(yintercept = 1, linetype = "dashed") +
  labs(title = "Rolling market beta is not stable over the sample",
       x = "End of rolling window", y = "36-month rolling CAPM beta", colour = "Stock") +
  theme_minimal()
ggsave("figures/rolling_capm_beta.png", width = 9, height = 5, dpi = 300)

# ---- 17. Save full results and session info ---------------------
sink("results/complete_ols_results.txt")
for (label in c("CAPM", "FF3", "FF5", "Carhart")) {
  cat("\n\n", label, " REGRESSION RESULTS\n")
  mods <- switch(label, CAPM = capm_models, FF3 = ff3_models,
                 FF5 = ff5_models, Carhart = carhart_models)
  for (t in tickers) { cat("\n---", t, "---\n"); print(summary(mods[[t]])) }
}
cat("\n\nMODEL COMPARISON\n"); print(model_comparison)
cat("\n\nMODEL F-TESTS\n"); print(model_f_tests)
cat("\n\nGRS JOINT ALPHA TESTS\n"); print(grs_results)
cat("\n\nCOOK SENSITIVITY\n"); print(cook_sensitivity)
sink()
writeLines(capture.output(sessionInfo()), "results/session_info.txt")
