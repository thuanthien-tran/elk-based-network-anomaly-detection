#!/usr/bin/env python3
"""
Script to write ML detection results back to Elasticsearch
"""

from elasticsearch import Elasticsearch
import pandas as pd
import argparse
import sys
from datetime import datetime
import json
import hashlib

def connect_elasticsearch(host='localhost', port=9200, scheme='http', request_timeout=300, retries=3, retry_delay=2):
    """Connect to Elasticsearch with retries. request_timeout=300 (5 phut) cho bulk index nhieu document."""
    import time
    url = f"{scheme}://{host}:{port}"
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            es = Elasticsearch([url], request_timeout=request_timeout)
            if es.ping():
                print(f"Connected to Elasticsearch at {url}")
                return es
            raise Exception("Ping failed")
        except Exception as e:
            last_error = e
            if attempt < retries:
                print(f"  Attempt {attempt}/{retries} failed: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
    raise Exception(f"Cannot connect to Elasticsearch at {url}: {last_error}")

def write_results(es, df, index_name='ml-alerts', refresh='wait_for', check_duplicates=True, model_name=None):
    """
    Write ML detection results to Elasticsearch

    Args:
        es: Elasticsearch client
        df: DataFrame with results
        index_name: Base index name
        refresh: Refresh policy ('wait_for', 'false', 'true')
        check_duplicates: Check for duplicate documents
        model_name: Ten model/pipeline de phan biet tren Kibana (vd: unified, russellmitchell, csv)
    """
    df = df.copy()
    if model_name is not None:
        df['ml_model'] = model_name
    index_pattern = f"{index_name}-{datetime.now().strftime('%Y.%m.%d')}"
    
    # Create index if not exists
    if not es.indices.exists(index=index_pattern):
        mappings = {
            "properties": {
                "@timestamp": {"type": "date"},
                "source_ip": {"type": "keyword"},
                "ml_anomaly": {"type": "boolean"},
                "ml_anomaly_score": {"type": "float"},
                "ml_model": {"type": "keyword"},
                "is_attack": {"type": "boolean"},
                "attack_type": {"type": "keyword"},
                "defense_recommendations": {"type": "keyword"},
                "geoip": {
                    "properties": {
                        "country_name": {"type": "keyword"},
                        "city_name": {"type": "keyword"}
                    }
                }
            }
        }
        settings = {"refresh_interval": "30s"}
        try:
            es.indices.create(index=index_pattern, mappings=mappings, settings=settings)
        except TypeError:
            es.indices.create(index=index_pattern, body={"mappings": mappings, "settings": settings})
        print(f"Created index: {index_pattern}")
    else:
        # Check if mapping needs update (handle conflicts)
        try:
            current_mapping = es.indices.get_mapping(index=index_pattern)
            # If needed, update mapping dynamically
        except Exception as e:
            print(f"Warning: Could not check mapping: {e}")
    
    # Add defense recommendations by attack_type
    try:
        try:
            from scripts.defense_recommendations import add_recommendations_to_dataframe
        except ImportError:
            from defense_recommendations import add_recommendations_to_dataframe
        df = add_recommendations_to_dataframe(df.copy())
    except Exception as e:
        print(f"Warning: could not add defense_recommendations: {e}")
    
    # Convert DataFrame to documents
    documents = []
    seen_ids = set()  # For duplicate checking
    
    for _, row in df.iterrows():
        doc = row.to_dict()
        
        # Ensure timestamp field with proper ISO 8601 format
        if 'timestamp' in doc:
            timestamp_value = doc['timestamp']
            # Convert to ISO 8601 format if needed
            if isinstance(timestamp_value, str):
                # Try to parse and reformat
                try:
                    from dateutil import parser
                    dt = parser.parse(timestamp_value)
                    doc['@timestamp'] = dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                except:
                    # If parsing fails, try to fix common formats
                    timestamp_str = str(timestamp_value)
                    # Replace space with T and ensure Z at end
                    if ' ' in timestamp_str and 'T' not in timestamp_str:
                        timestamp_str = timestamp_str.replace(' ', 'T')
                    if not timestamp_str.endswith('Z') and '+' not in timestamp_str:
                        timestamp_str = timestamp_str + 'Z'
                    doc['@timestamp'] = timestamp_str
            else:
                doc['@timestamp'] = timestamp_value
        elif '@timestamp' in doc:
            # Fix existing @timestamp if needed
            timestamp_value = doc['@timestamp']
            if isinstance(timestamp_value, str) and ' ' in timestamp_value and 'T' not in timestamp_value:
                try:
                    from dateutil import parser
                    dt = parser.parse(timestamp_value)
                    doc['@timestamp'] = dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                except:
                    timestamp_str = str(timestamp_value).replace(' ', 'T')
                    if not timestamp_str.endswith('Z') and '+' not in timestamp_str:
                        timestamp_str = timestamp_str + 'Z'
                    doc['@timestamp'] = timestamp_str
        else:
            doc['@timestamp'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        # Convert boolean fields from int (0/1) to bool (True/False) for Elasticsearch
        boolean_fields = ['ml_anomaly', 'is_attack']
        for field in boolean_fields:
            if field in doc:
                value = doc[field]
                # Convert int/float to bool
                if isinstance(value, (int, float)):
                    doc[field] = bool(value)
                # Convert string '0'/'1' to bool
                elif isinstance(value, str):
                    doc[field] = value.lower() in ('true', '1', 'yes')
                # Already bool, keep as is
                elif isinstance(value, bool):
                    doc[field] = value
        
        # Clean up source_ip - remove invalid values
        if 'source_ip' in doc:
            source_ip = doc['source_ip']
            if isinstance(source_ip, str):
                # Remove empty strings, 'unknown', 'null', etc.
                if source_ip.lower() in ('', 'unknown', 'null', 'none', 'nan'):
                    doc['source_ip'] = None
                # Validate IP format (basic check)
                elif '.' not in source_ip and ':' not in source_ip:
                    doc['source_ip'] = None
        
        # Format geoip if exists
        if 'geoip_country' in doc or 'geoip_city' in doc:
            doc['geoip'] = {
                'country_name': doc.get('geoip_country', ''),
                'city_name': doc.get('geoip_city', '')
            }
        
        # Create document ID for duplicate checking
        if check_duplicates:
            # Use timestamp + source_ip + ml_anomaly_score as unique identifier
            doc_id = f"{doc.get('@timestamp', '')}_{doc.get('source_ip', '')}_{doc.get('ml_anomaly_score', 0)}"
            if doc_id in seen_ids:
                continue  # Skip duplicate
            seen_ids.add(doc_id)
        
        documents.append(doc)
    
    print(f"Prepared {len(documents)} documents for indexing")
    
    # Bulk insert with progress bar
    from elasticsearch.helpers import streaming_bulk

    total = len(documents)
    chunk_size = 100
    bar_width = 30

    def doc_generator():
        for doc in documents:
            action = {
                "_index": index_pattern,
                "_source": doc
            }
            if check_duplicates:
                doc_id = f"{doc.get('@timestamp', '')}_{doc.get('source_ip', '')}_{doc.get('ml_anomaly_score', 0)}"
                action["_id"] = hashlib.md5(doc_id.encode()).hexdigest()
            yield action

    # Dung refresh='false' de tranh dung khi cho ES refresh (wait_for rat lau o chunk cuoi)
    failed_list = []
    for i, (ok, item) in enumerate(streaming_bulk(
        es,
        doc_generator(),
        chunk_size=chunk_size,
        raise_on_error=False,
        refresh="false"
    )):
        if not ok and isinstance(item, dict) and "items" in item:
            for x in item.get("items", []):
                idx = x.get("index", {})
                if idx.get("error"):
                    failed_list.append(x)
        current = min((i + 1) * chunk_size, total)
        pct = (current * 100) // total
        filled = (bar_width * current) // total if total else 0
        bar = "#" * filled + "-" * (bar_width - filled)
        print(f"\r  Dang ghi ES: [{bar}] {current}/{total} ({pct}%)", end="", flush=True)
    print()
    success = total - len(failed_list)
    print(f"Successfully indexed {success} documents")
    print("  (Du lieu hien trong Kibana trong vai giay, hoac bam Refresh.)")
    if failed_list:
        print(f"Failed to index {len(failed_list)} documents")
        for item in failed_list[:5]:
            print(f"  Error: {item.get('index', {}).get('error', {})}")
    return index_pattern

def main():
    parser = argparse.ArgumentParser(description='Write ML results to Elasticsearch')
    parser.add_argument('--input', required=True, help='Input CSV file with ML predictions')
    parser.add_argument('--host', default='localhost', help='Elasticsearch host')
    parser.add_argument('--port', type=int, default=9200, help='Elasticsearch port')
    parser.add_argument('--index', default='ml-alerts', help='Index name pattern')
    parser.add_argument('--filter-anomalies', action='store_true',
                       help='Only write records marked as anomalies')
    parser.add_argument('--refresh', choices=['wait_for', 'false', 'true'],
                       default='wait_for', help='Refresh policy')
    parser.add_argument('--no-check-duplicates', action='store_true',
                       help='Skip duplicate checking')
    parser.add_argument('--model-name', default='', metavar='NAME',
                       help='Ten model/pipeline (ghi vao truong ml_model de phan biet tren Kibana, vd: unified, russellmitchell, csv)')
    
    args = parser.parse_args()
    
    # Connect to Elasticsearch
    es = connect_elasticsearch(args.host, args.port, scheme='http')
    
    # Load data
    print(f"Loading data from {args.input}...")
    df = pd.read_csv(args.input)
    print(f"Loaded {len(df)} records")
    
    # Them truong phan biet model/pipeline tren Kibana
    if args.model_name:
        df['ml_model'] = args.model_name
    
    # Filter anomalies if requested
    if args.filter_anomalies and 'ml_anomaly' in df.columns:
        # Handle both int (0/1) and bool (True/False) formats
        if df['ml_anomaly'].dtype == bool:
            df = df[df['ml_anomaly'] == True]
        else:
            df = df[df['ml_anomaly'] == 1]
        print(f"Filtered to {len(df)} anomaly records")
    
    # Write to Elasticsearch
    try:
        index_name = write_results(
            es,
            df,
            args.index,
            refresh=args.refresh,
            check_duplicates=not args.no_check_duplicates
        )
        print(f"\nResults written to index: {index_name}")
        print(f"You can view them in Kibana with index pattern: {args.index}-*")
    except Exception as e:
        print(f"\n[ERROR] Ghi Elasticsearch that bai: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
