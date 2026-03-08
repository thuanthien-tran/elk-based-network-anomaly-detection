#!/usr/bin/env python3
"""
Data preprocessing script for network logs
"""

import pandas as pd
import numpy as np
import sys
from datetime import datetime
import argparse
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
from collections import Counter

def clean_data(df):
    """Clean the raw data"""
    print("Cleaning data...")
    
    # Remove duplicates
    initial_count = len(df)
    df = df.drop_duplicates()
    print(f"Removed {initial_count - len(df)} duplicate records")
    
    # Handle missing values
    # Fill numeric columns with 0
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(0)
    
    # Fill categorical columns with 'unknown'
    categorical_cols = df.select_dtypes(include=['object', 'str']).columns
    df[categorical_cols] = df[categorical_cols].fillna('unknown')
    
    return df

def extract_time_features(df):
    """Extract time-based features"""
    print("Extracting time features...")
    
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Extract time components
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['day_of_month'] = df['timestamp'].dt.day
        df['month'] = df['timestamp'].dt.month
        
        # Is weekend flag
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        
        # Is business hours (9 AM - 5 PM)
        df['is_business_hours'] = ((df['hour'] >= 9) & (df['hour'] <= 17)).astype(int)
    
    return df

def extract_ip_features(df, ip_column='source_ip'):
    """Extract features related to IP addresses"""
    print("Extracting IP features...")
    
    if ip_column in df.columns:
        # Count requests per IP (total)
        ip_counts = df[ip_column].value_counts()
        df['requests_per_ip'] = df[ip_column].map(ip_counts)
        
        # Hash IP address instead of encoding (to avoid false relationships)
        import hashlib
        df['ip_hash'] = df[ip_column].apply(
            lambda x: int(hashlib.md5(str(x).encode()).hexdigest()[:8], 16) if pd.notna(x) else 0
        )
    
    return df

def extract_attack_features(df, window_minutes=5):
    """Extract features related to attacks with time windows"""
    print("Extracting attack features...")
    
    if 'timestamp' not in df.columns:
        return df
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    # Failed login count per IP (total)
    if 'status' in df.columns and 'source_ip' in df.columns:
        failed_logins = df[df['status'] == 'failed'].groupby('source_ip').size()
        df['failed_login_count'] = df['source_ip'].map(failed_logins).fillna(0)
        
        # Window-based failed login count (within time window)
        df_sorted = df.sort_values('timestamp')
        window = pd.Timedelta(minutes=window_minutes)
        
        failed_in_window = []
        for idx, row in df_sorted.iterrows():
            if row['status'] == 'failed' and pd.notna(row['source_ip']):
                window_start = row['timestamp'] - window
                window_end = row['timestamp']
                mask = (
                    (df_sorted['timestamp'] >= window_start) & 
                    (df_sorted['timestamp'] <= window_end) &
                    (df_sorted['source_ip'] == row['source_ip']) &
                    (df_sorted['status'] == 'failed')
                )
                failed_in_window.append(mask.sum())
            else:
                failed_in_window.append(0)
        
        df_sorted['failed_login_count_window'] = failed_in_window
        df = df_sorted.sort_index()
    
    # Attack type frequency
    if 'attack_type' in df.columns:
        attack_types = df['attack_type'].value_counts()
        df['attack_type_frequency'] = df['attack_type'].map(attack_types).fillna(0)
    
    return df

def extract_web_features(df, ip_column='source_ip'):
    """
    Extract features for web/HTTP logs (DU_KIEN_DATASET: URL, status code, 4xx/5xx rate, query pattern).
    """
    print("Extracting web features...")
    
    # Request/URL length
    if 'request' in df.columns:
        df['request_length'] = df['request'].fillna('').astype(str).str.len()
        df['has_query_string'] = (df['request'].fillna('').astype(str).str.contains(r'\?', regex=True)).astype(int)
    else:
        df['request_length'] = 0
        df['has_query_string'] = 0
    
    # Status code (response)
    if 'response' in df.columns:
        df['response'] = pd.to_numeric(df['response'], errors='coerce').fillna(0).astype(int)
        df['is_4xx'] = ((df['response'] >= 400) & (df['response'] < 500)).astype(int)
        df['is_5xx'] = (df['response'] >= 500).astype(int)
    else:
        df['response'] = 0
        df['is_4xx'] = 0
        df['is_5xx'] = 0
    
    # Per-IP error rate (4xx+5xx count / request count)
    if ip_column in df.columns:
        ip_total = df.groupby(ip_column).size()
        df['requests_per_ip'] = df[ip_column].map(ip_total).fillna(0)
        err = df[df['is_4xx'] == 1].groupby(ip_column).size()
        df['count_4xx_per_ip'] = df[ip_column].map(err).fillna(0)
        err5 = df[df['is_5xx'] == 1].groupby(ip_column).size()
        df['count_5xx_per_ip'] = df[ip_column].map(err5).fillna(0)
        df['error_rate_per_ip'] = np.where(
            df['requests_per_ip'] > 0,
            (df['count_4xx_per_ip'] + df['count_5xx_per_ip']) / df['requests_per_ip'],
            0
        )
    
    return df

def normalize_numeric_features(df, columns=None):
    """Normalize numeric features"""
    print("Normalizing numeric features...")
    
    if columns is None:
        # Auto-detect numeric columns (exclude target variables)
        exclude_cols = ['is_attack', 'ml_anomaly', 'status']
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        columns = [col for col in numeric_cols if col not in exclude_cols]
    
    for col in columns:
        if col in df.columns:
            # Min-Max normalization
            min_val = df[col].min()
            max_val = df[col].max()
            if max_val > min_val:
                df[f'{col}_normalized'] = (df[col] - min_val) / (max_val - min_val)
    
    return df

def handle_imbalance(df, target_col='is_attack', method='undersample', random_state=42):
    """
    Handle class imbalance in the dataset
    
    Args:
        df: DataFrame
        target_col: Target column name
        method: 'undersample', 'oversample', or 'smote'
        random_state: Random state for reproducibility
    """
    if target_col not in df.columns:
        print(f"Warning: {target_col} not found, skipping imbalance handling")
        return df
    
    print(f"Handling class imbalance using {method}...")
    print(f"Original distribution: {Counter(df[target_col])}")
    
    # Separate features and target
    X = df.drop(columns=[target_col], errors='ignore')
    y = df[target_col]
    
    if method == 'undersample':
        sampler = RandomUnderSampler(random_state=random_state)
    elif method == 'oversample':
        from imblearn.over_sampling import RandomOverSampler
        sampler = RandomOverSampler(random_state=random_state)
    elif method == 'smote':
        sampler = SMOTE(random_state=random_state)
    else:
        print(f"Unknown method {method}, skipping")
        return df
    
    try:
        X_resampled, y_resampled = sampler.fit_resample(X, y)
        df_resampled = pd.DataFrame(X_resampled, columns=X.columns)
        df_resampled[target_col] = y_resampled
        
        print(f"Resampled distribution: {Counter(df_resampled[target_col])}")
        return df_resampled
    except Exception as e:
        print(f"Error in resampling: {e}")
        return df

def main():
    parser = argparse.ArgumentParser(description='Preprocess network logs')
    parser.add_argument('--input', required=True, help='Input CSV file')
    parser.add_argument('--output', required=True, help='Output CSV file')
    parser.add_argument('--clean', action='store_true', help='Clean data')
    parser.add_argument('--extract-time', action='store_true', help='Extract time features')
    parser.add_argument('--extract-ip', action='store_true', help='Extract IP features')
    parser.add_argument('--extract-attack', action='store_true', help='Extract attack features')
    parser.add_argument('--normalize', action='store_true', help='Normalize numeric features')
    parser.add_argument('--handle-imbalance', choices=['undersample', 'oversample', 'smote'],
                       help='Handle class imbalance')
    parser.add_argument('--window-minutes', type=int, default=5,
                       help='Time window in minutes for window-based features')
    parser.add_argument('--log-type', choices=['ssh', 'web', 'auto'], default='auto',
                       help='Log type: ssh (SSH features), web (web features), auto (detect from columns)')
    
    args = parser.parse_args()
    
    # Load data
    print(f"Loading data from {args.input}...")
    try:
        df = pd.read_csv(args.input, encoding="utf-8", encoding_errors="replace")
    except pd.errors.EmptyDataError:
        print("[ERROR] File is empty or has no columns.")
        print("  Cause: data_extraction.py likely extracted 0 logs from Elasticsearch.")
        print("  Fix: 1) Start Filebeat and send logs  2) Check index exists: curl http://127.0.0.1:9200/_cat/indices?v")
        print("       3) Re-run: python scripts/data_extraction.py --index \"test-logs-*,ssh-logs-*\" --output data/raw/logs.csv --hours 24 --host 127.0.0.1 --port 9200")
        sys.exit(1)
    if len(df) == 0:
        print("[ERROR] CSV has 0 rows. Run data_extraction.py first and ensure Elasticsearch has logs (Filebeat running).")
        sys.exit(1)
    print(f"Loaded {len(df)} records")
    print(f"Columns: {list(df.columns)}")
    
    # Apply preprocessing steps
    if args.clean:
        df = clean_data(df)
    
    if args.extract_time:
        df = extract_time_features(df)
    
    if args.extract_ip:
        df = extract_ip_features(df, ip_column='source_ip' if 'source_ip' in df.columns else 'clientip')
    
    # Feature set by log type (DU_KIEN_DATASET: SSH vs web-specific features)
    log_type = args.log_type
    if log_type == 'auto':
        has_web = 'request' in df.columns and 'response' in df.columns
        has_ssh = 'status' in df.columns and 'source_ip' in df.columns
        if has_web and has_ssh:
            log_type = 'both'
        elif has_web:
            log_type = 'web'
        elif has_ssh:
            log_type = 'ssh'
        else:
            log_type = 'ssh'
    if log_type in ('web', 'both'):
        df = extract_web_features(df)
    if args.extract_attack and ('status' in df.columns and 'source_ip' in df.columns):
        df = extract_attack_features(df, window_minutes=args.window_minutes)
    
    if args.normalize:
        df = normalize_numeric_features(df)
    
    if args.handle_imbalance:
        df = handle_imbalance(df, method=args.handle_imbalance)
    
    # Save processed data
    df.to_csv(args.output, index=False)
    print(f"Processed data saved to {args.output}")
    print(f"Final shape: {df.shape}")
    
    # Print statistics
    print("\nData Statistics:")
    print(df.describe())
    
    if 'is_attack' in df.columns:
        print(f"\nAttack distribution:")
        print(df['is_attack'].value_counts())

if __name__ == '__main__':
    main()
