#!/usr/bin/env python3
"""
Performance Benchmarking Script
Measures processing time for different components
"""

import pandas as pd
import numpy as np
import time
import json
from datetime import datetime
import argparse
import os
from scripts.ml_detector import NetworkAnomalyDetector
from scripts.data_preprocessing import clean_data, extract_time_features, extract_ip_features

class PerformanceBenchmark:
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'benchmarks': {}
        }
    
    def benchmark_data_extraction(self, es, index_pattern, hours=24):
        """Benchmark data extraction from Elasticsearch"""
        print("Benchmarking data extraction...")
        
        from scripts.data_extraction import extract_logs
        from datetime import datetime, timedelta
        
        start_time = datetime.now() - timedelta(hours=hours)
        end_time = datetime.now()
        
        start = time.time()
        count = 0
        for batch in extract_logs(es, index_pattern, start_time.isoformat(), end_time.isoformat()):
            count += len(batch)
        elapsed = time.time() - start
        
        self.results['benchmarks']['data_extraction'] = {
            'records_extracted': count,
            'time_seconds': elapsed,
            'records_per_second': count / elapsed if elapsed > 0 else 0
        }
        
        print(f"Extracted {count} records in {elapsed:.2f}s ({count/elapsed:.2f} records/s)")
    
    def benchmark_preprocessing(self, df):
        """Benchmark data preprocessing"""
        print("Benchmarking data preprocessing...")
        
        # Clean data
        start = time.time()
        df_clean = clean_data(df.copy())
        clean_time = time.time() - start
        
        # Extract features
        start = time.time()
        df_features = extract_time_features(df_clean.copy())
        time_features_time = time.time() - start
        
        start = time.time()
        df_features = extract_ip_features(df_features.copy())
        ip_features_time = time.time() - start
        
        total_time = clean_time + time_features_time + ip_features_time
        
        self.results['benchmarks']['preprocessing'] = {
            'records': len(df),
            'clean_time': clean_time,
            'time_features_time': time_features_time,
            'ip_features_time': ip_features_time,
            'total_time': total_time,
            'records_per_second': len(df) / total_time if total_time > 0 else 0
        }
        
        print(f"Processed {len(df)} records in {total_time:.2f}s ({len(df)/total_time:.2f} records/s)")
    
    def benchmark_ml_training(self, df, model_type='isolation_forest'):
        """Benchmark ML model training"""
        print(f"Benchmarking ML training ({model_type})...")
        
        detector = NetworkAnomalyDetector(model_type=model_type)
        
        start = time.time()
        detector.train(df, contamination=0.1)
        train_time = time.time() - start
        
        self.results['benchmarks'][f'ml_training_{model_type}'] = {
            'model_type': model_type,
            'records': len(df),
            'time_seconds': train_time,
            'records_per_second': len(df) / train_time if train_time > 0 else 0
        }
        
        print(f"Trained {model_type} on {len(df)} records in {train_time:.2f}s")
    
    def benchmark_ml_prediction(self, detector, df, model_type='isolation_forest'):
        """Benchmark ML prediction"""
        print(f"Benchmarking ML prediction ({model_type})...")
        
        start = time.time()
        df_predicted = detector.predict(df)
        predict_time = time.time() - start
        
        self.results['benchmarks'][f'ml_prediction_{model_type}'] = {
            'model_type': model_type,
            'records': len(df),
            'time_seconds': predict_time,
            'records_per_second': len(df) / predict_time if predict_time > 0 else 0
        }
        
        print(f"Predicted {len(df)} records in {predict_time:.2f}s ({len(df)/predict_time:.2f} records/s)")
    
    def benchmark_es_indexing(self, es, df, index_name='benchmark-test'):
        """Benchmark Elasticsearch indexing"""
        print("Benchmarking Elasticsearch indexing...")
        
        from scripts.elasticsearch_writer import write_results
        
        start = time.time()
        write_results(es, df, index_name=index_name, refresh='false')
        index_time = time.time() - start
        
        self.results['benchmarks']['es_indexing'] = {
            'records': len(df),
            'time_seconds': index_time,
            'records_per_second': len(df) / index_time if index_time > 0 else 0
        }
        
        print(f"Indexed {len(df)} records in {index_time:.2f}s ({len(df)/index_time:.2f} records/s)")
        
        # Cleanup
        try:
            es.indices.delete(index=f"{index_name}-*", ignore=[404])
        except:
            pass
    
    def save_results(self, output_path='reports/performance_benchmark.json'):
        """Save benchmark results"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nBenchmark results saved to {output_path}")
    
    def print_summary(self):
        """Print benchmark summary"""
        print("\n" + "=" * 80)
        print("PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 80)
        
        for benchmark_name, metrics in self.results['benchmarks'].items():
            print(f"\n{benchmark_name}:")
            print(f"  Records: {metrics.get('records', 'N/A')}")
            print(f"  Time: {metrics.get('time_seconds', 0):.4f}s")
            if 'records_per_second' in metrics:
                print(f"  Throughput: {metrics['records_per_second']:.2f} records/s")

def main():
    parser = argparse.ArgumentParser(description='Performance Benchmarking')
    parser.add_argument('--data-file', help='CSV file with data for benchmarking')
    parser.add_argument('--es-host', default='localhost', help='Elasticsearch host')
    parser.add_argument('--es-port', type=int, default=9200, help='Elasticsearch port')
    parser.add_argument('--index', help='Elasticsearch index pattern')
    parser.add_argument('--output', default='reports/performance_benchmark.json', help='Output file')
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark()
    
    # Benchmark preprocessing if data file provided
    if args.data_file:
        df = pd.read_csv(args.data_file)
        benchmark.benchmark_preprocessing(df)
        
        # Benchmark ML training
        benchmark.benchmark_ml_training(df, 'isolation_forest')
        
        # Benchmark ML prediction
        detector = NetworkAnomalyDetector('isolation_forest')
        detector.train(df)
        benchmark.benchmark_ml_prediction(detector, df)
        
        # Benchmark ES indexing if ES available
        try:
            from elasticsearch import Elasticsearch
            url = f"http://{args.es_host}:{args.es_port}"
            # Force HTTP by using http:// URL prefix
            # Using elasticsearch-py 8.x which is compatible with ES 8.x server
            es = Elasticsearch([url], request_timeout=30)
            if es.ping():
                benchmark.benchmark_es_indexing(es, df)
        except Exception as e:
            print(f"Could not benchmark ES indexing: {e}")
    
    # Benchmark data extraction if ES and index provided
    if args.index:
        try:
            from elasticsearch import Elasticsearch
            url = f"http://{args.es_host}:{args.es_port}"
            # Force HTTP by using http:// URL prefix
            # Using elasticsearch-py 8.x which is compatible with ES 8.x server
            es = Elasticsearch([url], request_timeout=30)
            if es.ping():
                benchmark.benchmark_data_extraction(es, args.index)
        except Exception as e:
            print(f"Could not benchmark data extraction: {e}")
    
    benchmark.print_summary()
    benchmark.save_results(args.output)

if __name__ == '__main__':
    main()
