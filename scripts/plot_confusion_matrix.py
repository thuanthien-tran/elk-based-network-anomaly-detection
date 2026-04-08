#!/usr/bin/env python3
"""
Generate confusion matrix heatmap image for report.
"""

from pathlib import Path
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import seaborn as sns
except Exception:
    sns = None


def main() -> int:
    cm = np.array([
        [1175, 1],
        [8, 1168],
    ])
    labels = ["Normal", "Attack"]

    output = Path("report") / "confusion_matrix_heatmap.png"
    output.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(6, 5))
    if sns is not None:
        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap="Blues",
            xticklabels=labels,
            yticklabels=labels,
            cbar=True,
            linewidths=0.5,
            linecolor="white",
        )
    else:
        plt.imshow(cm, cmap="Blues")
        plt.colorbar()
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                plt.text(j, i, f"{cm[i, j]}", ha="center", va="center", color="black")
        plt.xticks([0, 1], labels)
        plt.yticks([0, 1], labels)

    plt.title("Confusion Matrix - ELKShield Random Forest")
    plt.xlabel("Predicted label")
    plt.ylabel("True label")
    plt.tight_layout()
    plt.savefig(output, dpi=300)
    print(f"Saved: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
