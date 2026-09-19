import json
import argparse
import os
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman"],
    "axes.labelsize": 12,
    "font.size": 11,
    "legend.fontsize": 10,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
})


def load_metrics(path):
    with open(path, "rt") as f:
        return json.load(f)


def extract_metric(metrics_json, key):
    return [j[key] for j in metrics_json["job_metrics"] if key in j and j[key] is not None]


def compute_cdf(values):
    values = np.sort(np.asarray(values))
    n = len(values)
    y = np.arange(1, n + 1) / n
    return values, y


def write_caption_snippet(filename, title, label, outdir):
    snippet = (
        "\\begin{figure}[h]\n"
        "  \\centering\n"
        f"  \\includegraphics[width=0.48\\textwidth]{{{filename}}}\n"
        f"  \\caption{{{title}}}\n"
        f"  \\label{{fig:{label}}}\n"
        "\\end{figure}\n\n"
    )
    with open(Path(outdir) / "captions_figures.tex", "a") as f:
        f.write(snippet)


def write_metrics_table(custom_json, default_json, reversed_json, outdir):
    rows = [
        ("Avg JCT (s)", "avg_jct"),
        ("Tail (95\\%) JCT (s)", "tail_latency_95th"),
        ("Max JCT (s)", "max_jct"),
        ("Min JCT (s)", "min_jct"),
        ("Makespan (s)", "makespan"),
    ]
    lines = [
        "\\begin{tabular}{lccc}",
        "\\toprule",
        "Metric & Custom & Default & Reversed \\\\",
        "\\midrule"
    ]
    for label, key in rows:
        c = custom_json.get(key, "--")
        d = default_json.get(key, "--")
        r = reversed_json.get(key, "--")
        lines.append(f"{label} & {c:.2f} & {d:.2f} & {r:.2f} \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")

    with open(Path(outdir) / "metrics_table.tex", "w") as f:
        f.write("\n".join(lines))


def plot_cdf(metric_key, label, ylabel, custom_vals, default_vals, reversed_vals, outdir):
    x_c, y_c = compute_cdf(custom_vals)
    x_d, y_d = compute_cdf(default_vals)
    x_r, y_r = compute_cdf(reversed_vals) if reversed_vals else ([], [])

    plt.figure()
    plt.plot(x_c, y_c, label="Custom")
    plt.plot(x_d, y_d, label="Default")
    if reversed_vals:
        plt.plot(x_r, y_r, label="Custom (Reversed)", linestyle="--")
    plt.xlabel(label)
    plt.ylabel("CDF")
    plt.title(f"CDF of {label}")
    plt.grid(True, alpha=0.3)
    plt.legend()
    outpath = Path(outdir) / f"cdf_{metric_key}.pdf"
    plt.savefig(outpath, bbox_inches="tight")
    plt.close()
    print(f"✅ Saved CDF plot to {outpath}")

    write_caption_snippet(
        filename=str(outpath),
        title=f"Cumulative distribution of {label.lower()} comparing the custom, default, and reversed schedulers.",
        label=f"cdf-{metric_key}",
        outdir=outdir
    )


def plot_summary_bars(custom_json, default_json, reversed_json, outdir):
    def g(js, key): return js.get(key)

    metrics_to_plot = [
        ("avg_jct", "Avg JCT (s)"),
        ("tail_latency_95th", "Tail (95th) JCT (s)"),
        ("max_jct", "Max JCT (s)"),
        ("min_jct", "Min JCT (s)"),
        ("makespan", "Makespan (s)"),
    ]

    labels = [label for _, label in metrics_to_plot]
    custom_vals = [g(custom_json, key) for key, _ in metrics_to_plot]
    default_vals = [g(default_json, key) for key, _ in metrics_to_plot]
    reversed_vals = [g(reversed_json, key) for key, _ in metrics_to_plot]

    x = np.arange(len(labels))
    width = 0.25

    plt.figure()
    bars1 = plt.bar(x - width, custom_vals, width, label="Custom")
    bars2 = plt.bar(x, default_vals, width, label="Default")
    bars3 = plt.bar(x + width, reversed_vals, width, label="Custom (Reversed)")

    # Annotate
    for bar_group in [bars1, bars2, bars3]:
        for bar in bar_group:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2, height + 1, f"{height:.0f}",
                     ha='center', va='bottom', fontsize=9)

    plt.xticks(x, labels, rotation=20, ha="right")
    plt.ylabel("Seconds")
    plt.title("Summary Metrics: Custom vs Default vs Reversed")
    plt.grid(axis="y", alpha=0.3)
    plt.legend()
    outpath = Path(outdir) / "summary_bars.pdf"
    plt.savefig(outpath, bbox_inches="tight")
    plt.close()
    print(f"✅ Saved summary bar chart to {outpath}")

    write_caption_snippet(
        filename=str(outpath),
        title="Comparison of performance metrics across the custom scheduler, default Kubernetes scheduler, and reversed scheduling order.",
        label="summary-bars",
        outdir=outdir
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--custom", required=True)
    parser.add_argument("--default", required=True)
    parser.add_argument("--reversed", required=False)
    parser.add_argument("--outdir", default="figs")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    open(Path(args.outdir) / "captions_figures.tex", "w").close()

    custom_json = load_metrics(args.custom)
    default_json = load_metrics(args.default)
    reversed_json = load_metrics(args.reversed) if args.reversed else None

    custom_jct = extract_metric(custom_json, "JCT")
    default_jct = extract_metric(default_json, "JCT")
    reversed_jct = extract_metric(reversed_json, "JCT") if reversed_json else []

    # Plot
    plot_cdf("jct", "Job Completion Time (s)", "CDF",
             custom_jct, default_jct, reversed_jct, args.outdir)

    if reversed_json:
        plot_summary_bars(custom_json, default_json, reversed_json, args.outdir)
        write_metrics_table(custom_json, default_json, reversed_json, args.outdir)
    else:
        print("⚠️ No --reversed provided: skipping 3-bar plots and table with reversed.")

    # Print improvements (custom vs default only)
    def pct_delta(a, b): return 100.0 * (b - a) / b

    print("\n=== Summary ===")
    try:
        avg_c = custom_json["avg_jct"]
        avg_d = default_json["avg_jct"]
        print(f"Avg JCT improvement: {pct_delta(avg_c, avg_d):.2f}%")

        tail_c = custom_json["tail_latency_95th"]
        tail_d = default_json["tail_latency_95th"]
        print(f"Tail Latency improvement: {pct_delta(tail_c, tail_d):.2f}%")

        mk_c = custom_json["makespan"]
        mk_d = default_json["makespan"]
        print(f"Makespan improvement: {pct_delta(mk_c, mk_d):.2f}%")
    except KeyError:
        pass


if __name__ == "__main__":
    main()
