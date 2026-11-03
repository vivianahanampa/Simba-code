"""
Compare SimBA predictions on held-out test videos against your own hand annotations.

Usage (run inside your SimBA conda environment):
    python evaluate_simba_test_videos.py \
        --project /path/to/project_folder \
        --annotations /path/to/project_folder/csv/heldout_test_annotations \
        --classifier Attack

Optional:
    --fps 30          # used only if logs/video_info.csv is missing a video
    --sweep           # also print F1 at a range of probability thresholds (diagnostic only)

For each test video it reads:
    <annotations>/<video>.csv              -> human labels (column named after the classifier, 0/1)
    <project>/csv/machine_results/<video>.csv -> SimBA labels (same column name, 0/1)
                                                and Probability_<classifier>
and prints frame-level precision / recall / F1 plus total behavior time and bout counts.
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd


def read_table(path):
    if path.endswith(".parquet"):
        return pd.read_parquet(path)
    return pd.read_csv(path, index_col=0)


def find_file(directory, video_name):
    for ext in (".csv", ".parquet"):
        candidate = os.path.join(directory, video_name + ext)
        if os.path.isfile(candidate):
            return candidate
    return None


def count_bouts(labels):
    # A bout starts wherever the label goes 0 -> 1 (or the video starts in a bout).
    padded = np.concatenate([[0], labels])
    return int(np.sum((padded[1:] == 1) & (padded[:-1] == 0)))


def frame_metrics(truth, pred):
    tp = int(np.sum((truth == 1) & (pred == 1)))
    fp = int(np.sum((truth == 0) & (pred == 1)))
    fn = int(np.sum((truth == 1) & (pred == 0)))
    tn = int(np.sum((truth == 0) & (pred == 0)))
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else float("nan")
    return dict(tp=tp, fp=fp, fn=fn, tn=tn, precision=precision, recall=recall, f1=f1)


def load_fps_table(project):
    path = os.path.join(project, "logs", "video_info.csv")
    if not os.path.isfile(path):
        return {}
    df = pd.read_csv(path)
    return dict(zip(df["Video"].astype(str), df["fps"].astype(float)))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", required=True, help="Path to SimBA project_folder")
    parser.add_argument("--annotations", required=True, help="Folder with held-out human-annotated files")
    parser.add_argument("--classifier", required=True, help="Classifier/behavior name, exactly as in SimBA")
    parser.add_argument("--fps", type=float, default=None, help="Fallback fps if not in video_info.csv")
    parser.add_argument("--sweep", action="store_true", help="Print F1 across probability thresholds")
    args = parser.parse_args()

    clf = args.classifier
    prob_col = f"Probability_{clf}"
    results_dir = os.path.join(args.project, "csv", "machine_results")
    fps_table = load_fps_table(args.project)

    annotation_files = sorted(f for f in os.listdir(args.annotations) if f.endswith((".csv", ".parquet")))
    if not annotation_files:
        sys.exit(f"No .csv/.parquet files found in {args.annotations}")

    rows, all_truth, all_pred, all_prob = [], [], [], []
    for file_name in annotation_files:
        video = os.path.splitext(file_name)[0]
        pred_path = find_file(results_dir, video)
        if pred_path is None:
            print(f"[skip] {video}: no machine_results file. Did you run the model on this video?")
            continue

        truth_df = read_table(os.path.join(args.annotations, file_name))
        pred_df = read_table(pred_path)
        if clf not in truth_df.columns:
            print(f"[skip] {video}: column '{clf}' not in annotation file")
            continue
        if clf not in pred_df.columns:
            print(f"[skip] {video}: column '{clf}' not in machine_results file")
            continue

        n = min(len(truth_df), len(pred_df))
        if len(truth_df) != len(pred_df):
            print(f"[warn] {video}: {len(truth_df)} annotated frames vs {len(pred_df)} predicted; using first {n}")
        truth = truth_df[clf].to_numpy()[:n].astype(int)
        pred = pred_df[clf].to_numpy()[:n].astype(int)

        fps = fps_table.get(video, args.fps)
        m = frame_metrics(truth, pred)
        rows.append({
            "video": video,
            "frames": n,
            "precision": m["precision"],
            "recall": m["recall"],
            "f1": m["f1"],
            "human_s": truth.sum() / fps if fps else np.nan,
            "simba_s": pred.sum() / fps if fps else np.nan,
            "human_bouts": count_bouts(truth),
            "simba_bouts": count_bouts(pred),
        })
        all_truth.append(truth)
        all_pred.append(pred)
        if prob_col in pred_df.columns:
            all_prob.append(pred_df[prob_col].to_numpy()[:n])

    if not rows:
        sys.exit("Nothing to evaluate.")

    table = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(f"\nPer-video results for '{clf}' (frame level):\n")
    print(table.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    pooled = frame_metrics(np.concatenate(all_truth), np.concatenate(all_pred))
    print(f"\nPooled over all test videos: precision={pooled['precision']:.3f}  "
          f"recall={pooled['recall']:.3f}  F1={pooled['f1']:.3f}  "
          f"(TP={pooled['tp']}, FP={pooled['fp']}, FN={pooled['fn']})")
    if table["human_s"].notna().all():
        r = np.corrcoef(table["human_s"], table["simba_s"])[0, 1] if len(table) > 2 else float("nan")
        print(f"Total time  human={table['human_s'].sum():.1f}s  simba={table['simba_s'].sum():.1f}s  "
              f"(per-video correlation r={r:.3f})")
    else:
        print("Durations unavailable: add the videos to logs/video_info.csv or pass --fps.")

    out_path = os.path.join(args.project, "logs", f"heldout_evaluation_{clf}.csv")
    if os.path.isdir(os.path.dirname(out_path)):
        table.to_csv(out_path, index=False)
        print(f"\nSaved per-video table to {out_path}")

    if args.sweep:
        if len(all_prob) != len(all_truth):
            print(f"\n[sweep skipped] '{prob_col}' column missing in some machine_results files")
            return
        truth = np.concatenate(all_truth)
        prob = np.concatenate(all_prob)
        print("\nThreshold sweep (raw probabilities, no minimum-bout filter). Diagnostic only:")
        print("choosing your final threshold here makes the test score optimistic.\n")
        print("threshold  precision  recall     F1")
        for t in np.arange(0.1, 0.95, 0.05):
            m = frame_metrics(truth, (prob >= t).astype(int))
            print(f"   {t:.2f}     {m['precision']:.3f}    {m['recall']:.3f}  {m['f1']:.3f}")


if __name__ == "__main__":
    main()
