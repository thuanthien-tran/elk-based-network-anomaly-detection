#!/usr/bin/env python3
"""
Test script to verify Elasticsearch connection
"""

from elasticsearch import Elasticsearch
import sys

def test_connection(host='localhost', port=9200, scheme='http'):
    """Test Elasticsearch connection"""
    try:
        # Force HTTP scheme explicitly to avoid HTTPS auto-detection
        url = f"{scheme}://{host}:{port}"
        print(f"Attempting to connect to {url}...")
        
        # Force HTTP by using http:// URL prefix
        # Using elasticsearch-py 8.x which is compatible with ES 8.x server
        es = Elasticsearch([url], request_timeout=10)
        
        # Test ping with detailed error handling
        try:
            ping_result = es.ping()
            if ping_result:
                print("[OK] Successfully connected to Elasticsearch!")
                
                # Get cluster info
                info = es.info()
                print(f"\nCluster Info:")
                print(f"  Name: {info.get('cluster_name', 'N/A')}")
                print(f"  Version: {info.get('version', {}).get('number', 'N/A')}")
                
                # List indices
                try:
                    indices = es.indices.get_alias(index="*")
                    print(f"\nFound {len(indices)} indices")
                    if indices:
                        print("Sample indices:")
                        for idx in list(indices.keys())[:5]:
                            print(f"  - {idx}")
                except Exception as e:
                    print(f"\nNote: Could not list indices: {e}")
                
                return True
            else:
                print("[ERROR] Connection failed - ping returned False")
                # Try to get more info
                try:
                    info = es.info()
                    print(f"  But info() succeeded: {info.get('cluster_name', 'N/A')}")
                except Exception as e2:
                    print(f"  info() also failed: {e2}")
                return False
        except Exception as ping_error:
            print(f"[ERROR] Ping failed with exception: {ping_error}")
            print(f"  Error type: {type(ping_error).__name__}")
            import traceback
            print(f"  Traceback:\n{traceback.format_exc()}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        print(f"  Error type: {type(e).__name__}")
        import traceback
        print(f"  Full traceback:\n{traceback.format_exc()}")
        print(f"\nTroubleshooting:")
        print(f"  1. Check if Elasticsearch is running: docker ps")
        print(f"  2. Test with curl: curl http://{host}:{port}")
        print(f"  3. Verify host and port: {host}:{port}")
        print(f"  4. Check firewall settings")
        return False

if __name__ == '__main__':
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9200
    scheme = sys.argv[3] if len(sys.argv) > 3 else 'http'
    
    success = test_connection(host, port, scheme=scheme)
    sys.exit(0 if success else 1)
