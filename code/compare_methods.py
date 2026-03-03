#!/usr/bin/env python3
"""
Compare Rule-based vs ML-based Detection Methods
Generate comprehensive comparison report
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    classification_report, confusion_matrix,
    precision_score, recall_score, f1_score, accuracy_score,
    roc_auc_score
)
import argparse
import json
from datetime import datetime
import os

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 10)

class MethodComparator:
    def __init__(self, df, rule_col='rule_based', ml_col='ml_anomaly', true_col='is_attack'):
        """
        Compare rule-based and ML-based detection
        
        Args:
            df: DataFrame with predictions
            rule_col: Column name for rule-based predictions
            ml_col: Column name for ML-based predictions
            true_col: Column name for true labels
        """
        self.df = df
        self.rule_col = rule_col
        self.ml_col = ml_col
        self.true_col = true_col
        
        # Ensure binary format
        self.y_true = (df[true_col] == 1).astype(int).values if true_col in df.columns else None
        self.y_rule = (df[rule_col] == 1).astype(int).values if rule_col in df.columns else None
        self.y_ml = (df[ml_col] == 1).astype(int).values if ml_col in df.columns else None
    
    def calculate_metrics(self, y_pred, method_name):
        """Calculate all metrics for a method"""
        if self.y_true is None or y_pred is None:
            return None
        
        cm = confusion_matrix(self.y_true, y_pred)
        tn, fp, fn, tp = cm.ravel()
        
        accuracy = accuracy_score(self.y_true, y_pred)
        precision = precision_score(self.y_true, y_pred, zero_division=0)
        recall = recall_score(self.y_true, y_pred, zero_division=0)
        f1 = f1_score(self.y_true, y_pred, zero_division=0)
        false_positive_rate = fp / (fp + tn) if (fp + tn) > 0 else 0
        false_negative_rate = fn / (fn + tp) if (fn + tp) > 0 else 0
        
        return {
            'method': method_name,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'false_positive_rate': false_positive_rate,
            'false_negative_rate': false_negative_rate,
            'true_positives': int(tp),
            'true_negatives': int(tn),
            'false_positives': int(fp),
            'false_negatives': int(fn),
            'total_detected': int(tp + fp),
            'total_actual': int(tp + fn)
        }
    
    def compare_methods(self):
        """Compare both methods"""
        rule_metrics = self.calculate_metrics(self.y_rule, 'Rule-Based')
        ml_metrics = self.calculate_metrics(self.y_ml, 'ML-Based')
        
        return rule_metrics, ml_metrics
    
    def plot_comparison(self, save_path=None):
        """Plot comparison charts"""
        rule_metrics, ml_metrics = self.compare_methods()
        
        if rule_metrics is None or ml_metrics is None:
            print("Cannot plot: missing predictions or labels")
            return
        
        # Prepare data
        metrics_to_plot = ['accuracy', 'precision', 'recall', 'f1_score']
        rule_values = [rule_metrics[m] for m in metrics_to_plot]
        ml_values = [ml_metrics[m] for m in metrics_to_plot]
        
        # Create comparison bar chart
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. Metrics comparison
        ax1 = axes[0, 0]
        x = np.arange(len(metrics_to_plot))
        width = 0.35
        ax1.bar(x - width/2, rule_values, width, label='Rule-Based', color='steelblue', alpha=0.8)
        ax1.bar(x + width/2, ml_values, width, label='ML-Based', color='coral', alpha=0.8)
        ax1.set_xlabel('Metrics', fontsize=12)
        ax1.set_ylabel('Score', fontsize=12)
        ax1.set_title('Metrics Comparison', fontsize=14, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(metrics_to_plot)
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis='y')
        ax1.set_ylim([0, 1.1])
        
        # 2. False Positive/Negative Rate
        ax2 = axes[0, 1]
        fpr_rule = rule_metrics['false_positive_rate']
        fnr_rule = rule_metrics['false_negative_rate']
        fpr_ml = ml_metrics['false_positive_rate']
        fnr_ml = ml_metrics['false_negative_rate']
        
        x = ['False Positive Rate', 'False Negative Rate']
        rule_rates = [fpr_rule, fnr_rule]
        ml_rates = [fpr_ml, fnr_ml]
        
        ax2.bar(x, rule_rates, width=0.35, label='Rule-Based', color='steelblue', alpha=0.8)
        ax2.bar(x, ml_rates, width=0.35, label='ML-Based', bottom=rule_rates, color='coral', alpha=0.8)
        ax2.set_ylabel('Rate', fontsize=12)
        ax2.set_title('Error Rates Comparison', fontsize=14, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')
        
        # 3. Detection counts
        ax3 = axes[1, 0]
        categories = ['TP', 'TN', 'FP', 'FN']
        rule_counts = [
            rule_metrics['true_positives'],
            rule_metrics['true_negatives'],
            rule_metrics['false_positives'],
            rule_metrics['false_negatives']
        ]
        ml_counts = [
            ml_metrics['true_positives'],
            ml_metrics['true_negatives'],
            ml_metrics['false_positives'],
            ml_metrics['false_negatives']
        ]
        
        x = np.arange(len(categories))
        ax3.bar(x - width/2, rule_counts, width, label='Rule-Based', color='steelblue', alpha=0.8)
        ax3.bar(x + width/2, ml_counts, width, label='ML-Based', color='coral', alpha=0.8)
        ax3.set_xlabel('Category', fontsize=12)
        ax3.set_ylabel('Count', fontsize=12)
        ax3.set_title('Confusion Matrix Comparison', fontsize=14, fontweight='bold')
        ax3.set_xticks(x)
        ax3.set_xticklabels(categories)
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis='y')
        
        # 4. Summary table
        ax4 = axes[1, 1]
        ax4.axis('tight')
        ax4.axis('off')
        
        comparison_data = {
            'Metric': ['Accuracy', 'Precision', 'Recall', 'F1-Score', 'FPR', 'FNR'],
            'Rule-Based': [
                f"{rule_metrics['accuracy']:.4f}",
                f"{rule_metrics['precision']:.4f}",
                f"{rule_metrics['recall']:.4f}",
                f"{rule_metrics['f1_score']:.4f}",
                f"{rule_metrics['false_positive_rate']:.4f}",
                f"{rule_metrics['false_negative_rate']:.4f}"
            ],
            'ML-Based': [
                f"{ml_metrics['accuracy']:.4f}",
                f"{ml_metrics['precision']:.4f}",
                f"{ml_metrics['recall']:.4f}",
                f"{ml_metrics['f1_score']:.4f}",
                f"{ml_metrics['false_positive_rate']:.4f}",
                f"{ml_metrics['false_negative_rate']:.4f}"
            ],
            'Difference': [
                f"{ml_metrics['accuracy'] - rule_metrics['accuracy']:+.4f}",
                f"{ml_metrics['precision'] - rule_metrics['precision']:+.4f}",
                f"{ml_metrics['recall'] - rule_metrics['recall']:+.4f}",
                f"{ml_metrics['f1_score'] - rule_metrics['f1_score']:+.4f}",
                f"{ml_metrics['false_positive_rate'] - rule_metrics['false_positive_rate']:+.4f}",
                f"{ml_metrics['false_negative_rate'] - rule_metrics['false_negative_rate']:+.4f}"
            ]
        }
        
        table = ax4.table(cellText=[[comparison_data['Metric'][i],
                                     comparison_data['Rule-Based'][i],
                                     comparison_data['ML-Based'][i],
                                     comparison_data['Difference'][i]]
                                    for i in range(len(comparison_data['Metric']))],
                         colLabels=['Metric', 'Rule-Based', 'ML-Based', 'Difference'],
                         cellLoc='center',
                         loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.5)
        ax4.set_title('Detailed Comparison Table', fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Comparison plot saved to {save_path}")
        else:
            plt.show()
        plt.close()
    
    def generate_report(self, output_dir='reports'):
        """Generate comparison report"""
        os.makedirs(output_dir, exist_ok=True)
        
        rule_metrics, ml_metrics = self.compare_methods()
        
        if rule_metrics is None or ml_metrics is None:
            print("Cannot generate report: missing predictions or labels")
            return
        
        # Save JSON report
        report = {
            'timestamp': datetime.now().isoformat(),
            'rule_based': rule_metrics,
            'ml_based': ml_metrics,
            'summary': {
                'ml_better_accuracy': ml_metrics['accuracy'] > rule_metrics['accuracy'],
                'ml_better_precision': ml_metrics['precision'] > rule_metrics['precision'],
                'ml_better_recall': ml_metrics['recall'] > rule_metrics['recall'],
                'ml_better_f1': ml_metrics['f1_score'] > rule_metrics['f1_score'],
                'ml_lower_fpr': ml_metrics['false_positive_rate'] < rule_metrics['false_positive_rate'],
                'ml_lower_fnr': ml_metrics['false_negative_rate'] < rule_metrics['false_negative_rate']
            }
        }
        
        report_path = os.path.join(output_dir, 'method_comparison.json')
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save text report
        text_report_path = os.path.join(output_dir, 'method_comparison.txt')
        with open(text_report_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("RULE-BASED vs ML-BASED DETECTION COMPARISON\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
            
            f.write("RULE-BASED METRICS:\n")
            f.write("-" * 80 + "\n")
            for key, value in rule_metrics.items():
                f.write(f"{key}: {value}\n")
            
            f.write("\nML-BASED METRICS:\n")
            f.write("-" * 80 + "\n")
            for key, value in ml_metrics.items():
                f.write(f"{key}: {value}\n")
            
            f.write("\nSUMMARY:\n")
            f.write("-" * 80 + "\n")
            for key, value in report['summary'].items():
                f.write(f"{key}: {value}\n")
        
        print(f"\nComparison report saved to {output_dir}/")
        return report

def main():
    parser = argparse.ArgumentParser(description='Compare Rule-based vs ML-based detection')
    parser.add_argument('--input', required=True, help='CSV file with predictions')
    parser.add_argument('--rule-col', default='rule_based', help='Rule-based prediction column')
    parser.add_argument('--ml-col', default='ml_anomaly', help='ML-based prediction column')
    parser.add_argument('--true-col', default='is_attack', help='True label column')
    parser.add_argument('--output-dir', default='reports', help='Output directory')
    
    args = parser.parse_args()
    
    # Load data
    df = pd.read_csv(args.input)
    print(f"Loaded {len(df)} records")
    
    # Create comparator
    comparator = MethodComparator(
        df,
        rule_col=args.rule_col,
        ml_col=args.ml_col,
        true_col=args.true_col
    )
    
    # Generate comparison
    comparator.plot_comparison(
        save_path=os.path.join(args.output_dir, 'method_comparison.png')
    )
    
    report = comparator.generate_report(output_dir=args.output_dir)
    
    print("\nComparison Summary:")
    print(f"ML Better Accuracy: {report['summary']['ml_better_accuracy']}")
    print(f"ML Better Precision: {report['summary']['ml_better_precision']}")
    print(f"ML Better Recall: {report['summary']['ml_better_recall']}")
    print(f"ML Better F1: {report['summary']['ml_better_f1']}")

if __name__ == '__main__':
    main()
