import json, argparse, os
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import glob


# --- Styling ---
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman"],
    "axes.labelsize": 12,
    "font.size": 11,
    "legend.fontsize": 10,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
})

# ---------- Helpers ----------
def load_metrics(path):
    with open(path, "rt", encoding="utf-8") as f:
        return json.load(f)

def extract_jcts(metrics_json):
    return np.array([j["JCT"] for j in metrics_json["job_metrics"] if j.get("JCT") is not None], dtype=float)

def ecdf(values):
    x = np.sort(np.asarray(values, dtype=float))
    y = np.arange(1, len(x)+1) / len(x)
    return x, y

def write_caption_snippet(filename, title, label, outdir):
    snippet = (
        "\\begin{figure}[h]\n"
        "  \\centering\n"
        f"  \\includegraphics[width=0.48\\textwidth]{{{filename}}}\n"
        f"  \\caption{{{title}}}\n"
        f"  \\label{{fig:{label}}}\n"
        "\\end{figure}\n\n"
    )
    with open(Path(outdir) / "captions_figures.tex", "a", encoding="utf-8") as f:
        f.write(snippet)

def pct_delta(a, b):
    return 100.0 * (b - a) / b

# ---------- Aggregation ----------
def load_runs(paths):
    """Return list of per-run JCT arrays and list of per-run summary dicts."""
    runs = []
    summaries = []
    for p in paths:
        js = load_metrics(p)
        runs.append(extract_jcts(js))
        summaries.append({
            "avg_jct": js.get("avg_jct"),
            "tail_latency_95th": js.get("tail_latency_95th"),
            "max_jct": js.get("max_jct"),
            "min_jct": js.get("min_jct"),
            "makespan": js.get("makespan"),
        })
    return runs, summaries

def quantile_grid(runs, probs=np.linspace(0, 1, 200)):
    """Mean ECDF via averaging quantiles across runs (+ IQR band)."""
    Q = np.vstack([np.quantile(r, probs) for r in runs])  # (num_runs, len(probs))
    mean = Q.mean(axis=0)
    lo   = np.percentile(Q, 25, axis=0)
    hi   = np.percentile(Q, 75, axis=0)
    return mean, lo, hi, probs

# ---------- Plot utils ----------
def _annotate_bar_values(ax, rects, fmt="{:.0f}"):
    """Place numeric value labels on top of bars."""
    for r in rects:
        height = r.get_height()
        ax.annotate(fmt.format(height),
                    xy=(r.get_x() + r.get_width() / 2, height),
                    xytext=(0, 3),  # 3 pts vertical offset
                    textcoords="offset points",
                    ha="center", va="bottom")

# ---------- Plots ----------
def plot_pooled_ecdf(custom_runs, default_runs, outdir):
    pooled_c = np.concatenate(custom_runs)
    pooled_d = np.concatenate(default_runs)

    x_c, y_c = ecdf(pooled_c)
    x_d, y_d = ecdf(pooled_d)

    plt.figure()
    plt.step(x_c, y_c, where="post", label="Custom (pooled)")
    plt.step(x_d, y_d, where="post", label="Default (pooled)")
    plt.xlabel("Job Completion Time (s)")
    plt.ylabel("CDF")
    plt.title("CDF of Job Completion Time (pooled across runs)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    outpath = Path(outdir) / "cdf_jct_pooled.pdf"
    plt.savefig(outpath, bbox_inches="tight")
    plt.close()
    print(f"✅ Saved pooled ECDF to {outpath}")
    write_caption_snippet(str(outpath),
        "Pooled ECDF of job completion times across runs per scheduler.",
        "cdf-jct-pooled", outdir)

def plot_mean_ecdf(custom_runs, default_runs, outdir):
    mc_mean, mc_lo, mc_hi, p = quantile_grid(custom_runs)
    md_mean, md_lo, md_hi, _ = quantile_grid(default_runs, probs=p)

    plt.figure()
    plt.plot(mc_mean, p, label="Custom (mean ECDF)")
    plt.fill_betweenx(p, mc_lo, mc_hi, alpha=0.2)
    plt.plot(md_mean, p, label="Default (mean ECDF)")
    plt.fill_betweenx(p, md_lo, md_hi, alpha=0.2)
    plt.xlabel("Job Completion Time (s)")
    plt.ylabel("CDF")
    plt.title("Mean ECDF of JCT with IQR band for 48 jobs half load")
    plt.grid(True, alpha=0.3)
    plt.legend()
    outpath = Path(outdir) / "cdf_jct_mean.pdf"
    plt.savefig(outpath, bbox_inches="tight")
    plt.close()
    print(f"✅ Saved mean ECDF to {outpath}")
    write_caption_snippet(str(outpath),
        "Mean ECDF (with interquartile band) of job completion times across runs.",
        "cdf-jct-mean", outdir)

def plot_summary_bars_avg(custom_summaries, default_summaries, outdir):
    """
    Summary bars WITHOUT std-dev whiskers and WITH value labels on top.
    """
    metrics = [
        ("avg_jct", "Avg JCT (s)"),
        ("tail_latency_95th", "Tail (95th) JCT (s)"),
        ("max_jct", "Max JCT (s)"),
        ("min_jct", "Min JCT (s)"),
        ("makespan", "Makespan (s)"),
    ]

    def stack(key, lst):
        vals = np.array([d[key] for d in lst if d.get(key) is not None], dtype=float)
        return vals

    has_c = len(custom_summaries) > 0
    has_d = len(default_summaries) > 0

    c_means, d_means, labels = [], [], []
    for k, label in metrics:
        labels.append(label)
        if has_c:
            c_vals = stack(k, custom_summaries)
            c_means.append(c_vals.mean() if c_vals.size else 0.0)
        else:
            c_means.append(0.0)

        if has_d:
            d_vals = stack(k, default_summaries)
            d_means.append(d_vals.mean() if d_vals.size else 0.0)
        else:
            d_means.append(0.0)

    x = np.arange(len(labels))
    w = 0.38

    fig, ax = plt.subplots()
    if has_c and has_d:
        rects1 = ax.bar(x - w/2, c_means, w, label="Custom")
        rects2 = ax.bar(x + w/2, d_means, w, label="Default")
        title = "Summary average metrics across runs"
        _annotate_bar_values(ax, rects1)
        _annotate_bar_values(ax, rects2)
    elif has_c:
        rects1 = ax.bar(x, c_means, w, label="Custom")
        title = "Summary average metrics across runs"
        _annotate_bar_values(ax, rects1)
    else:
        rects2 = ax.bar(x, d_means, w, label="Default")
        title = "Summary average metrics across runs"
        _annotate_bar_values(ax, rects2)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Seconds")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.3)
    ax.legend()

    outpath = Path(outdir) / "summary_bars_avg.pdf"
    fig.savefig(outpath, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ Saved averaged summary bars to {outpath}")
    write_caption_snippet(str(outpath),
        "Average values of key metrics across runs (bars show means; no variability whiskers).",
        "summary-bars-avg", outdir)

# ---------- Improvements I/O ----------
def save_improvements(outdir, avg_impr_pct, tail_impr_pct, mk_impr_pct):
    outpath = Path(outdir) / "improvements.txt"
    with open(outpath, "w", encoding="utf-8") as f:
        f.write("Average improvements (Custom vs Default):\n")
        f.write(f"- Avg JCT improvement: {avg_impr_pct:.2f}%\n")
        f.write(f"- Tail Latency (95th) improvement: {tail_impr_pct:.2f}%\n")
        f.write(f"- Makespan improvement: {mk_impr_pct:.2f}%\n")
    print(f"📝 Saved improvements to {outpath}")

# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--custom", nargs="+", required=False, help="One or more metrics_*.json for custom")
    parser.add_argument("--default", nargs="+", required=False, help="One or more metrics_*.json for default")
    parser.add_argument("--outdir", default="figs")
    args = parser.parse_args()

    # --- Expand any wildcards on Windows ---
    if args.custom:
        expanded_custom = []
        for pattern in args.custom:
            expanded_custom.extend(glob.glob(pattern))
        args.custom = sorted(expanded_custom) or None

    if args.default:
        expanded_default = []
        for pattern in args.default:
            expanded_default.extend(glob.glob(pattern))
        args.default = sorted(expanded_default) or None

    os.makedirs(args.outdir, exist_ok=True)
    open(Path(args.outdir) / "captions_figures.tex", "w").close()

    custom_runs, custom_summ = ([], [])
    default_runs, default_summ = ([], [])

    if args.custom:
        custom_runs, custom_summ = load_runs(args.custom)
    if args.default:
        default_runs, default_summ = load_runs(args.default)

    # --- CDFs ---
    if args.custom and args.default:
        plot_pooled_ecdf(custom_runs, default_runs, args.outdir)
        plot_mean_ecdf(custom_runs, default_runs, args.outdir)
    elif args.custom:
        pooled_c = np.concatenate(custom_runs)
        x_c, y_c = ecdf(pooled_c)
        plt.figure()
        plt.step(x_c, y_c, where="post", label="Custom (pooled)")
        plt.xlabel("Job Completion Time (s)")
        plt.ylabel("CDF")
        plt.title("Custom Scheduler: Pooled ECDF")
        plt.grid(True, alpha=0.3)
        plt.legend()
        outpath = Path(args.outdir) / "cdf_jct_pooled_custom.pdf"
        plt.savefig(outpath, bbox_inches="tight")
        plt.close()

        mc_mean, mc_lo, mc_hi, p = quantile_grid(custom_runs)
        plt.figure()
        plt.plot(mc_mean, p, label="Custom (mean ECDF)")
        plt.fill_betweenx(p, mc_lo, mc_hi, alpha=0.2)
        plt.xlabel("Job Completion Time (s)")
        plt.ylabel("CDF")
        plt.title("Custom Scheduler: Mean ECDF with IQR band for 12 jobs")
        plt.grid(True, alpha=0.3)
        plt.legend()
        outpath = Path(args.outdir) / "cdf_jct_mean_custom.pdf"
        plt.savefig(outpath, bbox_inches="tight")
        plt.close()

    elif args.default:
        pooled_d = np.concatenate(default_runs)
        x_d, y_d = ecdf(pooled_d)
        plt.figure()
        plt.step(x_d, y_d, where="post", label="Default (pooled)")
        plt.xlabel("Job Completion Time (s)")
        plt.ylabel("CDF")
        plt.title("Default Scheduler: Pooled ECDF")
        plt.grid(True, alpha=0.3)
        plt.legend()
        outpath = Path(args.outdir) / "cdf_jct_pooled_default.pdf"
        plt.savefig(outpath, bbox_inches="tight")
        plt.close()

        md_mean, md_lo, md_hi, p = quantile_grid(default_runs)
        plt.figure()
        plt.plot(md_mean, p, label="Default (mean ECDF)")
        plt.fill_betweenx(p, md_lo, md_hi, alpha=0.2)
        plt.xlabel("Job Completion Time (s)")
        plt.ylabel("CDF")
        plt.title("Default Scheduler: Mean ECDF (IQR band)")
        plt.grid(True, alpha=0.3)
        plt.legend()
        outpath = Path(args.outdir) / "cdf_jct_mean_default.pdf"
        plt.savefig(outpath, bbox_inches="tight")
        plt.close()

    # --- Summary bars (no std-dev, with labels) ---
    if args.custom and args.default:
        plot_summary_bars_avg(custom_summ, default_summ, args.outdir)
    elif args.custom:
        plot_summary_bars_avg(custom_summ, [], args.outdir)
    elif args.default:
        plot_summary_bars_avg([], default_summ, args.outdir)

    # --- Improvements: print + save to file when both provided ---
    if args.custom and args.default:
        try:
            avg_c = np.mean([d["avg_jct"] for d in custom_summ if d["avg_jct"] is not None])
            avg_d = np.mean([d["avg_jct"] for d in default_summ if d["avg_jct"] is not None])
            tail_c = np.mean([d["tail_latency_95th"] for d in custom_summ if d["tail_latency_95th"] is not None])
            tail_d = np.mean([d["tail_latency_95th"] for d in default_summ if d["tail_latency_95th"] is not None])
            mk_c = np.mean([d["makespan"] for d in custom_summ if d["makespan"] is not None])
            mk_d = np.mean([d["makespan"] for d in default_summ if d["makespan"] is not None])

            avg_impr_pct  = pct_delta(avg_c,  avg_d)
            tail_impr_pct = pct_delta(tail_c, tail_d)
            mk_impr_pct   = pct_delta(mk_c,   mk_d)

            print(f"\nAvg JCT improvement (mean over runs): {avg_impr_pct:.2f}%")
            print(f"Tail Latency improvement (mean over runs): {tail_impr_pct:.2f}%")
            print(f"Makespan improvement (mean over runs): {mk_impr_pct:.2f}%")

            save_improvements(args.outdir, avg_impr_pct, tail_impr_pct, mk_impr_pct)
        except Exception as e:
            print(f"⚠️ Could not compute/save improvements: {e}")

if __name__ == "__main__":
    main()
