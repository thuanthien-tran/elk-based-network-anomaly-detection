#!/usr/bin/env python3
"""
False Positive Rate Analyzer
Analyzes false positives in detail to improve model performance
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import argparse
import json
from datetime import datetime
import os

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 10)

class FalsePositiveAnalyzer:
    def __init__(self, df, true_col='is_attack', pred_col='ml_anomaly'):
        """
        Analyze false positives
        
        Args:
            df: DataFrame with predictions and true labels
            true_col: Column name for true labels
            pred_col: Column name for predictions
        """
        self.df = df.copy()
        self.true_col = true_col
        self.pred_col = pred_col
        
        # Identify different prediction categories
        self.df['prediction_category'] = 'Unknown'
        self.df.loc[(self.df[true_col] == 1) & (self.df[pred_col] == 1), 'prediction_category'] = 'True Positive'
        self.df.loc[(self.df[true_col] == 0) & (self.df[pred_col] == 0), 'prediction_category'] = 'True Negative'
        self.df.loc[(self.df[true_col] == 0) & (self.df[pred_col] == 1), 'prediction_category'] = 'False Positive'
        self.df.loc[(self.df[true_col] == 1) & (self.df[pred_col] == 0), 'prediction_category'] = 'False Negative'
        
        self.fp_df = self.df[self.df['prediction_category'] == 'False Positive'].copy()
    
    def analyze_fp_by_feature(self, feature_col):
        """Analyze false positives by a specific feature"""
        if feature_col not in self.df.columns:
            return None
        
        fp_counts = self.fp_df[feature_col].value_counts()
        total_counts = self.df[feature_col].value_counts()
        
        fp_rate = (fp_counts / total_counts * 100).fillna(0)
        
        return pd.DataFrame({
            'feature_value': fp_rate.index,
            'total_count': total_counts[fp_rate.index],
            'fp_count': fp_counts[fp_rate.index],
            'fp_rate_percent': fp_rate.values
        }).sort_values('fp_rate_percent', ascending=False)
    
    def plot_fp_analysis(self, save_path=None):
        """Plot false positive analysis"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. Prediction category distribution
        ax1 = axes[0, 0]
        category_counts = self.df['prediction_category'].value_counts()
        colors = {'True Positive': 'green', 'True Negative': 'blue', 
                 'False Positive': 'red', 'False Negative': 'orange'}
        category_counts.plot(kind='bar', ax=ax1, color=[colors.get(c, 'gray') for c in category_counts.index])
        ax1.set_title('Prediction Category Distribution', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Category', fontsize=12)
        ax1.set_ylabel('Count', fontsize=12)
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(True, alpha=0.3, axis='y')
        
        # 2. False Positive Rate by IP (if source_ip exists)
        if 'source_ip' in self.df.columns:
            ax2 = axes[0, 1]
            fp_by_ip = self.analyze_fp_by_feature('source_ip')
            if fp_by_ip is not None and len(fp_by_ip) > 0:
                top_fp_ips = fp_by_ip.head(10)
                ax2.barh(range(len(top_fp_ips)), top_fp_ips['fp_rate_percent'].values, color='coral')
                ax2.set_yticks(range(len(top_fp_ips)))
                ax2.set_yticklabels(top_fp_ips['feature_value'].values)
                ax2.set_xlabel('False Positive Rate (%)', fontsize=12)
                ax2.set_title('Top 10 IPs by False Positive Rate', fontsize=14, fontweight='bold')
                ax2.grid(True, alpha=0.3, axis='x')
        
        # 3. False Positive Rate by Attack Type (if exists)
        if 'attack_type' in self.df.columns:
            ax3 = axes[1, 0]
            fp_by_type = self.analyze_fp_by_feature('attack_type')
            if fp_by_type is not None and len(fp_by_type) > 0:
                fp_by_type.plot(x='feature_value', y='fp_rate_percent', kind='bar', ax=ax3, color='steelblue')
                ax3.set_title('False Positive Rate by Attack Type', fontsize=14, fontweight='bold')
                ax3.set_xlabel('Attack Type', fontsize=12)
                ax3.set_ylabel('False Positive Rate (%)', fontsize=12)
                ax3.tick_params(axis='x', rotation=45)
                ax3.grid(True, alpha=0.3, axis='y')
        
        # 4. Score distribution comparison
        if 'ml_anomaly_score' in self.df.columns:
            ax4 = axes[1, 1]
            fp_scores = self.fp_df['ml_anomaly_score'].values
            tp_scores = self.df[self.df['prediction_category'] == 'True Positive']['ml_anomaly_score'].values
            
            ax4.hist(fp_scores, bins=50, alpha=0.5, label='False Positives', color='red', density=True)
            ax4.hist(tp_scores, bins=50, alpha=0.5, label='True Positives', color='green', density=True)
            ax4.set_xlabel('Anomaly Score', fontsize=12)
            ax4.set_ylabel('Density', fontsize=12)
            ax4.set_title('Score Distribution: FP vs TP', fontsize=14, fontweight='bold')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"False positive analysis plot saved to {save_path}")
        else:
            plt.show()
        plt.close()
    
    def generate_report(self, output_dir='reports'):
        """Generate false positive analysis report"""
        os.makedirs(output_dir, exist_ok=True)
        
        total = len(self.df)
        fp_count = len(self.fp_df)
        tp_count = len(self.df[self.df['prediction_category'] == 'True Positive'])
        tn_count = len(self.df[self.df['prediction_category'] == 'True Negative'])
        fn_count = len(self.df[self.df['prediction_category'] == 'False Negative'])
        
        fp_rate = fp_count / (fp_count + tn_count) if (fp_count + tn_count) > 0 else 0
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_records': int(total),
                'false_positives': int(fp_count),
                'true_positives': int(tp_count),
                'true_negatives': int(tn_count),
                'false_negatives': int(fn_count),
                'false_positive_rate': float(fp_rate),
                'false_negative_rate': float(fn_count / (fn_count + tp_count) if (fn_count + tp_count) > 0 else 0)
            },
            'false_positive_analysis': {}
        }
        
        # Analyze by different features
        if 'source_ip' in self.df.columns:
            fp_by_ip = self.analyze_fp_by_feature('source_ip')
            if fp_by_ip is not None:
                report['false_positive_analysis']['by_ip'] = fp_by_ip.head(20).to_dict('records')
        
        if 'attack_type' in self.df.columns:
            fp_by_type = self.analyze_fp_by_feature('attack_type')
            if fp_by_type is not None:
                report['false_positive_analysis']['by_attack_type'] = fp_by_type.to_dict('records')
        
        if 'ml_anomaly_score' in self.df.columns:
            report['false_positive_analysis']['score_statistics'] = {
                'mean': float(self.fp_df['ml_anomaly_score'].mean()),
                'median': float(self.fp_df['ml_anomaly_score'].median()),
                'std': float(self.fp_df['ml_anomaly_score'].std()),
                'min': float(self.fp_df['ml_anomaly_score'].min()),
                'max': float(self.fp_df['ml_anomaly_score'].max())
            }
        
        # Save JSON report
        json_path = os.path.join(output_dir, 'false_positive_analysis.json')
        with open(json_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save text report
        text_path = os.path.join(output_dir, 'false_positive_analysis.txt')
        with open(text_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("FALSE POSITIVE ANALYSIS REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
            
            f.write("SUMMARY:\n")
            f.write("-" * 80 + "\n")
            for key, value in report['summary'].items():
                f.write(f"{key}: {value}\n")
            
            f.write("\nFALSE POSITIVE ANALYSIS:\n")
            f.write("-" * 80 + "\n")
            if 'by_ip' in report['false_positive_analysis']:
                f.write("\nTop False Positive IPs:\n")
                for item in report['false_positive_analysis']['by_ip'][:10]:
                    f.write(f"  IP: {item['feature_value']}, FP Rate: {item['fp_rate_percent']:.2f}%, "
                           f"FP Count: {item['fp_count']}, Total: {item['total_count']}\n")
            
            if 'score_statistics' in report['false_positive_analysis']:
                f.write("\nFalse Positive Score Statistics:\n")
                stats = report['false_positive_analysis']['score_statistics']
                for key, value in stats.items():
                    f.write(f"  {key}: {value:.4f}\n")
        
        print(f"\nFalse positive analysis report saved to {output_dir}/")
        return report

def main():
    parser = argparse.ArgumentParser(description='Analyze False Positives')
    parser.add_argument('--input', required=True, help='CSV file with predictions')
    parser.add_argument('--true-col', default='is_attack', help='True label column')
    parser.add_argument('--pred-col', default='ml_anomaly', help='Prediction column')
    parser.add_argument('--output-dir', default='reports', help='Output directory')
    
    args = parser.parse_args()
    
    # Load data
    df = pd.read_csv(args.input)
    print(f"Loaded {len(df)} records")
    
    # Create analyzer
    analyzer = FalsePositiveAnalyzer(df, true_col=args.true_col, pred_col=args.pred_col)
    
    # Generate analysis
    analyzer.plot_fp_analysis(
        save_path=os.path.join(args.output_dir, 'false_positive_analysis.png')
    )
    
    report = analyzer.generate_report(output_dir=args.output_dir)
    
    print("\nFalse Positive Analysis Summary:")
    print(f"Total Records: {report['summary']['total_records']}")
    print(f"False Positives: {report['summary']['false_positives']}")
    print(f"False Positive Rate: {report['summary']['false_positive_rate']:.4f}")
    print(f"False Negative Rate: {report['summary']['false_negative_rate']:.4f}")

if __name__ == '__main__':
    main()
