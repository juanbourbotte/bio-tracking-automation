import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def export_results_excel(summary_df, events_df, coloc_df, stats_df, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        if summary_df is not None and not summary_df.empty:
            summary_df.to_excel(writer, sheet_name="Per-Cell Summary", index=False)
        if stats_df is not None and not stats_df.empty:
            stats_df.to_excel(writer, sheet_name="Statistical Comparisons", index=False)
        if events_df is not None and not events_df.empty:
            events_df.to_excel(writer, sheet_name="Detailed Events", index=False)
        if coloc_df is not None and not coloc_df.empty:
            coloc_df.to_excel(writer, sheet_name="All Colocalizations", index=False)

def generate_plots(summary_df, events_df, stats_df, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    sns.set_theme(style="ticks", palette="muted")
    plt.rcParams.update({"font.size": 10, "figure.dpi": 300, "font.sans-serif": "Arial"})

    has_conditions = "CONDITION" in summary_df.columns and summary_df["CONDITION"].nunique() >= 2

    # -------------------------------------------------------------
    # FIGURE 1: QUANTIFICATION & STATISTICAL COMPARISONS
    # -------------------------------------------------------------
    fig1, axes1 = plt.subplots(1, 3, figsize=(18, 5))

    if has_conditions:
        df_freq = summary_df.melt(
            id_vars=["CONDITION", "CELL_ID"],
            value_vars=["Fusion_Freq_per_um2_min", "Fission_Freq_per_um2_min"],
            var_name="Event_Type", value_name="Frequency"
        )
        df_freq["Event_Type"] = df_freq["Event_Type"].str.replace("_Freq_per_um2_min", "")

        sns.boxplot(data=df_freq, x="Event_Type", y="Frequency", hue="CONDITION", ax=axes1[0], palette="Set2", width=0.5, boxprops=dict(alpha=0.7))
        sns.stripplot(data=df_freq, x="Event_Type", y="Frequency", hue="CONDITION", ax=axes1[0], dodge=True, color="black", size=6, alpha=0.7)
        axes1[0].set_ylabel("Frequency (events / µm² / min)")
        axes1[0].set_title("A. Fusion & Fission Frequency", fontweight="bold")
        axes1[0].grid(axis="y", linestyle="--", alpha=0.5)

        df_counts = summary_df.melt(
            id_vars=["CONDITION", "CELL_ID"],
            value_vars=["Fusion_Events", "Fission_Events"],
            var_name="Event_Type", value_name="Count"
        )
        df_counts["Event_Type"] = df_counts["Event_Type"].str.replace("_Events", "")

        sns.barplot(data=df_counts, x="Event_Type", y="Count", hue="CONDITION", ax=axes1[1], palette="Set2", capsize=0.1, edgecolor="black")
        axes1[1].set_ylabel("Mean Event Count per Cell")
        axes1[1].set_title("B. Event Counts per Cell (Mean ± SEM)", fontweight="bold")
        axes1[1].grid(axis="y", linestyle="--", alpha=0.5)
    else:
        tot_f = events_df[events_df["EVENT_TYPE"] == "Fusion"].shape[0] if not events_df.empty else 0
        tot_fi = events_df[events_df["EVENT_TYPE"] == "Fission"].shape[0] if not events_df.empty else 0
        axes1[0].bar(["Fusion", "Fission"], [tot_f, tot_fi], color=["#2ca02c", "#d62728"], width=0.45)
        axes1[0].set_title("A. Overall Event Quantification", fontweight="bold")

    axes1[2].axis("off")
    axes1[2].set_title("C. Statistical Comparison Summary", fontweight="bold")

    if not stats_df.empty and has_conditions:
        cond_names = list(summary_df["CONDITION"].unique())
        c1, c2 = cond_names[0], cond_names[1]

        table_data = []
        for idx, row in stats_df.iterrows():
            metric_short = str(row["Metric"]).replace(" (events/µm²/min)", " Freq").replace(" per Cell", "")
            table_data.append([
                metric_short,
                row[f"{c1} Mean±SEM"],
                row[f"{c2} Mean±SEM"],
                f"p={row['p_value']:.4f} ({row['Significance']})"
            ])

        tbl = axes1[2].table(cellText=table_data, colLabels=["Metric", c1, c2, "Significance"], loc="center", cellLoc="center")
        tbl.set_fontsize(8.5)
        tbl.scale(1.05, 1.8)

    plt.tight_layout()
    fig1_path = os.path.join(output_dir, "Figure1_Condition_Statistical_Comparisons.png")
    plt.savefig(fig1_path, dpi=300)
    plt.close(fig1)

    # -------------------------------------------------------------
    # FIGURE 2: KINETICS, TIMING & SPATIAL MAP
    # -------------------------------------------------------------
    if not events_df.empty:
        fig2, axes2 = plt.subplots(1, 3, figsize=(18, 5))
        plot_hue = "CONDITION" if has_conditions else "EVENT_TYPE"

        sns.histplot(data=events_df, x="DURATION_SEC", hue=plot_hue, kde=True, element="step", ax=axes2[0], palette="Set2" if has_conditions else {"Fusion": "#2ca02c", "Fission": "#d62728"})
        axes2[0].set_xlabel("Interaction Duration (seconds)")
        axes2[0].set_ylabel("Event Count")
        axes2[0].set_title("A. Interaction Lifetime Distribution", fontweight="bold")

        sns.histplot(data=events_df, x="TIME_SEC", hue=plot_hue, element="step", bins=20, ax=axes2[1], palette="Set2" if has_conditions else {"Fusion": "#2ca02c", "Fission": "#d62728"})
        axes2[1].set_xlabel("Movie Time (seconds)")
        axes2[1].set_ylabel("Event Count")
        axes2[1].set_title("B. Temporal Distribution of Events", fontweight="bold")

        sns.scatterplot(data=events_df, x="X_POS", y="Y_POS", hue=plot_hue, style="EVENT_TYPE", ax=axes2[2], s=80, alpha=0.85, palette="Set2" if has_conditions else {"Fusion": "#2ca02c", "Fission": "#d62728"})
        axes2[2].set_xlabel("X Position (µm)")
        axes2[2].set_ylabel("Y Position (µm)")
        axes2[2].set_title("C. Spatial Coordinates of Events", fontweight="bold")
        axes2[2].set_aspect("equal", adjustable="datalim")

        plt.tight_layout()
        fig2_path = os.path.join(output_dir, "Figure2_Dynamics_and_Spatial_Map.png")
        plt.savefig(fig2_path, dpi=300)
        plt.close(fig2)