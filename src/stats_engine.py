import numpy as np
import pandas as pd
from scipy import stats

def calculate_condition_statistics(summary_df, events_df):
    if summary_df.empty or "CONDITION" not in summary_df.columns:
        return pd.DataFrame()

    conditions = summary_df["CONDITION"].unique()
    if len(conditions) < 2:
        return pd.DataFrame()

    c1, c2 = conditions[0], conditions[1]
    g1_sum = summary_df[summary_df["CONDITION"] == c1]
    g2_sum = summary_df[summary_df["CONDITION"] == c2]

    metrics = [
        ("Fusion_Freq_per_um2_min", "Fusion Frequency (events/µm²/min)"),
        ("Fission_Freq_per_um2_min", "Fission Frequency (events/µm²/min)"),
        ("Fusion_Events", "Fusion Events per Cell"),
        ("Fission_Events", "Fission Events per Cell")
    ]

    stat_results = []

    for col_id, metric_label in metrics:
        v1 = g1_sum[col_id].dropna().values
        v2 = g2_sum[col_id].dropna().values

        m1, std1, sem1 = np.mean(v1), np.std(v1, ddof=1), stats.sem(v1) if len(v1) > 1 else 0
        m2, std2, sem2 = np.mean(v2), np.std(v2, ddof=1), stats.sem(v2) if len(v2) > 1 else 0

        norm1 = stats.shapiro(v1).pvalue > 0.05 if len(v1) >= 3 else True
        norm2 = stats.shapiro(v2).pvalue > 0.05 if len(v2) >= 3 else True

        if norm1 and norm2:
            t_stat, p_val = stats.ttest_ind(v1, v2, equal_var=False)
            test_used = "Welch's t-test"
        else:
            t_stat, p_val = stats.mannwhitneyu(v1, v2, alternative="two-sided")
            test_used = "Mann-Whitney U"

        sig_stars = "ns"
        if p_val < 0.001: sig_stars = "***"
        elif p_val < 0.01: sig_stars = "**"
        elif p_val < 0.05: sig_stars = "*"

        stat_results.append({
            "Metric": metric_label,
            f"{c1} Mean±SD": f"{m1:.4f} ± {std1:.4f}",
            f"{c1} Mean±SEM": f"{m1:.4f} ± {sem1:.4f}",
            f"{c2} Mean±SD": f"{m2:.4f} ± {std2:.4f}",
            f"{c2} Mean±SEM": f"{m2:.4f} ± {sem2:.4f}",
            "Test_Used": test_used, "Statistic": t_stat, "p_value": p_val, "Significance": sig_stars
        })

    if not events_df.empty and "CONDITION" in events_df.columns:
        g1_dur = events_df[events_df["CONDITION"] == c1]["DURATION_SEC"].dropna().values
        g2_dur = events_df[events_df["CONDITION"] == c2]["DURATION_SEC"].dropna().values

        if len(g1_dur) > 0 and len(g2_dur) > 0:
            m1, std1, sem1 = np.mean(g1_dur), np.std(g1_dur, ddof=1), stats.sem(g1_dur)
            m2, std2, sem2 = np.mean(g2_dur), np.std(g2_dur, ddof=1), stats.sem(g2_dur)

            u_stat, p_val = stats.mannwhitneyu(g1_dur, g2_dur, alternative="two-sided")
            sig_stars = "ns"
            if p_val < 0.001: sig_stars = "***"
            elif p_val < 0.01: sig_stars = "**"
            elif p_val < 0.05: sig_stars = "*"

            stat_results.append({
                "Metric": "Interaction Duration (seconds)",
                f"{c1} Mean±SD": f"{m1:.2f} ± {std1:.2f}",
                f"{c1} Mean±SEM": f"{m1:.2f} ± {sem1:.2f}",
                f"{c2} Mean±SD": f"{m2:.2f} ± {std2:.2f}",
                f"{c2} Mean±SEM": f"{m2:.2f} ± {sem2:.2f}",
                "Test_Used": "Mann-Whitney U", "Statistic": u_stat, "p_value": p_val, "Significance": sig_stars
            })

    return pd.DataFrame(stat_results)