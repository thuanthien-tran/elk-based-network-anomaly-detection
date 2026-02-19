#!/usr/bin/env python3
"""
Script to find Elasticsearch instance and test connection
"""

from elasticsearch import Elasticsearch
import sys

def test_connection(host='localhost', port=9200):
    """Test Elasticsearch connection"""
    url = f"http://{host}:{port}"
    try:
        # Force HTTP by using http:// URL prefix
        # Using elasticsearch-py 8.x which is compatible with ES 8.x server
        es = Elasticsearch([url], request_timeout=5)
        if es.ping():
            info = es.info()
            return True, info
        return False, None
    except:
        return False, None

def find_elasticsearch():
    """Try to find Elasticsearch on common ports"""
    print("Searching for Elasticsearch...")
    print("=" * 60)
    
    # Common ports
    ports = [9200, 9201, 9202, 9300]
    host = 'localhost'
    
    found = False
    
    for port in ports:
        print(f"Trying {host}:{port}...", end=" ")
        success, info = test_connection(host, port)
        
        if success:
            print("[FOUND]")
            print(f"\nElasticsearch found at: http://{host}:{port}")
            print(f"Cluster: {info.get('cluster_name', 'N/A')}")
            print(f"Version: {info.get('version', {}).get('number', 'N/A')}")
            
            # List indices
            try:
                indices = list(info.get('indices', {}).keys()) if 'indices' in info else []
                if not indices:
                    # Try to get indices another way
                    from elasticsearch import Elasticsearch
                    es = Elasticsearch([f"http://{host}:{port}"])
                    indices_response = es.cat.indices(format="json")
                    indices = [idx['index'] for idx in indices_response if not idx['index'].startswith('.')]
                
                print(f"\nAvailable indices:")
                for idx in indices[:10]:
                    print(f"  - {idx}")
                if len(indices) > 10:
                    print(f"  ... and {len(indices) - 10} more")
            except:
                pass
            
            found = True
            print(f"\nUse this in your scripts:")
            print(f"  --host {host} --port {port}")
            break
        else:
            print("[NOT FOUND]")
    
    if not found:
        print("\n[ERROR] Elasticsearch not found on common ports")
        print("\nPossible solutions:")
        print("  1. Start Elasticsearch:")
        print("     - Docker: cd docker && docker-compose up -d")
        print("     - Manual: Run elasticsearch.bat")
        print("  2. Check if running on different host/port")
        print("  3. Check Docker containers: docker ps")
    
    return found

if __name__ == '__main__':
    find_elasticsearch()
