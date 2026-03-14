#!/usr/bin/env python3
"""
Script to extract logs from Elasticsearch for ML processing
"""

from elasticsearch import Elasticsearch
import elasticsearch as _es_pkg
from datetime import datetime, timedelta, timezone
import pandas as pd
import json
import argparse
import sys

def connect_elasticsearch(host='localhost', port=9200, scheme='http', retries=3, retry_delay=2):
    """Connect to Elasticsearch with retries (robustness: transient failures)."""
    import time
    url = f"{scheme}://{host}:{port}"
    print(f"Connecting to Elasticsearch at {url}...")
    last_error = None
    major = 0
    try:
        major = int(getattr(_es_pkg, "__version__", (0,))[0])
    except Exception:
        major = 0
    if major >= 9:
        raise RuntimeError(
            "Ban dang dung elasticsearch-py v9 (khong tuong thich voi Elasticsearch 8.x).\n"
            "Fix (khuyen nghi): py -3 -m pip uninstall -y elasticsearch && py -3 -m pip install \"elasticsearch>=8,<9\""
        )
    for attempt in range(1, retries + 1):
        try:
            es = Elasticsearch([url], request_timeout=10)
            # Use info() instead of ping() for better compatibility
            info = es.info()
            print(f"[OK] Successfully connected to Elasticsearch at {url}")
            try:
                print(f"  Cluster: {info.get('cluster_name', 'N/A')}")
                print(f"  Version: {info.get('version', {}).get('number', 'N/A')}")
            except Exception:
                pass
            return es
        except Exception as e:
            last_error = e
            if attempt < retries:
                print(f"  Attempt {attempt}/{retries} failed: {e}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                break
    error_msg = str(last_error) if last_error else "unknown"
    print(f"\n[ERROR] Cannot connect to Elasticsearch at {url} after {retries} attempts")
    print("\nPossible causes:")
    print("  1. Elasticsearch server is not running")
    print("  2. Wrong host or port")
    print("  3. Firewall blocking connection")
    print(f"\nTo test: curl http://{host}:{port}")
    raise Exception(f"Cannot connect to Elasticsearch at {url}: {error_msg}")

def extract_logs(es, index_pattern, start_time, end_time, size=10000, batch_size=1000, max_total_docs=0):
    """
    Extract logs from Elasticsearch with proper scroll handling.

    Args:
        es: Elasticsearch client
        index_pattern: Index pattern to search
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        size: Initial scroll size per request
        batch_size: Batch size for yielding to avoid memory issues
        max_total_docs: Cap total documents (0 = no limit). Use e.g. 500000 to avoid OOM on large indices.
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
        total_so_far = 0
        while len(hits) > 0:
            for hit in hits:
                logs.append(hit['_source'])
                total_so_far += 1
                if max_total_docs and total_so_far >= max_total_docs:
                    break
            if max_total_docs and total_so_far >= max_total_docs:
                break
            if len(logs) >= batch_size:
                yield logs
                logs = []
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
    
    # Extract user: "for user1", "for invalid user admin", "publickey for jhall from", "session opened for user X"
    user_patterns = [
        r'for\s+(?:invalid\s+)?user\s+(\S+)',   # "for invalid user admin" or "for user admin"
        r'password for\s+(\S+)\s+from',         # "Accepted/Failed password for user1 from"
        r'publickey for\s+(\S+)\s+from',       # "Accepted publickey for jhall from"
        r'session opened for user\s+(\S+)',     # pam_unix(sshd:session): session opened for user jhall
        r'session closed for user\s+(\S+)',
        r'Successful su for\s+(\S+)\s+by',     # su[27950]: Successful su for jhall by www-data
        r'user\s+(\S+)',                        # Fallback
    ]
    for pattern in user_patterns:
        user_match = re.search(pattern, message, re.IGNORECASE)
        if user_match:
            user = user_match.group(1)
            break
    
    # Extract status: "Failed password", "Accepted password", "Accepted publickey", session, su, sudo, etc.
    if 'failed password' in message.lower():
        status = 'failed'
        is_attack = True
        attack_type = 'brute_force'
    elif 'accepted password' in message.lower():
        status = 'accepted'
        is_attack = False
    elif 'accepted publickey' in message.lower():
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
    elif 'session opened for user' in message.lower() or 'session closed for user' in message.lower():
        status = 'session'
        is_attack = False
    elif 'successful su for' in message.lower() or 'su for' in message.lower():
        status = 'su'
        is_attack = False  # labels may override for attacker escalation
    elif 'sudo:' in message.lower() or 'pam_unix(sudo:session)' in message.lower():
        status = 'sudo'
        is_attack = False
    elif 'did not receive identification' in message.lower():
        status = 'connection_refused'
        is_attack = False
    elif 'disconnected from' in message.lower() or 'received disconnect' in message.lower():
        status = 'disconnect'
        is_attack = False
    
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
            clientip = log.get('clientip', '') or log.get('source', {}).get('ip', '')
            record = {
                'timestamp': log.get('@timestamp'),
                'source_ip': clientip,
                'clientip': clientip,
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
            clientip = log.get('clientip', '')
            record = {
                'timestamp': log.get('@timestamp'),
                'source_ip': clientip,
                'clientip': clientip,
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
    parser.add_argument('--index', default=None,
                       help='Index pattern (e.g. ssh-logs-*, web-logs-*, test-logs-*). Default: ssh-logs-* for --log-type ssh, web-logs-* for web, required for all')
    parser.add_argument('--output', required=True, help='Output CSV file')
    parser.add_argument('--hours', type=int, default=24, help='Number of hours to extract')
    parser.add_argument('--max-docs', type=int, default=0, help='Max documents to extract (0=no limit; use e.g. 500000 to avoid OOM)')
    parser.add_argument('--log-type', choices=['ssh', 'web', 'all'], default='all',
                       help='Type of logs to extract (used for parsing and default index)')
    parser.add_argument('--skip-connection-check', action='store_true',
                       help='Skip Elasticsearch connection check (for testing)')
    
    args = parser.parse_args()
    
    # Default index by log-type (per DU_KIEN_DATASET: ssh-logs-*, web-logs-*)
    index_pattern = args.index
    if index_pattern is None:
        if args.log_type == 'ssh':
            index_pattern = 'ssh-logs-*'
        elif args.log_type == 'web':
            index_pattern = 'web-logs-*'
        else:
            print("[ERROR] --index is required when --log-type is 'all'. Example: --index test-logs-*")
            sys.exit(1)
    args.index = index_pattern
    
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
    
    # List indices matching pattern (help debug when 0 docs)
    try:
        matching = es.indices.get(index=args.index)
        names = [k for k in (matching or {}) if not k.startswith('.')]
        if names:
            print(f"  Indices matching '{args.index}': {', '.join(sorted(names))}")
        else:
            cat = es.cat.indices(format="json")
            existing = [x.get("index", "") for x in (cat or []) if x.get("index", "") and not x.get("index", "").startswith(".")]
            print(f"  No indices match '{args.index}'. Existing: {', '.join(sorted(existing)[:25])}")
            print("  => Chay [4] Filebeat va giu cua so mo, tao log [5]/[10], doi 15s roi thu lai.")
    except Exception as e:
        print(f"  (Kiem tra index: {e})")
    
    # Calculate time range (use UTC to match Elasticsearch)
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=args.hours)
    
    # Format as ISO 8601 with Z suffix for UTC
    start_time_iso = start_time.isoformat().replace('+00:00', 'Z')
    end_time_iso = end_time.isoformat().replace('+00:00', 'Z')
    
    print(f"Extracting logs from {start_time} (UTC) to {end_time} (UTC)")
    print(f"  ISO format: {start_time_iso} to {end_time_iso}")
    
    # Extract logs in batches
    all_logs = []
    batch_count = 0
    for batch_logs in extract_logs(es, args.index, start_time_iso, end_time_iso, max_total_docs=getattr(args, 'max_docs', 0)):
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
        print("  1. Index pattern matches existing indices (thu: test-logs-* hoac ssh-logs-*)")
        print("  2. Time range contains logs")
        print("  3. Filebeat and Logstash are running; logs in C:\\Users\\...\\Documents\\test.log")
        sys.exit(1)

if __name__ == '__main__':
    main()
