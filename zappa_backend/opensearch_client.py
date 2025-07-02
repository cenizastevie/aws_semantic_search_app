import os
import json
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import traceback

# Configuration
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
INDEX_NAME = os.environ.get('INDEX_NAME', 'semantic-search-index')

def create_opensearch_index(endpoint=OPENSEARCH_ENDPOINT, region=AWS_REGION, index_name=INDEX_NAME):
    """
    Create OpenSearch index with k-NN settings for embeddings
    
    Args:
        endpoint (str): OpenSearch domain endpoint
        region (str): AWS region
        index_name (str): Index name
        
    Returns:
        bool: True if successful
    """
    if not endpoint:
        print("OpenSearch endpoint not configured")
        return False
    
    session = boto3.Session()
    credentials = session.get_credentials()
    if not credentials:
        raise Exception('Unable to get AWS credentials')
    
    # Index mapping with k-NN configuration
    index_mapping = {
        "settings": {
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 100
            }
        },
        "mappings": {
            "properties": {
                "title": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "content": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "summary": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "embedding": {
                    "type": "knn_vector",
                    "dimension": 1536,  # Amazon Titan Text Embedding dimensions
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "lucene",
                        "parameters": {
                            "ef_construction": 128,
                            "m": 24
                        }
                    }
                },
                "sentiment_label": {
                    "type": "keyword"
                },
                "sentiment_score": {
                    "type": "float"
                },
                "timestamp": {
                    "type": "date"
                },
                "url": {
                    "type": "keyword"
                },
                "category": {
                    "type": "keyword"
                }
            }
        }
    }
    
    try:
        # Create index
        url = f"https://{endpoint}/{index_name}"
        data = json.dumps(index_mapping)
        
        request = AWSRequest(method='PUT', url=url, data=data.encode('utf-8'))
        request.headers['Content-Type'] = 'application/json'
        request.headers['Host'] = endpoint
        SigV4Auth(credentials, 'es', region).add_auth(request)
        headers = dict(request.headers)
        
        response = requests.put(url, data=data, headers=headers)
        
        if response.ok:
            print(f"✅ Index '{index_name}' created successfully!")
            return True
        else:
            print(f"❌ Failed to create index: {response.status_code} {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating index: {str(e)}")
        print(traceback.format_exc())
        return False

def search_opensearch_by_embedding(embedding, endpoint=OPENSEARCH_ENDPOINT, region=AWS_REGION, index_name=INDEX_NAME, k=10):
    """
    Search OpenSearch using vector embedding
    
    Args:
        embedding (list): Vector embedding
        endpoint (str): OpenSearch domain endpoint
        region (str): AWS region
        index_name (str): Index name
        k (int): Number of results to return
        
    Returns:
        dict: Search results
    """
    try:
        if not endpoint:
            raise Exception("OpenSearch endpoint not configured")
            
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            raise Exception('Unable to get AWS credentials')
        
        url = f"https://{endpoint}/{index_name}/_search"
        
        # k-NN query for semantic search
        query = {
            "size": k,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": embedding,
                        "k": k
                    }
                }
            },
            "_source": ["title", "summary", "content", "sentiment_label", "sentiment_score", "category", "url", "timestamp"]
        }
        
        data = json.dumps(query)
        request = AWSRequest(method='POST', url=url, data=data.encode('utf-8'))
        request.headers['Content-Type'] = 'application/json'
        request.headers['Host'] = endpoint
        SigV4Auth(credentials, 'es', region).add_auth(request)
        headers = dict(request.headers)
        
        response = requests.post(url, data=data, headers=headers)
        
        if not response.ok:
            raise Exception(f"OpenSearch query failed: {response.status_code} {response.text}")
        
        return response.json()
        
    except Exception as e:
        print(f"Error searching OpenSearch: {str(e)}")
        print(traceback.format_exc())
        raise e

def add_document_to_opensearch(document, doc_id=None, endpoint=OPENSEARCH_ENDPOINT, region=AWS_REGION, index_name=INDEX_NAME):
    """
    Add a document to OpenSearch index
    
    Args:
        document (dict): Document to add
        doc_id (str): Document ID (optional)
        endpoint (str): OpenSearch domain endpoint
        region (str): AWS region
        index_name (str): Index name
        
    Returns:
        bool: True if successful
    """
    try:
        if not endpoint:
            raise Exception("OpenSearch endpoint not configured")
            
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            raise Exception('Unable to get AWS credentials')
        
        # Generate doc ID if not provided
        if not doc_id:
            doc_id = str(hash(document.get('title', '') + document.get('content', '')))
        
        url = f"https://{endpoint}/{index_name}/_doc/{doc_id}"
        data = json.dumps(document)
        
        request = AWSRequest(method='PUT', url=url, data=data.encode('utf-8'))
        request.headers['Content-Type'] = 'application/json'
        request.headers['Host'] = endpoint
        SigV4Auth(credentials, 'es', region).add_auth(request)
        headers = dict(request.headers)
        
        response = requests.put(url, data=data, headers=headers)
        
        if response.ok:
            print(f"✅ Document '{doc_id}' added successfully")
            return True
        else:
            print(f"❌ Failed to add document: {response.status_code} {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error adding document: {str(e)}")
        print(traceback.format_exc())
        return False

def bulk_add_documents(documents, endpoint=OPENSEARCH_ENDPOINT, region=AWS_REGION, index_name=INDEX_NAME):
    """
    Bulk add documents to OpenSearch
    
    Args:
        documents (list): List of documents
        endpoint (str): OpenSearch domain endpoint
        region (str): AWS region
        index_name (str): Index name
        
    Returns:
        bool: True if successful
    """
    try:
        if not endpoint:
            raise Exception("OpenSearch endpoint not configured")
            
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            raise Exception('Unable to get AWS credentials')
        
        # Prepare bulk data
        bulk_data = []
        for i, doc in enumerate(documents):
            # Add index operation
            bulk_data.append(json.dumps({"index": {"_index": index_name, "_id": str(i+1)}}))
            # Add document
            bulk_data.append(json.dumps(doc))
        
        bulk_body = '\n'.join(bulk_data) + '\n'
        
        url = f"https://{endpoint}/_bulk"
        
        request = AWSRequest(method='POST', url=url, data=bulk_body.encode('utf-8'))
        request.headers['Content-Type'] = 'application/x-ndjson'
        request.headers['Host'] = endpoint
        SigV4Auth(credentials, 'es', region).add_auth(request)
        headers = dict(request.headers)
        
        response = requests.post(url, data=bulk_body, headers=headers)
        
        if response.ok:
            result = response.json()
            errors = [item for item in result.get('items', []) if 'error' in item.get('index', {})]
            if errors:
                print(f"⚠️ Bulk operation completed with {len(errors)} errors")
                return False
            else:
                print(f"✅ Bulk operation completed successfully - {len(documents)} documents added")
                return True
        else:
            print(f"❌ Bulk operation failed: {response.status_code} {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error in bulk operation: {str(e)}")
        print(traceback.format_exc())
        return False

def get_index_info(endpoint=OPENSEARCH_ENDPOINT, region=AWS_REGION, index_name=INDEX_NAME):
    """
    Get information about the OpenSearch index
    
    Args:
        endpoint (str): OpenSearch domain endpoint
        region (str): AWS region
        index_name (str): Index name
        
    Returns:
        dict: Index information
    """
    try:
        if not endpoint:
            raise Exception("OpenSearch endpoint not configured")
            
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            raise Exception('Unable to get AWS credentials')
        
        # Get index stats
        stats_url = f"https://{endpoint}/{index_name}/_stats"
        request = AWSRequest(method='GET', url=stats_url)
        request.headers['Host'] = endpoint
        SigV4Auth(credentials, 'es', region).add_auth(request)
        headers = dict(request.headers)
        stats_resp = requests.get(stats_url, headers=headers)
        
        # Get index mapping
        mapping_url = f"https://{endpoint}/{index_name}/_mapping"
        request = AWSRequest(method='GET', url=mapping_url)
        request.headers['Host'] = endpoint
        SigV4Auth(credentials, 'es', region).add_auth(request)
        headers = dict(request.headers)
        mapping_resp = requests.get(mapping_url, headers=headers)
        
        return {
            "stats": stats_resp.json() if stats_resp.ok else f"Error: {stats_resp.text}",
            "mapping": mapping_resp.json() if mapping_resp.ok else f"Error: {mapping_resp.text}"
        }
        
    except Exception as e:
        print(f"Error getting index info: {str(e)}")
        return {"error": str(e)}

def test_opensearch_connection(endpoint=OPENSEARCH_ENDPOINT, region=AWS_REGION):
    """
    Test connection to OpenSearch
    
    Args:
        endpoint (str): OpenSearch domain endpoint
        region (str): AWS region
        
    Returns:
        bool: True if connection successful
    """
    try:
        if not endpoint:
            print("❌ OpenSearch endpoint not configured")
            return False
            
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            print("❌ Unable to get AWS credentials")
            return False
        
        # Test cluster health
        url = f"https://{endpoint}/_cluster/health"
        request = AWSRequest(method='GET', url=url)
        request.headers['Host'] = endpoint
        SigV4Auth(credentials, 'es', region).add_auth(request)
        headers = dict(request.headers)
        
        response = requests.get(url, headers=headers)
        
        if response.ok:
            health = response.json()
            print(f"✅ OpenSearch connection successful!")
            print(f"   Endpoint: {endpoint}")
            print(f"   Cluster status: {health.get('status', 'unknown')}")
            print(f"   Number of nodes: {health.get('number_of_nodes', 0)}")
            return True
        else:
            print(f"❌ OpenSearch connection failed: {response.status_code} {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ OpenSearch connection error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 Testing OpenSearch Connection...")
    
    if test_opensearch_connection():
        print(f"\n📊 Getting index info for '{INDEX_NAME}':")
        info = get_index_info()
        
        if "error" not in info:
            stats = info.get("stats", {})
            if isinstance(stats, dict):
                indices = stats.get("indices", {})
                if INDEX_NAME in indices:
                    index_stats = indices[INDEX_NAME]
                    doc_count = index_stats.get("total", {}).get("docs", {}).get("count", 0)
                    store_size = index_stats.get("total", {}).get("store", {}).get("size_in_bytes", 0)
                    print(f"   Documents: {doc_count}")
                    print(f"   Size: {store_size / 1024 / 1024:.2f} MB")
                else:
                    print(f"   Index '{INDEX_NAME}' does not exist")
            else:
                print(f"   Index info: {stats}")
        else:
            print(f"   Error getting index info: {info['error']}")
    else:
        print("❌ Cannot proceed - OpenSearch connection failed")
        print("\nTroubleshooting:")
        print("1. Check OPENSEARCH_ENDPOINT environment variable")
        print("2. Verify AWS credentials are configured")
        print("3. Ensure OpenSearch domain is accessible")
        print("4. Check IAM permissions for OpenSearch access")
