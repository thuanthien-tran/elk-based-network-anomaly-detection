#!/usr/bin/env python3
"""Quick script to verify ML alerts in Elasticsearch"""

from elasticsearch import Elasticsearch
import sys

def main():
    host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9200
    
    es = Elasticsearch([f'http://{host}:{port}'])
    
    # Search ML alerts
    result = es.search(
        index='ml-alerts-*',
        body={'query': {'match_all': {}}, 'size': 10}
    )
    
    total = result['hits']['total']['value']
    print(f"Total ML alerts: {total}")
    print("\nSample documents:")
    print("=" * 80)
    
    for i, hit in enumerate(result['hits']['hits'][:5], 1):
        source = hit['_source']
        print(f"\nDocument {i}:")
        print(f"  ml_anomaly: {source.get('ml_anomaly')} (type: {type(source.get('ml_anomaly')).__name__})")
        print(f"  is_attack: {source.get('is_attack')} (type: {type(source.get('is_attack')).__name__})")
        print(f"  source_ip: {source.get('source_ip')}")
        print(f"  ml_anomaly_score: {source.get('ml_anomaly_score')}")
        print(f"  attack_type: {source.get('attack_type')}")
    
    # Count anomalies
    anomaly_result = es.search(
        index='ml-alerts-*',
        body={'query': {'term': {'ml_anomaly': True}}, 'size': 0}
    )
    anomaly_count = anomaly_result['hits']['total']['value']
    print(f"\n{'=' * 80}")
    print(f"Total anomalies (ml_anomaly=True): {anomaly_count}")

if __name__ == '__main__':
    main()
