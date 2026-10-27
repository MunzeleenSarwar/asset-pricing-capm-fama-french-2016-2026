"""Full analysis for January 2016 to August 2026 (128 months).
Mirrors scripts/asset_pricing_analysis.R, which is the main project script.
R is not installed on the work machine after the October 2026 VM restart,
so this Python script is the run that produced the data, tables, figures
and report numbers in this folder. It uses the same sources, sample and
formulas as the R script: Yahoo Finance adjusted prices, French factor
files, OLS, HC1 and Newey-West (lag 3) standard errors, GRS joint alpha
test, subperiods, 36-month rolling betas, out-of-sample check and Cook
sensitivity. All returns and factors are in percentage points.
"""
import io, json, re, urllib.request, zipfile
import numpy as np, pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = "/home/hatch/workspace/your_files/asset-pricing-capm-fama-french-2016-2026"
TICKERS = ["AAPL", "AVGO", "MSFT", "NVDA", "ORCL"]
N = 128

def download_ff(url, cols):
    raw = urllib.request.urlopen(url, timeout=60).read()
    z = zipfile.ZipFile(io.BytesIO(raw))
    txt = z.read(z.namelist()[0]).decode("utf-8", errors="ignore")
    rows = []
    for line in txt.splitlines():
        if re.match(r"\s*\d{6}\s*,", line):
            parts = [p.strip() for p in line.split(",")]
            try:
                vals = [float(p) for p in parts[1:1 + len(cols)]]
            except ValueError:
                continue
            rows.append([parts[0]] + vals)
    df = pd.DataFrame(rows, columns=["YYYYMM"] + cols)
    df["Date"] = pd.to_datetime(df["YYYYMM"], format="%Y%m") + pd.offsets.MonthEnd(0)
    return df

def yahoo_monthly(ticker):
    url = (f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
           "?period1=1448928000&period2=1788220800&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    res = d["chart"]["result"][0]
    s = pd.Series(res["indicators"]["adjclose"][0]["adjclose"],
                  index=pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert("America/New_York").date)
    s = s.dropna(); s.index = pd.to_datetime(s.index)
    monthly = s.resample("M").last()
    monthly.index = pd.to_datetime(monthly.index.date)
    return monthly

def ols(y, X, names):
    X1 = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
    resid = y - X1 @ beta
    n, k = X1.shape
    sigma2 = (resid @ resid) / (n - k)
    cov = sigma2 * np.linalg.inv(X1.T @ X1)
    se = np.sqrt(np.diag(cov)); t = beta / se; p = 2 * stats.t.sf(np.abs(t), n - k)
    r2 = 1 - (resid ** 2).sum() / ((y - y.mean()) ** 2).sum()
    adj = 1 - (1 - r2) * (n - 1) / (n - k)
    XtX_inv = np.linalg.inv(X1.T @ X1)
    meat = (X1 * (resid ** 2)[:, None]).T @ X1 * (n / (n - k))
    se_hc1 = np.sqrt(np.diag(XtX_inv @ meat @ XtX_inv))
    L = 3; S = (X1 * (resid ** 2)[:, None]).T @ X1
    for lag in range(1, L + 1):
        w = 1 - lag / (L + 1); e1 = resid[lag:]; e0 = resid[:-lag]
        cross = (X1[lag:] * (e1 * e0)[:, None]).T @ X1[:-lag]
        S = S + w * (cross + cross.T)
    se_nw = np.sqrt(np.diag(XtX_inv @ S @ XtX_inv * (n / (n - k))))
    ll = -n / 2 * (np.log(2 * np.pi * (resid ** 2).sum() / n) + 1)
    aic = -2 * ll + 2 * (k + 1); bic = -2 * ll + np.log(n) * (k + 1)
    b_bp, *_ = np.linalg.lstsq(X1, resid ** 2, rcond=None)
    r_bp = resid ** 2 - X1 @ b_bp
    r2_bp = 1 - (r_bp ** 2).sum() / ((resid ** 2 - (resid ** 2).mean()) ** 2).sum()
    p_bp = stats.chi2.sf(n * r2_bp, k - 1)
    m2 = np.mean((resid - resid.mean()) ** 2); m3 = np.mean((resid - resid.mean()) ** 3); m4 = np.mean((resid - resid.mean()) ** 4)
    skew = m3 / m2 ** 1.5; kurt = m4 / m2 ** 2
    jb = n / 6 * (skew ** 2 + (kurt - 3) ** 2 / 4); p_jb = stats.chi2.sf(jb, 2)
    return dict(names=["Alpha"] + names, beta=beta, se=se, se_hc1=se_hc1, se_nw=se_nw,
                p=p, resid=resid, adj=adj, r2=r2, sigma=np.sqrt(sigma2), aic=aic, bic=bic,
                bp_p=p_bp, jb_p=p_jb, X=X1, n=n, k=k)

def bg_p(resid, X1, order=3):
    n = len(resid)
    lags = np.column_stack([np.roll(resid, l) for l in range(1, order + 1)])[order:]
    Xa = np.column_stack([X1[order:], lags]); ya = resid[order:]
    b, *_ = np.linalg.lstsq(Xa, ya, rcond=None); r = ya - Xa @ b
    r2 = 1 - (r ** 2).sum() / ((ya - ya.mean()) ** 2).sum()
    return stats.chi2.sf((n - order) * r2, order)

def vif(X, names):
    out = {}
    for i, nm in enumerate(names):
        o = np.delete(X, i, axis=1); Xd = np.column_stack([np.ones(len(X)), o])
        b, *_ = np.linalg.lstsq(Xd, X[:, i], rcond=None); pred = Xd @ b
        r2 = 1 - ((X[:, i] - pred) ** 2).sum() / ((X[:, i] - X[:, i].mean()) ** 2).sum()
        out[nm] = 1 / (1 - r2)
    return out

def grs(alphas, resid_mat, factors):
    T, Nn = resid_mat.shape; K = factors.shape[1]
    Sigma = resid_mat.T @ resid_mat / (T - K - 1)
    fbar = factors.mean(axis=0); Omega = np.atleast_2d(np.cov(factors, rowvar=False, bias=True))
    stat = (T - Nn - K) / Nn * (alphas @ np.linalg.inv(Sigma) @ alphas) / (1 + fbar @ np.linalg.inv(Omega) @ fbar)
    return stat, stats.f.sf(stat, Nn, T - Nn - K)

# ---- Download ----
ff3 = download_ff("https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip",
                  ["MKT_RF", "SMB", "HML", "RF"])
ff5 = download_ff("https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip",
                  ["MKT_RF5", "SMB5", "HML5", "RMW", "CMA", "RF5"])
mom = download_ff("https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_CSV.zip",
                  ["MOM"])
prices = {tk: yahoo_monthly(tk) for tk in TICKERS}
prices_df = pd.DataFrame(prices)
rets = 100 * (prices_df / prices_df.shift(1) - 1)
rets = rets.loc["2016-01-01":"2026-08-31"].dropna()
assert len(rets) == N, len(rets)
rets_wide = rets.copy(); rets_wide.index.name = "Date"
rets_wide.to_csv(f"{BASE}/data/monthly_stock_returns_wide.csv")
ff = ff3.merge(ff5, on="Date").merge(mom, on="Date")
ff = ff.loc[(ff["Date"] >= "2016-01-01") & (ff["Date"] <= "2026-08-31")].reset_index(drop=True)
assert len(ff) == N, len(ff)
assert np.allclose(ff["RF"], ff["RF5"])
ff_out = ff.drop(columns=["YYYYMM", "YYYYMM_x", "YYYYMM_y", "RF5"], errors="ignore")
ff_out.to_csv(f"{BASE}/data/fama_french_factors.csv", index=False)

rows = []
for tk in TICKERS:
    for dt, r in rets[tk].items():
        f = ff.loc[ff["Date"] == dt].iloc[0]
        rows.append(dict(Date=dt, Ticker=tk, Stock_Return=r, Excess_Return=r - f["RF"],
                         MKT_RF=f["MKT_RF"], SMB=f["SMB"], HML=f["HML"], RF=f["RF"],
                         MKT_RF5=f["MKT_RF5"], SMB5=f["SMB5"], HML5=f["HML5"],
                         RMW=f["RMW"], CMA=f["CMA"], MOM=f["MOM"]))
data = pd.DataFrame(rows)
data.to_csv(f"{BASE}/data/final_asset_pricing_dataset.csv", index=False)
assert len(data) == 640

MODELS = {"CAPM": ["MKT_RF"], "FF3": ["MKT_RF", "SMB", "HML"],
          "FF5": ["MKT_RF5", "SMB5", "HML5", "RMW", "CMA"],
          "Carhart": ["MKT_RF", "SMB", "HML", "MOM"]}
models = {mn: {} for mn in MODELS}
for tk in TICKERS:
    d = data[data["Ticker"] == tk]; y = d["Excess_Return"].values
    for mn, cols in MODELS.items():
        models[mn][tk] = ols(y, d[cols].values, cols)

# Descriptive, factor stats, correlations
desc = []
for tk in TICKERS:
    d = data[data["Ticker"] == tk]
    desc.append(dict(Stock=tk, N=len(d), Mean=round(d["Stock_Return"].mean(), 2), SD=round(d["Stock_Return"].std(), 2),
                     Minimum=round(d["Stock_Return"].min(), 2), Maximum=round(d["Stock_Return"].max(), 2),
                     Mean_excess=round(d["Excess_Return"].mean(), 2)))
pd.DataFrame(desc).to_csv(f"{BASE}/tables/descriptive_statistics.csv", index=False)
ffm = data.drop_duplicates("Date")[["MKT_RF", "SMB", "HML", "RF", "RMW", "CMA", "MOM"]]
ffm.agg(["mean", "std", "min", "max"]).round(2).to_csv(f"{BASE}/tables/factor_descriptive_statistics.csv")
data.drop_duplicates("Date")[["MKT_RF", "SMB", "HML", "RF"]].corr().round(3).to_csv(f"{BASE}/tables/factor_correlation_matrix.csv")

for mn in MODELS:
    rws = []
    for tk in TICKERS:
        m = models[mn][tk]; row = {"Stock": tk}
        for nm, b, se, p in zip(m["names"], m["beta"], m["se"], m["p"]):
            row[f"{nm}"] = round(float(b), 3); row[f"{nm}_SE"] = round(float(se), 3); row[f"{nm}_p"] = round(float(p), 4)
        row["Adj_R2"] = round(m["adj"], 3); row["Residual_SE"] = round(m["sigma"], 2)
        rws.append(row)
    pd.DataFrame(rws).to_csv(f"{BASE}/tables/{mn.lower()}_results.csv", index=False)

comp = []
for mn in MODELS:
    for tk in TICKERS:
        m = models[mn][tk]
        comp.append(dict(Stock=tk, Model=mn, Adj_R2=round(m["adj"], 3), Residual_SE=round(m["sigma"], 2),
                         AIC=round(m["aic"], 2), BIC=round(m["bic"], 2)))
pd.DataFrame(comp).to_csv(f"{BASE}/tables/model_comparison.csv", index=False)

def ftest(r, u):
    q = u["k"] - r["k"]; n = u["n"]
    F = ((r["resid"] @ r["resid"] - u["resid"] @ u["resid"]) / q) / ((u["resid"] @ u["resid"]) / (n - u["k"]))
    return F, stats.f.sf(F, q, n - u["k"])
ft = []
for tk in TICKERS:
    F, p = ftest(models["CAPM"][tk], models["FF3"][tk]); ft.append(dict(Stock=tk, Test="CAPM vs FF3", F=round(F, 3), p=round(float(p), 4)))
    F, p = ftest(models["FF3"][tk], models["Carhart"][tk]); ft.append(dict(Stock=tk, Test="FF3 vs Carhart (MOM added)", F=round(F, 3), p=round(float(p), 4)))
pd.DataFrame(ft).to_csv(f"{BASE}/tables/model_f_tests.csv", index=False)

diag = []
for mn in ["CAPM", "FF3"]:
    for tk in TICKERS:
        m = models[mn][tk]
        diag.append(dict(Stock=tk, Model=mn, BP_p=round(float(m["bp_p"]), 4),
                         BG_p=round(float(bg_p(m["resid"], m["X"])), 4), JB_p=round(float(m["jb_p"]), 4)))
pd.DataFrame(diag).to_csv(f"{BASE}/tables/diagnostic_summary.csv", index=False)
vif_rows = []
for tk in TICKERS:
    d = data[data["Ticker"] == tk]
    for k, v in vif(d[["MKT_RF", "SMB", "HML"]].values, ["MKT_RF", "SMB", "HML"]).items():
        vif_rows.append(dict(Stock=tk, Variable=k, VIF=round(v, 3)))
pd.DataFrame(vif_rows).to_csv(f"{BASE}/tables/vif_results.csv", index=False)

rob = []
for tk in TICKERS:
    m = models["FF3"][tk]
    for nm, b, se, h, nw, p in zip(m["names"], m["beta"], m["se"], m["se_hc1"], m["se_nw"], m["p"]):
        rob.append(dict(Stock=tk, Term=nm, Estimate=round(float(b), 3), OLS_SE=round(float(se), 3),
                        HC1_SE=round(float(h), 3), NW3_SE=round(float(nw), 3), p_OLS=round(float(p), 4)))
pd.DataFrame(rob).to_csv(f"{BASE}/tables/ff3_robust_se.csv", index=False)

grs_rows = []
for mn, cols in MODELS.items():
    alphas = np.array([models[mn][tk]["beta"][0] for tk in TICKERS])
    resid_mat = np.column_stack([models[mn][tk]["resid"] for tk in TICKERS])
    fac = data.drop_duplicates("Date")[cols].values
    stat, p = grs(alphas, resid_mat, fac)
    grs_rows.append(dict(Model=mn, GRS_F=round(float(stat), 3), p=round(float(p), 4), df1=5, df2=int(N - 5 - len(cols))))
pd.DataFrame(grs_rows).to_csv(f"{BASE}/tables/grs_joint_alpha_tests.csv", index=False)

sub = []
for label, mask in [("2016-2019", data["Date"] < "2020-01-01"), ("2020-2026", data["Date"] >= "2020-01-01")]:
    for tk in TICKERS:
        d = data[(data["Ticker"] == tk) & mask]
        m = ols(d["Excess_Return"].values, d[["MKT_RF", "SMB", "HML"]].values, ["MKT_RF", "SMB", "HML"])
        sub.append(dict(Period=label, Stock=tk, N=len(d), Alpha=round(m["beta"][0], 3), Alpha_p=round(float(m["p"][0]), 4),
                        Market_beta=round(m["beta"][1], 3), SMB=round(m["beta"][2], 3), HML=round(m["beta"][3], 3),
                        Adj_R2=round(m["adj"], 3)))
pd.DataFrame(sub).to_csv(f"{BASE}/tables/ff3_subperiods.csv", index=False)

roll_rows = []
for tk in TICKERS:
    d = data[data["Ticker"] == tk].reset_index(drop=True)
    for i in range(35, N):
        w = d.iloc[i - 35:i + 1]
        m = ols(w["Excess_Return"].values, w[["MKT_RF"]].values, ["MKT_RF"])
        roll_rows.append(dict(Date=w["Date"].iloc[-1], Stock=tk, Rolling_beta_36m=round(m["beta"][1], 3)))
roll_df = pd.DataFrame(roll_rows)
roll_df.to_csv(f"{BASE}/tables/rolling_capm_beta_36m.csv", index=False)

oos = []
for mn, cols in [("CAPM", ["MKT_RF"]), ("FF3", ["MKT_RF", "SMB", "HML"])]:
    for tk in TICKERS:
        tr = data[(data["Ticker"] == tk) & (data["Date"] < "2021-01-01")]
        te = data[(data["Ticker"] == tk) & (data["Date"] >= "2021-01-01")]
        m = ols(tr["Excess_Return"].values, tr[cols].values, cols)
        pred = m["beta"][0] + te[cols].values @ m["beta"][1:]
        r2o = 1 - ((te["Excess_Return"].values - pred) ** 2).sum() / (te["Excess_Return"].values ** 2).sum()
        oos.append(dict(Model=mn, Stock=tk, OOS_R2=round(float(r2o), 3), Test_months=len(te)))
pd.DataFrame(oos).to_csv(f"{BASE}/tables/out_of_sample.csv", index=False)

cook_rows = []
for tk in TICKERS:
    m = models["FF3"][tk]; X = m["X"]; resid = m["resid"]
    h = np.sum(X * (X @ np.linalg.inv(X.T @ X)), axis=1)
    mse = (resid ** 2).sum() / (N - 4)
    cook = resid ** 2 / (4 * mse) * (h / (1 - h) ** 2)
    d = data[data["Ticker"] == tk].reset_index(drop=True)
    keep = cook <= 4 / N
    m2 = ols(d.loc[keep, "Excess_Return"].values, d.loc[keep, ["MKT_RF", "SMB", "HML"]].values, ["MKT_RF", "SMB", "HML"])
    cook_rows.append(dict(Stock=tk, Max_Cook=round(float(cook.max()), 3),
                          Max_Cook_month=str(d.loc[np.argmax(cook), "Date"].date()),
                          Dropped=int((~keep).sum()), Alpha_full=round(m["beta"][0], 3),
                          Alpha_dropped=round(m2["beta"][0], 3), HML_full=round(m["beta"][3], 3),
                          HML_dropped=round(m2["beta"][3], 3)))
pd.DataFrame(cook_rows).to_csv(f"{BASE}/tables/ff3_cook_sensitivity.csv", index=False)

# Figures
plt.rcParams.update({"font.size": 10})
cum = data.copy()
cum["Growth"] = cum.groupby("Ticker")["Stock_Return"].transform(lambda s: np.cumprod(1 + s / 100))
fig, ax = plt.subplots(figsize=(9, 5))
for tk in TICKERS:
    d = cum[cum["Ticker"] == tk]
    ax.plot(d["Date"], d["Growth"], label=tk, linewidth=1.5)
ax.set_yscale("log"); ax.set_ylabel("Growth of 1 invested (log scale)")
ax.set_xlabel("Date"); ax.set_title("Cumulative growth of 1 invested, 2016-2026 (log scale)")
ax.legend(ncol=5, frameon=False); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(f"{BASE}/figures/cumulative_growth.png", dpi=300); plt.close(fig)

comp_df = pd.DataFrame(comp)
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(TICKERS)); w = 0.2
for j, mn in enumerate(["CAPM", "FF3", "FF5", "Carhart"]):
    vals = [comp_df[(comp_df["Stock"] == tk) & (comp_df["Model"] == mn)]["Adj_R2"].iloc[0] for tk in TICKERS]
    ax.bar(x + (j - 1.5) * w, vals, width=w, label=mn)
ax.set_xticks(x); ax.set_xticklabels(TICKERS); ax.set_ylabel("Adjusted R-squared")
ax.set_title("Model fit by stock: adjusted R-squared"); ax.legend(frameon=False); ax.grid(axis="y", alpha=0.3)
fig.tight_layout(); fig.savefig(f"{BASE}/figures/adjusted_r2_comparison.png", dpi=300); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 5))
for tk in TICKERS:
    d = roll_df[roll_df["Stock"] == tk]
    ax.plot(d["Date"], d["Rolling_beta_36m"], label=tk, linewidth=1.5)
ax.axhline(1.0, color="black", linestyle="--", linewidth=0.8)
ax.set_ylabel("36-month rolling CAPM beta"); ax.set_xlabel("End of rolling window")
ax.set_title("Rolling market beta is not stable over the sample")
ax.legend(ncol=5, frameon=False); ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(f"{BASE}/figures/rolling_capm_beta.png", dpi=300); plt.close(fig)

print("Done. Sample months:", N, "dataset rows:", len(data))
print("Cumulative growth end values:")
print(cum.groupby("Ticker")["Growth"].last().round(1).to_string())
print("\nModel comparison:")
print(comp_df.to_string(index=False))
print("\nGRS:")
print(pd.DataFrame(grs_rows).to_string(index=False))
print("\nFF3 alphas:")
for tk in TICKERS:
    print(tk, round(models["FF3"][tk]["beta"][0], 3), "HML", round(models["FF3"][tk]["beta"][3], 3), "adjR2", round(models["FF3"][tk]["adj"], 3))
