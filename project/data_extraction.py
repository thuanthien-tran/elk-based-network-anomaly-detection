#!/usr/bin/env python3
"""
Script to extract logs from Elasticsearch for ML processing
"""

from elasticsearch import Elasticsearch
from datetime import datetime, timedelta
import pandas as pd
import json
import argparse
import sys

def connect_elasticsearch(host='localhost', port=9200, scheme='http'):
    """Connect to Elasticsearch"""
    # Force HTTP scheme explicitly to avoid HTTPS auto-detection
    url = f"{scheme}://{host}:{port}"
    
    print(f"Connecting to Elasticsearch at {url}...")
    
    try:
        # Force HTTP by using http:// URL prefix
        # Using elasticsearch-py 8.x which is compatible with ES 8.x server
        es = Elasticsearch([url], request_timeout=10)
        
        # Test connection
        if not es.ping():
            print(f"[ERROR] Cannot connect to Elasticsearch at {url}")
            print("\nTroubleshooting:")
            print("  1. Check if Elasticsearch is running")
            print(f"     Test: curl http://{host}:{port}")
            print("  2. Verify host and port are correct")
            print("  3. Check firewall settings")
            print("  4. If using Docker, ensure container is running")
            raise Exception(f"Cannot connect to Elasticsearch at {url} - ping failed")
        
        print(f"[OK] Successfully connected to Elasticsearch at {url}")
        
        # Get cluster info
        try:
            info = es.info()
            print(f"  Cluster: {info.get('cluster_name', 'N/A')}")
            print(f"  Version: {info.get('version', {}).get('number', 'N/A')}")
        except:
            pass
        
        return es
        
    except Exception as e:
        error_msg = str(e)
        if "Connection refused" in error_msg or "ping failed" in error_msg:
            print(f"\n[ERROR] Cannot connect to Elasticsearch at {url}")
            print("\nPossible causes:")
            print("  1. Elasticsearch server is not running")
            print("  2. Wrong host or port")
            print("  3. Firewall blocking connection")
            print("  4. Elasticsearch is running on different port")
            print("\nTo test connection manually:")
            print(f"  curl http://{host}:{port}")
            print(f"  Or: python scripts/test_elasticsearch_connection.py {host} {port}")
        raise Exception(f"Cannot connect to Elasticsearch at {url}: {error_msg}")

def extract_logs(es, index_pattern, start_time, end_time, size=10000, batch_size=1000):
    """
    Extract logs from Elasticsearch with proper scroll handling
    
    Args:
        es: Elasticsearch client
        index_pattern: Index pattern to search
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        size: Initial scroll size
        batch_size: Batch size for processing to avoid memory issues
    """
    # Query for Elasticsearch 9.x (query structure)
    query_dict = {
        "range": {
            "@timestamp": {
                "gte": start_time,
                "lte": end_time
            }
        }
    }
    
    logs = []
    scroll_id = None
    
    try:
        # Initial search (Elasticsearch 8.x uses query parameter)
        response = es.search(
            index=index_pattern, 
            query=query_dict,
            size=size,
            scroll='2m'
        )
        scroll_id = response.get('_scroll_id')
        
        # Process initial batch
        hits = response['hits']['hits']
        while len(hits) > 0:
            for hit in hits:
                logs.append(hit['_source'])
            
            # Process in batches to avoid memory issues
            if len(logs) >= batch_size:
                yield logs
                logs = []
            
            # Continue scrolling
            try:
                response = es.scroll(scroll_id=scroll_id, scroll='2m')
                scroll_id = response.get('_scroll_id')
                hits = response['hits']['hits']
            except Exception as e:
                print(f"Error during scroll: {e}")
                break
        
        # Yield remaining logs
        if logs:
            yield logs
            
    except Exception as e:
        print(f"Error during extraction: {e}")
        raise
    finally:
        # Clear scroll context
        if scroll_id:
            try:
                es.clear_scroll(scroll_id=scroll_id)
            except Exception as e:
                print(f"Warning: Could not clear scroll: {e}")

def get_log_type(log):
    """Get log_type from log, checking both top-level and fields.log_type"""
    # Check top-level
    log_type = log.get('log_type')
    if log_type:
        return log_type
    
    # Check fields.log_type (Filebeat format)
    fields = log.get('fields', {})
    if isinstance(fields, dict):
        log_type = fields.get('log_type')
        if log_type:
            return log_type
    
    # Try to infer from message content
    message = log.get('message', '')
    if 'ssh' in message.lower() or 'sshd' in message.lower():
        return 'ssh'
    elif 'http' in message.lower() or 'GET' in message or 'POST' in message:
        return 'web'
    
    return None

def parse_ssh_message(message):
    """Parse SSH log message to extract IP, user, status, and attack info"""
    import re
    
    source_ip = ''
    user = ''
    status = ''
    is_attack = False
    attack_type = ''
    
    if not message:
        return source_ip, user, status, is_attack, attack_type
    
    # Extract IP address: "from 192.168.1.101" or "from 10.10.10.10"
    ip_patterns = [
        r'from\s+([\d\.]+)',  # Standard: "from 192.168.1.101"
        r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',  # Any IP in message
    ]
    for pattern in ip_patterns:
        ip_match = re.search(pattern, message)
        if ip_match:
            source_ip = ip_match.group(1)
            break
    
    # Extract user: "for user1" or "for invalid user admin"
    user_patterns = [
        r'for\s+(?:invalid\s+)?user\s+(\S+)',  # "for user1" or "for invalid user admin"
        r'user\s+(\S+)',  # Fallback: "user hacker"
    ]
    for pattern in user_patterns:
        user_match = re.search(pattern, message, re.IGNORECASE)
        if user_match:
            user = user_match.group(1)
            break
    
    # Extract status: "Failed password" or "Accepted password"
    if 'failed password' in message.lower():
        status = 'failed'
        is_attack = True
        attack_type = 'brute_force'
    elif 'accepted password' in message.lower():
        status = 'accepted'
        is_attack = False
    elif 'authentication failure' in message.lower():
        status = 'failed'
        is_attack = True
        attack_type = 'brute_force'
    elif 'invalid user' in message.lower():
        status = 'invalid_user'
        is_attack = True
        attack_type = 'brute_force'
    
    return source_ip, user, status, is_attack, attack_type

def parse_ssh_logs(logs):
    """Parse SSH logs into structured format"""
    data = []
    for log in logs:
        log_type = get_log_type(log)
        message = log.get('message', '')
        
        # Check if this is an SSH log
        is_ssh = False
        if log_type and ('ssh' in log_type.lower()):
            is_ssh = True
        elif 'ssh' in message.lower() or 'sshd' in message.lower():
            is_ssh = True
        
        if is_ssh:
            # Try to get fields from log first
            source_ip = log.get('source_ip') or (log.get('source', {}).get('ip', '') if isinstance(log.get('source'), dict) else '')
            user = log.get('user', '')
            status = log.get('status', '')
            is_attack = log.get('is_attack', False)
            attack_type = log.get('attack_type', '')
            
            # Parse from message if fields not present
            parsed_ip, parsed_user, parsed_status, parsed_is_attack, parsed_attack_type = parse_ssh_message(message)
            
            # Use parsed values if original fields are empty
            if not source_ip:
                source_ip = parsed_ip
            if not user:
                user = parsed_user
            if not status:
                status = parsed_status
            if not attack_type and parsed_attack_type:
                attack_type = parsed_attack_type
            # Always use parsed is_attack if it's True (more accurate)
            if parsed_is_attack:
                is_attack = True
            
            record = {
                'timestamp': log.get('@timestamp'),
                'source_ip': source_ip,
                'user': user,
                'status': status,
                'message': message,
                'attack_type': attack_type,
                'is_attack': is_attack,
                'geoip_country': log.get('geoip', {}).get('country_name', '') if isinstance(log.get('geoip'), dict) else '',
                'geoip_city': log.get('geoip', {}).get('city_name', '') if isinstance(log.get('geoip'), dict) else '',
                'log_type': log_type or 'ssh',
            }
            data.append(record)
    
    return pd.DataFrame(data)

def parse_web_logs(logs):
    """Parse web logs into structured format"""
    data = []
    for log in logs:
        log_type = get_log_type(log)
        message = log.get('message', '')
        
        # Check if this is a web log
        if log_type == 'web' or 'web' in (log_type or '').lower():
            record = {
                'timestamp': log.get('@timestamp'),
                'clientip': log.get('clientip', '') or log.get('source', {}).get('ip', ''),
                'request': log.get('request', ''),
                'response': log.get('response', ''),
                'bytes': log.get('bytes', 0),
                'verb': log.get('verb', ''),
                'message': message,
                'is_attack': log.get('is_attack', False),
                'attack_type': log.get('attack_type', ''),
                'geoip_country': log.get('geoip', {}).get('country_name', '') if isinstance(log.get('geoip'), dict) else '',
                'log_type': log_type or 'web',
            }
            data.append(record)
        elif 'http' in message.lower() or 'GET' in message or 'POST' in message:
            # Fallback: if message contains HTTP keywords, treat as web log
            record = {
                'timestamp': log.get('@timestamp'),
                'clientip': log.get('clientip', ''),
                'request': log.get('request', ''),
                'response': log.get('response', ''),
                'bytes': log.get('bytes', 0),
                'verb': log.get('verb', ''),
                'message': message,
                'is_attack': log.get('is_attack', False),
                'attack_type': log.get('attack_type', ''),
                'geoip_country': '',
                'log_type': 'web',
            }
            data.append(record)
    return pd.DataFrame(data)

def parse_raw_logs(logs):
    """Parse all logs into a generic format - extracts everything"""
    data = []
    for log in logs:
        log_type = get_log_type(log)
        message = log.get('message', '')
        
        # Try to get fields from log first
        source_ip = log.get('source_ip') or (log.get('source', {}).get('ip', '') if isinstance(log.get('source'), dict) else '')
        user = log.get('user', '')
        status = log.get('status', '')
        is_attack = log.get('is_attack', False)
        attack_type = log.get('attack_type', '')
        
        # If this looks like SSH log, parse from message
        if 'ssh' in (log_type or '').lower() or 'ssh' in message.lower() or 'sshd' in message.lower():
            parsed_ip, parsed_user, parsed_status, parsed_is_attack, parsed_attack_type = parse_ssh_message(message)
            if not source_ip:
                source_ip = parsed_ip
            if not user:
                user = parsed_user
            if not status:
                status = parsed_status
            if parsed_is_attack:
                is_attack = True
            if parsed_attack_type:
                attack_type = parsed_attack_type
        
        # Create a generic record with all available fields
        record = {
            'timestamp': log.get('@timestamp'),
            'message': message,
            'log_type': log_type or 'unknown',
            'source_ip': source_ip,
            'clientip': log.get('clientip', ''),
            'user': user,
            'status': status,
            'request': log.get('request', ''),
            'response': log.get('response', ''),
            'bytes': log.get('bytes', 0),
            'verb': log.get('verb', ''),
            'is_attack': is_attack,
            'attack_type': attack_type,
            'geoip_country': log.get('geoip', {}).get('country_name', '') if isinstance(log.get('geoip'), dict) else '',
            'geoip_city': log.get('geoip', {}).get('city_name', '') if isinstance(log.get('geoip'), dict) else '',
        }
        
        # Add any additional fields from the log
        for key, value in log.items():
            if key not in record and key not in ['@timestamp', 'message', 'fields', 'geoip', 'source']:
                if isinstance(value, (str, int, float, bool)):
                    record[key] = value
        
        data.append(record)
    return pd.DataFrame(data)

def main():
    parser = argparse.ArgumentParser(description='Extract logs from Elasticsearch')
    parser.add_argument('--host', default='localhost', help='Elasticsearch host')
    parser.add_argument('--port', type=int, default=9200, help='Elasticsearch port')
    parser.add_argument('--index', required=True, help='Index pattern (e.g., ssh-logs-*)')
    parser.add_argument('--output', required=True, help='Output CSV file')
    parser.add_argument('--hours', type=int, default=24, help='Number of hours to extract')
    parser.add_argument('--log-type', choices=['ssh', 'web', 'all'], default='all', 
                       help='Type of logs to extract')
    parser.add_argument('--skip-connection-check', action='store_true',
                       help='Skip Elasticsearch connection check (for testing)')
    
    args = parser.parse_args()
    
    # Connect to Elasticsearch (force HTTP scheme)
    try:
        es = connect_elasticsearch(args.host, args.port, scheme='http')
    except Exception as e:
        if args.skip_connection_check:
            print(f"[WARNING] Connection failed but continuing: {e}")
            print("[INFO] This script requires a running Elasticsearch server.")
            return
        else:
            print(f"\n[ERROR] {e}")
            print("\nIf you don't have Elasticsearch running, you can:")
            print("  1. Start Elasticsearch server")
            print("  2. Use Docker: docker-compose up -d (from docker/ directory)")
            print("  3. Or skip connection check: --skip-connection-check (for testing)")
            sys.exit(1)
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=args.hours)
    
    print(f"Extracting logs from {start_time} to {end_time}")
    
    # Extract logs in batches
    all_logs = []
    batch_count = 0
    for batch_logs in extract_logs(es, args.index, start_time.isoformat(), end_time.isoformat()):
        all_logs.extend(batch_logs)
        batch_count += 1
        print(f"Processed batch {batch_count}, total logs: {len(all_logs)}")
    
    print(f"Extracted {len(all_logs)} log entries in {batch_count} batches")
    
    # Parse logs based on type
    if args.log_type == 'ssh':
        df = parse_ssh_logs(all_logs)
    elif args.log_type == 'web':
        df = parse_web_logs(all_logs)
    else:
        # For 'all', use raw parser to extract everything
        # This ensures we don't lose any logs due to filtering
        df = parse_raw_logs(all_logs)
        
        # Also try to parse SSH and web logs separately for better structure
        ssh_df = parse_ssh_logs(all_logs)
        web_df = parse_web_logs(all_logs)
        
        # If we have structured logs, prefer them; otherwise use raw
        if len(ssh_df) > 0 or len(web_df) > 0:
            combined = []
            if len(ssh_df) > 0:
                combined.append(ssh_df)
            if len(web_df) > 0:
                combined.append(web_df)
            if combined:
                df = pd.concat(combined, ignore_index=True)
    
    # Save to CSV
    df.to_csv(args.output, index=False)
    print(f"Saved {len(df)} records to {args.output}")
    
    # Print statistics
    if len(df) > 0 and len(df.columns) > 0:
        print("\nStatistics:")
        print(df.describe())
        if 'is_attack' in df.columns:
            print(f"\nAttack detection: {df['is_attack'].sum()} attacks found")
    else:
        print("\nNo data extracted. Check:")
        print("  1. Index pattern matches existing indices")
        print("  2. Time range contains logs")
        print("  3. Logs match the specified log-type filter")

if __name__ == '__main__':
    main()
