#!/usr/bin/env python3
"""
Comprehensive ML Model Evaluator with Visualizations
Includes ROC curves, feature importance, and detailed metrics
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_curve, auc,
    precision_recall_curve, average_precision_score, roc_auc_score
)
from sklearn.model_selection import cross_val_score, StratifiedKFold
import argparse
import json
from datetime import datetime
import os

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)

class MLEvaluator:
    def __init__(self, model, X_test, y_test, y_pred, y_pred_proba=None, model_name="Model"):
        """
        Initialize evaluator
        
        Args:
            model: Trained model
            X_test: Test features
            y_test: True labels
            y_pred: Predicted labels
            y_pred_proba: Predicted probabilities (for binary classification)
            model_name: Name of the model
        """
        self.model = model
        self.X_test = X_test
        self.y_test = y_test
        self.y_pred = y_pred
        self.y_pred_proba = y_pred_proba
        self.model_name = model_name
        
    def plot_roc_curve(self, save_path=None):
        """Plot ROC curve"""
        if self.y_pred_proba is None or len(np.unique(self.y_test)) < 2:
            print("Cannot plot ROC curve: need probabilities and binary classification")
            return
        
        fpr, tpr, thresholds = roc_curve(self.y_test, self.y_pred_proba)
        roc_auc = auc(fpr, tpr)
        
        plt.figure(figsize=(10, 8))
        plt.plot(fpr, tpr, color='darkorange', lw=2, 
                label=f'ROC curve (AUC = {roc_auc:.4f})')
        plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', label='Random')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate', fontsize=12)
        plt.ylabel('True Positive Rate', fontsize=12)
        plt.title(f'ROC Curve - {self.model_name}', fontsize=14, fontweight='bold')
        plt.legend(loc="lower right", fontsize=11)
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"ROC curve saved to {save_path}")
        else:
            plt.show()
        plt.close()
        
        return roc_auc
    
    def plot_precision_recall_curve(self, save_path=None):
        """Plot Precision-Recall curve"""
        if self.y_pred_proba is None or len(np.unique(self.y_test)) < 2:
            print("Cannot plot PR curve: need probabilities and binary classification")
            return
        
        precision, recall, thresholds = precision_recall_curve(self.y_test, self.y_pred_proba)
        avg_precision = average_precision_score(self.y_test, self.y_pred_proba)
        
        plt.figure(figsize=(10, 8))
        plt.plot(recall, precision, color='blue', lw=2,
                label=f'PR curve (AP = {avg_precision:.4f})')
        plt.xlabel('Recall', fontsize=12)
        plt.ylabel('Precision', fontsize=12)
        plt.title(f'Precision-Recall Curve - {self.model_name}', fontsize=14, fontweight='bold')
        plt.legend(loc="lower left", fontsize=11)
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Precision-Recall curve saved to {save_path}")
        else:
            plt.show()
        plt.close()
        
        return avg_precision
    
    def plot_confusion_matrix(self, save_path=None):
        """Plot confusion matrix"""
        cm = confusion_matrix(self.y_test, self.y_pred)
        
        plt.figure(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                   xticklabels=['Normal', 'Attack'],
                   yticklabels=['Normal', 'Attack'],
                   cbar_kws={'label': 'Count'})
        plt.ylabel('True Label', fontsize=12)
        plt.xlabel('Predicted Label', fontsize=12)
        plt.title(f'Confusion Matrix - {self.model_name}', fontsize=14, fontweight='bold')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Confusion matrix saved to {save_path}")
        else:
            plt.show()
        plt.close()
    
    def plot_feature_importance(self, feature_names, top_n=20, save_path=None):
        """Plot feature importance (for tree-based models)"""
        if not hasattr(self.model, 'feature_importances_'):
            print("Model does not support feature importance")
            return
        
        importances = self.model.feature_importances_
        indices = np.argsort(importances)[::-1][:top_n]
        
        plt.figure(figsize=(12, 8))
        plt.barh(range(len(indices)), importances[indices], color='steelblue')
        plt.yticks(range(len(indices)), [feature_names[i] for i in indices])
        plt.xlabel('Feature Importance', fontsize=12)
        plt.title(f'Top {top_n} Feature Importance - {self.model_name}', 
                 fontsize=14, fontweight='bold')
        plt.gca().invert_yaxis()
        plt.grid(True, alpha=0.3, axis='x')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Feature importance plot saved to {save_path}")
        else:
            plt.show()
        plt.close()
        
        # Return feature importance as DataFrame
        importance_df = pd.DataFrame({
            'feature': [feature_names[i] for i in indices],
            'importance': importances[indices]
        })
        return importance_df
    
    def generate_report(self, output_dir='reports'):
        """Generate comprehensive evaluation report"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Classification report
        report = classification_report(self.y_test, self.y_pred, output_dict=True)
        
        # Confusion matrix
        cm = confusion_matrix(self.y_test, self.y_pred)
        tn, fp, fn, tp = cm.ravel()
        
        # Calculate metrics
        accuracy = (tp + tn) / (tp + tn + fp + fn)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        false_positive_rate = fp / (fp + tn) if (fp + tn) > 0 else 0
        
        metrics = {
            'model_name': self.model_name,
            'timestamp': datetime.now().isoformat(),
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'false_positive_rate': false_positive_rate,
            'true_positives': int(tp),
            'true_negatives': int(tn),
            'false_positives': int(fp),
            'false_negatives': int(fn),
        }
        
        # Add ROC AUC if available
        if self.y_pred_proba is not None and len(np.unique(self.y_test)) > 1:
            roc_auc = roc_auc_score(self.y_test, self.y_pred_proba)
            metrics['roc_auc'] = float(roc_auc)
        
        # Save metrics
        metrics_path = os.path.join(output_dir, f'{self.model_name}_metrics.json')
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        # Save classification report
        report_path = os.path.join(output_dir, f'{self.model_name}_classification_report.txt')
        with open(report_path, 'w') as f:
            f.write(f"Model: {self.model_name}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
            f.write("Classification Report:\n")
            f.write(classification_report(self.y_test, self.y_pred))
            f.write(f"\n\nConfusion Matrix:\n{cm}\n")
            f.write(f"\nMetrics:\n")
            for key, value in metrics.items():
                f.write(f"{key}: {value}\n")
        
        print(f"\nEvaluation report saved to {output_dir}/")
        return metrics

def main():
    parser = argparse.ArgumentParser(description='Evaluate ML model with visualizations')
    parser.add_argument('--predictions', required=True, help='CSV file with predictions')
    parser.add_argument('--model-file', help='Path to saved model file')
    parser.add_argument('--output-dir', default='reports', help='Output directory for reports')
    parser.add_argument('--model-name', default='Model', help='Model name')
    
    args = parser.parse_args()
    
    # Load predictions
    df = pd.read_csv(args.predictions)
    
    if 'y_true' not in df.columns or 'y_pred' not in df.columns:
        print("Error: CSV must contain 'y_true' and 'y_pred' columns")
        return
    
    y_test = df['y_true'].values
    y_pred = df['y_pred'].values
    y_pred_proba = df['y_pred_proba'].values if 'y_pred_proba' in df.columns else None
    
    # Create evaluator
    evaluator = MLEvaluator(
        model=None,  # Model not needed for evaluation
        X_test=None,
        y_test=y_test,
        y_pred=y_pred,
        y_pred_proba=y_pred_proba,
        model_name=args.model_name
    )
    
    # Generate visualizations
    os.makedirs(args.output_dir, exist_ok=True)
    
    evaluator.plot_confusion_matrix(
        save_path=os.path.join(args.output_dir, f'{args.model_name}_confusion_matrix.png')
    )
    
    if y_pred_proba is not None:
        evaluator.plot_roc_curve(
            save_path=os.path.join(args.output_dir, f'{args.model_name}_roc_curve.png')
        )
        evaluator.plot_precision_recall_curve(
            save_path=os.path.join(args.output_dir, f'{args.model_name}_pr_curve.png')
        )
    
    # Generate report
    metrics = evaluator.generate_report(output_dir=args.output_dir)
    
    print("\nEvaluation Metrics:")
    for key, value in metrics.items():
        print(f"{key}: {value}")

if __name__ == '__main__':
    main()
