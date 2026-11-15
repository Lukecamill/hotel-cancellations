"""Reproduce the recorded Entry 2 evidence; see docs/diary2-preparation-and-open-items.md."""


def main():
    from pathlib import Path
    import pandas as pd
    import numpy as np
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    r = Path(__file__).resolve().parents[1]
    out = r / "docs/figures"
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(r / "docs/evidence/diary2/monthly-drift-quality.csv")
    plt.rcParams.update(
        {"font.family": "DejaVu Sans", "font.size": 16, "axes.spines.top": False, "axes.spines.right": False}
    )
    for hotel, stem in [("City Hotel", "city"), ("Resort Hotel", "resort")]:
        d = df[df.hotel == hotel]
        x = np.arange(len(d))
        fig, axes = plt.subplots(
            2, 1, figsize=(12, 4.8), sharex=True, gridspec_kw={"height_ratios": [1, 1], "hspace": 0.13}
        )
        axes[0].plot(x, d.lead_time_psi, "o-", color="#21618C", lw=2.3, label="Lead time")
        axes[0].plot(x, d.market_segment_psi, "s--", color="#14806C", lw=2.3, label="Market segment")
        axes[0].axhline(0.1, color="#777777", ls=":", lw=1.2)
        axes[0].axhline(0.25, color="#777777", ls="--", lw=1.2)
        axes[0].set_ylabel("Input PSI")
        axes[0].set_ylim(0, max(0.68, float(d.market_segment_psi.max()) * 1.12))
        axes[0].legend(loc="upper left", bbox_to_anchor=(0, 1.38), ncol=2, frameon=False, fontsize=15)
        axes[1].axhspan(0.85, 1.15, color="#E3EEE7", label="Accepted band")
        axes[1].plot(x, d.expected_observed_ratio, "o-", color="#AC3F2F", lw=2.3, label="Predicted / observed")
        axes[1].axhline(1, color="#8B968E", lw=0.8)
        axes[1].set_ylabel("Cancellation\nratio")
        axes[1].set_ylim(0.4, 1.2)
        axes[1].set_xticks(x, labels=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"])
        axes[1].set_xlabel("2017 arrival-month cohort")
        for ax in axes:
            ax.grid(axis="y", alpha=0.2)
            ax.set_xlim(-0.15, 7.15)
        fig.subplots_adjust(left=0.12, right=0.98, top=0.86, bottom=0.15)
        fig.savefig(out / ("diary2-" + stem + "-drift-quality.png"), dpi=170, facecolor="white")
        fig.savefig(out / ("diary2-" + stem + "-drift-quality.pdf"), facecolor="white")
        plt.close(fig)
    print("Created two plots from the monthly CSV")


if __name__ == "__main__":
    main()
