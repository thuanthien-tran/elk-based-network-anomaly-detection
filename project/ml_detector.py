#!/usr/bin/env python3
"""
Machine Learning-based Anomaly Detection for Network Security
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix, roc_curve, auc, roc_auc_score
import joblib
import argparse
from datetime import datetime
import json
import hashlib
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler

class NetworkAnomalyDetector:
    def __init__(self, model_type='isolation_forest'):
        """
        Initialize the anomaly detector
        
        Args:
            model_type: Type of model to use ('isolation_forest', 'one_class_svm', 'random_forest')
        """
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}  # Dictionary to store encoders for each column
        self.threshold = None  # Threshold for anomaly detection
        
    def prepare_features(self, df):
        """Prepare features for ML model"""
        # Create a copy to avoid modifying original
        df_processed = df.copy()
        
        # Convert timestamp to datetime
        if 'timestamp' in df_processed.columns:
            df_processed['timestamp'] = pd.to_datetime(df_processed['timestamp'])
            df_processed['hour'] = df_processed['timestamp'].dt.hour
            df_processed['day_of_week'] = df_processed['timestamp'].dt.dayofweek
            df_processed['is_weekend'] = (df_processed['day_of_week'] >= 5).astype(int)
        
        # Hash IP addresses instead of encoding (to avoid false relationships)
        if 'source_ip' in df_processed.columns:
            df_processed['ip_hash'] = df_processed['source_ip'].apply(
                lambda x: int(hashlib.md5(str(x).encode()).hexdigest()[:8], 16) if pd.notna(x) and x != '' else 0
            )
            # Feature engineering: Request frequency per IP
            ip_counts = df_processed['source_ip'].value_counts()
            df_processed['requests_per_ip'] = df_processed['source_ip'].map(ip_counts)
        
        # Encode other categorical variables (one encoder per column)
        categorical_cols = ['user', 'geoip_country', 'geoip_city']
        for col in categorical_cols:
            if col in df_processed.columns:
                df_processed[col] = df_processed[col].fillna('unknown')
                # Create or reuse encoder for this column
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    df_processed[f'{col}_encoded'] = self.label_encoders[col].fit_transform(df_processed[col])
                else:
                    # Handle unseen values
                    try:
                        df_processed[f'{col}_encoded'] = self.label_encoders[col].transform(df_processed[col])
                    except ValueError:
                        # If new values exist, refit
                        self.label_encoders[col] = LabelEncoder()
                        df_processed[f'{col}_encoded'] = self.label_encoders[col].fit_transform(df_processed[col])
        
        # Feature engineering: Failed login count
        if 'status' in df_processed.columns:
            df_processed['failed_login'] = (df_processed['status'] == 'failed').astype(int)
            failed_counts = df_processed.groupby('source_ip')['failed_login'].sum()
            df_processed['failed_login_count'] = df_processed['source_ip'].map(failed_counts).fillna(0)
        
        # Select numerical features
        feature_cols = [
            'hour', 'day_of_week', 'is_weekend',
            'requests_per_ip', 'failed_login_count'
        ]
        
        # Add IP hash
        if 'ip_hash' in df_processed.columns:
            feature_cols.append('ip_hash')
        
        # Add encoded columns
        for col in categorical_cols:
            if f'{col}_encoded' in df_processed.columns:
                feature_cols.append(f'{col}_encoded')
        
        # Filter to existing columns
        feature_cols = [col for col in feature_cols if col in df_processed.columns]
        
        X = df_processed[feature_cols].fillna(0)
        
        return X, df_processed
    
    def train(self, df, contamination=0.1, use_cv=True, cv_folds=5, handle_imbalance=False):
        """
        Train the anomaly detection model
        
        Args:
            df: Training dataframe
            contamination: Expected proportion of anomalies (for Isolation Forest)
            use_cv: Use cross-validation for evaluation
            cv_folds: Number of CV folds
            handle_imbalance: Handle class imbalance for supervised learning
        """
        print(f"Training {self.model_type} model...")
        
        # Prepare features
        X, df_processed = self.prepare_features(df)
        
        # Handle imbalance for supervised learning
        if self.model_type == 'random_forest' and handle_imbalance and 'is_attack' in df.columns:
            y = df['is_attack'].astype(int)
            print(f"Original class distribution: {y.value_counts().to_dict()}")
            
            # Use SMOTE for oversampling
            smote = SMOTE(random_state=42)
            X, y = smote.fit_resample(X, y)
            print(f"After SMOTE class distribution: {pd.Series(y).value_counts().to_dict()}")
            
            # Update df_processed for consistency
            df_processed = pd.DataFrame(X, columns=X.columns)
            df_processed['is_attack'] = y
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Initialize and train model
        if self.model_type == 'isolation_forest':
            self.model = IsolationForest(
                contamination=contamination,
                random_state=42,
                n_estimators=100
            )
            self.model.fit(X_scaled)
            
            # Find optimal threshold using score distribution
            scores = self.model.score_samples(X_scaled)
            # Use percentile-based threshold
            threshold_percentile = (1 - contamination) * 100
            self.threshold = np.percentile(scores, threshold_percentile)
            print(f"Anomaly threshold (score): {self.threshold:.4f}")
            
        elif self.model_type == 'one_class_svm':
            self.model = OneClassSVM(
                nu=contamination,
                kernel='rbf',
                gamma='scale'
            )
            self.model.fit(X_scaled)
            
            # Find threshold
            scores = self.model.score_samples(X_scaled)
            threshold_percentile = (1 - contamination) * 100
            self.threshold = np.percentile(scores, threshold_percentile)
            print(f"Anomaly threshold (score): {self.threshold:.4f}")
            
        elif self.model_type == 'random_forest':
            # For supervised learning, need labels
            if 'is_attack' not in df_processed.columns:
                raise ValueError("Random Forest requires 'is_attack' column")
            
            y = df_processed['is_attack'].astype(int)
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.2, random_state=42, stratify=y
            )
            
            self.model = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                n_jobs=-1,
                class_weight='balanced'  # Handle imbalance
            )
            self.model.fit(X_train, y_train)
            
            # Cross-validation
            if use_cv:
                cv_scores = cross_val_score(
                    self.model, X_train, y_train, 
                    cv=StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42),
                    scoring='f1'
                )
                print(f"\nCross-validation F1 scores: {cv_scores}")
                print(f"Mean CV F1: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
            
            # Evaluate on test set
            y_pred = self.model.predict(X_test)
            y_pred_proba = self.model.predict_proba(X_test)[:, 1]
            
            print("\nClassification Report:")
            print(classification_report(y_test, y_pred))
            print("\nConfusion Matrix:")
            print(confusion_matrix(y_test, y_pred))
            
            # ROC Curve
            if len(np.unique(y_test)) > 1:
                roc_auc = roc_auc_score(y_test, y_pred_proba)
                print(f"\nROC AUC Score: {roc_auc:.4f}")
                
                # Feature importance for Random Forest
                if hasattr(self.model, 'feature_importances_'):
                    print("\nTop 10 Feature Importance:")
                    feature_importance = pd.DataFrame({
                        'feature': X.columns if hasattr(X, 'columns') else [f'feature_{i}' for i in range(X.shape[1])],
                        'importance': self.model.feature_importances_
                    }).sort_values('importance', ascending=False)
                    print(feature_importance.head(10).to_string(index=False))
        
        print("Model training completed!")
    
    def predict(self, df):
        """
        Predict anomalies in the data
        
        Returns:
            DataFrame with anomaly predictions and scores
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # Prepare features
        X, df_processed = self.prepare_features(df)
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Predict
        if self.model_type in ['isolation_forest', 'one_class_svm']:
            scores = self.model.score_samples(X_scaled)
            
            # Use threshold if available, otherwise use default prediction
            if self.threshold is not None:
                predictions = (scores < self.threshold).astype(int)
            else:
                predictions = self.model.predict(X_scaled)
                predictions = (predictions == -1).astype(int)
            
            # Convert to boolean (True/False) instead of int (0/1) for Elasticsearch
            df_processed['ml_anomaly'] = predictions.astype(bool)
            df_processed['ml_anomaly_score'] = -scores  # Negative because lower score = more anomalous
            
        else:  # random_forest
            predictions = self.model.predict(X_scaled)
            probabilities = self.model.predict_proba(X_scaled)
            
            # Convert to boolean (True/False) instead of int (0/1) for Elasticsearch
            df_processed['ml_anomaly'] = predictions.astype(bool)
            df_processed['ml_anomaly_score'] = probabilities[:, 1]  # Probability of attack
        
        return df_processed
    
    def save_model(self, filepath):
        """Save the trained model"""
        model_data = {
            'model_type': self.model_type,
            'model': self.model,
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'threshold': self.threshold
        }
        joblib.dump(model_data, filepath)
        print(f"Model saved to {filepath}")
    
    def load_model(self, filepath):
        """Load a trained model"""
        model_data = joblib.load(filepath)
        self.model_type = model_data['model_type']
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.label_encoders = model_data.get('label_encoders', {})
        self.threshold = model_data.get('threshold', None)
        print(f"Model loaded from {filepath}")

def main():
    parser = argparse.ArgumentParser(description='ML-based Network Anomaly Detection')
    parser.add_argument('--input', required=True, help='Input CSV file')
    parser.add_argument('--output', required=True, help='Output CSV file with predictions')
    parser.add_argument('--model-type', choices=['isolation_forest', 'one_class_svm', 'random_forest'],
                       default='isolation_forest', help='Type of ML model')
    parser.add_argument('--train', action='store_true', help='Train a new model')
    parser.add_argument('--model-file', help='Path to save/load model')
    parser.add_argument('--contamination', type=float, default=0.1,
                       help='Expected proportion of anomalies')
    parser.add_argument('--use-cv', action='store_true',
                       help='Use cross-validation for evaluation')
    parser.add_argument('--cv-folds', type=int, default=5,
                       help='Number of CV folds')
    parser.add_argument('--handle-imbalance', action='store_true',
                       help='Handle class imbalance (for supervised learning)')
    
    args = parser.parse_args()
    
    # Load data
    print(f"Loading data from {args.input}...")
    df = pd.read_csv(args.input)
    print(f"Loaded {len(df)} records")
    
    # Initialize detector
    detector = NetworkAnomalyDetector(model_type=args.model_type)
    
    # Train or load model
    if args.train:
        detector.train(
            df, 
            contamination=args.contamination,
            use_cv=args.use_cv,
            cv_folds=args.cv_folds,
            handle_imbalance=args.handle_imbalance
        )
        if args.model_file:
            detector.save_model(args.model_file)
    else:
        if args.model_file:
            detector.load_model(args.model_file)
        else:
            raise ValueError("Either --train or --model-file must be specified")
    
    # Predict
    print("Predicting anomalies...")
    df_predicted = detector.predict(df)
    
    # Save results
    df_predicted.to_csv(args.output, index=False)
    print(f"Results saved to {args.output}")
    
    # Print statistics
    if 'ml_anomaly' in df_predicted.columns:
        anomalies = df_predicted['ml_anomaly'].sum()
        print(f"\nDetected {anomalies} anomalies out of {len(df_predicted)} records")
        print(f"Anomaly rate: {anomalies/len(df_predicted)*100:.2f}%")

if __name__ == '__main__':
    main()
