import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from src.ingestion import clean_trackmate_df

def quantify_fusion_fission(df_cav1, df_eea1, dist_thresh, min_frames, max_gap, pixel_scale, time_step, cell_area_um2):
    c1 = clean_trackmate_df(df_cav1)
    c2 = clean_trackmate_df(df_eea1)

    if c1.empty or c2.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    all_colocs, all_events, per_cell_summary = [], [], []
    conditions = sorted(list(set(c1["CONDITION"]).intersection(set(c2["CONDITION"]))))

    for cond in conditions:
        sub_cond_c1 = c1[c1["CONDITION"] == cond]
        sub_cond_c2 = c2[c2["CONDITION"] == cond]
        common_cells = sorted(list(set(sub_cond_c1["CELL_ID"]).intersection(set(sub_cond_c2["CELL_ID"]))))

        for cell_id in common_cells:
            sub_c1 = sub_cond_c1[sub_cond_c1["CELL_ID"] == cell_id]
            sub_c2 = sub_cond_c2[sub_cond_c2["CELL_ID"] == cell_id]
            frames = sorted(list(set(sub_c1["FRAME"]).intersection(set(sub_c2["FRAME"]))))
            cell_colocs = []

            for f in frames:
                f_c1 = sub_c1[sub_c1["FRAME"] == f]
                f_c2 = sub_c2[sub_c2["FRAME"] == f]

                coords1 = f_c1[["POSITION_X", "POSITION_Y"]].values * pixel_scale
                coords2 = f_c2[["POSITION_X", "POSITION_Y"]].values * pixel_scale
                tids1 = f_c1["TRACK_ID"].values
                tids2 = f_c2["TRACK_ID"].values

                tree1, tree2 = cKDTree(coords1), cKDTree(coords2)
                pairs = tree1.query_ball_tree(tree2, r=dist_thresh)

                for idx1, matches in enumerate(pairs):
                    t1 = int(tids1[idx1])
                    x1, y1 = coords1[idx1]
                    for idx2 in matches:
                        t2 = int(tids2[idx2])
                        x2, y2 = coords2[idx2]
                        cell_colocs.append({
                            "CONDITION": cond, "CELL_ID": cell_id, "FRAME": f, "TIME_SEC": f * time_step,
                            "TRACK_CAV1": t1, "TRACK_EEA1": t2, "X": (x1 + x2) / 2.0, "Y": (y1 + y2) / 2.0
                        })

            coloc_df = pd.DataFrame(cell_colocs)
            if coloc_df.empty:
                continue

            all_colocs.append(coloc_df)
            c1_lifespan = sub_c1.groupby("TRACK_ID")["FRAME"].agg(["min", "max"])
            c2_lifespan = sub_c2.groupby("TRACK_ID")["FRAME"].agg(["min", "max"])

            fusion_c, fission_c = 0, 0
            grouped = coloc_df.groupby(["TRACK_CAV1", "TRACK_EEA1"])

            for (t1, t2), group in grouped:
                group = group.sort_values("FRAME")
                frame_list = group["FRAME"].tolist()

                diffs = np.diff(frame_list)
                split_idx = np.where(diffs > (max_gap + 1))[0] + 1
                blocks = np.split(frame_list, split_idx)

                for block in blocks:
                    duration = len(block)
                    if duration < min_frames:
                        continue

                    start_f, end_f = block[0], block[-1]
                    t1_min, t1_max = c1_lifespan.loc[t1, "min"], c1_lifespan.loc[t1, "max"]
                    t2_min, t2_max = c2_lifespan.loc[t2, "min"], c2_lifespan.loc[t2, "max"]

                    is_fusion = (start_f > t1_min) and (start_f > t2_min)
                    is_fission = (end_f < t1_max) and (end_f < t2_max)

                    block_spots = group[group["FRAME"].isin(block)]
                    avg_x, avg_y = block_spots["X"].mean(), block_spots["Y"].mean()

                    if is_fusion:
                        fusion_c += 1
                        all_events.append({
                            "CONDITION": cond, "CELL_ID": cell_id, "EVENT_TYPE": "Fusion",
                            "FRAME": start_f, "TIME_SEC": start_f * time_step,
                            "TRACK_CAV1": t1, "TRACK_EEA1": t2,
                            "DURATION_FRAMES": duration, "DURATION_SEC": duration * time_step,
                            "X_POS": avg_x, "Y_POS": avg_y
                        })

                    if is_fission:
                        fission_c += 1
                        all_events.append({
                            "CONDITION": cond, "CELL_ID": cell_id, "EVENT_TYPE": "Fission",
                            "FRAME": end_f, "TIME_SEC": end_f * time_step,
                            "TRACK_CAV1": t1, "TRACK_EEA1": t2,
                            "DURATION_FRAMES": duration, "DURATION_SEC": duration * time_step,
                            "X_POS": avg_x, "Y_POS": avg_y
                        })

            total_f = max(coloc_df["FRAME"].max(), 1)
            tot_time_min = (total_f * time_step) / 60.0
            per_cell_summary.append({
                "CONDITION": cond, "CELL_ID": cell_id, "Total_Frames": total_f, "Duration_Min": tot_time_min,
                "Fusion_Events": fusion_c, "Fission_Events": fission_c,
                "Fusion_Freq_per_um2_min": fusion_c / (cell_area_um2 * tot_time_min),
                "Fission_Freq_per_um2_min": fission_c / (cell_area_um2 * tot_time_min),
            })

    full_coloc_df = pd.concat(all_colocs, ignore_index=True) if all_colocs else pd.DataFrame()
    full_events_df = pd.DataFrame(all_events)
    summary_df = pd.DataFrame(per_cell_summary)

    return summary_df, full_events_df, full_coloc_df