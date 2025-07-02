import os
import json
import boto3
from flask import Flask, request, jsonify
from zappa.asynchronous import task
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import traceback

# Load environment variables
if os.environ.get('LAMBDA_TASK_ROOT') is None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    except Exception as e:
        pass

app = Flask(__name__)

# Configuration
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT')
WEBSOCKET_API_ENDPOINT = os.environ.get('WEBSOCKET_API_ENDPOINT')
MODEL_ID = os.environ.get('MODEL_ID', 'amazon.titan-embed-text-v1')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
INDEX_NAME = os.environ.get('INDEX_NAME', 'semantic-search-index')

# Initialize clients
apigw_management_client = None
if WEBSOCKET_API_ENDPOINT:
    apigw_management_client = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=WEBSOCKET_API_ENDPOINT
    )

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = "*"
    response.headers['Access-Control-Allow-Headers'] = "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
    response.headers['Access-Control-Allow-Methods'] = "OPTIONS,POST,GET"
    return response

@app.route('/')
def hello_world():
    return 'Hello, Semantic Search Backend!'

@app.route('/search', methods=['POST', 'OPTIONS'])
def search_endpoint():
    """Direct search endpoint for testing"""
    if request.method == 'OPTIONS':
        return '', 204

    try:
        body = request.json
        if not body or 'query' not in body:
            return jsonify(error='Missing query in request body.'), 400
        
        query_text = body['query']
        connection_id = body.get('connection_id')
        
        # Perform semantic search
        results = perform_semantic_search(query_text)
        
        # If connection_id provided, also send via WebSocket
        if connection_id and apigw_management_client:
            send_websocket_message(connection_id, {
                'message': f'Search results for: {query_text}',
                'results': results,
                'query': query_text
            })
        
        return jsonify({
            'query': query_text,
            'results': results,
            'total_results': len(results)
        }), 200
        
    except Exception as e:
        return jsonify(error=f'Search failed: {str(e)}'), 500

def get_bedrock_embedding(text, model_id=MODEL_ID):
    """Get embedding from Bedrock"""
    try:
        bedrock = boto3.client('bedrock-runtime', region_name=AWS_REGION)
        body = json.dumps({"inputText": text})
        response = bedrock.invoke_model(
            body=body,
            modelId=model_id,
            accept='application/json',
            contentType='application/json'
        )
        response_body = json.loads(response.get('body').read())
        embedding = response_body.get('embedding')
        return embedding
    except Exception as e:
        print(f"Error getting Bedrock embedding: {str(e)}")
        raise e

def search_opensearch_by_embedding(embedding, endpoint=OPENSEARCH_ENDPOINT, region=AWS_REGION, index_name=INDEX_NAME, k=10):
    """Search OpenSearch using vector embedding"""
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
            "_source": ["title", "summary", "content", "sentiment_label", "sentiment_score", "category"]
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
        raise e

def perform_semantic_search(query_text):
    """Perform complete semantic search workflow"""
    try:
        # Get embedding for the query
        embedding = get_bedrock_embedding(query_text)
        
        if not embedding:
            return []
        
        # Search OpenSearch
        search_results = search_opensearch_by_embedding(embedding, k=10)
        
        hits = search_results.get('hits', {}).get('hits', [])
        
        if not hits:
            return []
        
        # Format results
        formatted_results = []
        for hit in hits:
            source = hit.get('_source', {})
            result = {
                'title': source.get('title', 'Untitled'),
                'summary': source.get('summary', source.get('content', '')[:200] + '...'),
                'content': source.get('content', ''),
                'score': hit.get('_score', 0),
                'sentiment': {
                    'label': source.get('sentiment_label', 'Unknown'),
                    'score': source.get('sentiment_score', 0)
                },
                'category': source.get('category', 'Unknown')
            }
            formatted_results.append(result)
        
        return formatted_results
        
    except Exception as e:
        print(f"Error in semantic search: {str(e)}")
        print(traceback.format_exc())
        return []

def send_websocket_message(connection_id, message_data):
    """Send message to WebSocket client"""
    if not apigw_management_client:
        print("WebSocket API endpoint not configured, cannot send message.")
        return

    try:
        apigw_management_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message_data).encode('utf-8')
        )
        print(f"Message sent to connection {connection_id}")
    except apigw_management_client.exceptions.GoneException:
        print(f"Connection {connection_id} is gone.")
    except Exception as e:
        print(f"Error sending WebSocket message to {connection_id}: {e}")
        print(traceback.format_exc())

@task
def process_semantic_search(query_text, connection_id):
    """Async task to process semantic search"""
    try:
        # Send processing status
        send_websocket_message(connection_id, {
            "status": "processing",
            "message": f"Processing semantic search for: {query_text}"
        })
        
        # Perform search
        results = perform_semantic_search(query_text)
        
        if not results:
            send_websocket_message(connection_id, {
                "status": "no_results",
                "message": f"No results found for '{query_text}'. Try rephrasing your query.",
                "results": [],
                "query": query_text
            })
            return {"status": "no_results", "message": "No results found"}
        
        # Separate by sentiment
        positive_results = [r for r in results if r['sentiment']['label'] == 'POSITIVE']
        negative_results = [r for r in results if r['sentiment']['label'] == 'NEGATIVE']
        
        # Create response message
        response_parts = [f'Found {len(results)} results for "{query_text}"\n']
        
        if positive_results:
            response_parts.append('**Positive Sentiment Results:**')
            for i, result in enumerate(positive_results[:3], 1):
                response_parts.append(f"{i}. **{result['title']}**")
                response_parts.append(f"   {result['summary']}")
                response_parts.append(f"   Score: {result['score']:.3f} | Sentiment: {result['sentiment']['score']:.3f}\n")
        
        if negative_results:
            response_parts.append('**Negative Sentiment Results:**')
            for i, result in enumerate(negative_results[:3], 1):
                response_parts.append(f"{i}. **{result['title']}**")
                response_parts.append(f"   {result['summary']}")
                response_parts.append(f"   Score: {result['score']:.3f} | Sentiment: {result['sentiment']['score']:.3f}\n")
        
        if not positive_results and not negative_results:
            response_parts.append('**Top Results:**')
            for i, result in enumerate(results[:5], 1):
                response_parts.append(f"{i}. **{result['title']}**")
                response_parts.append(f"   {result['summary']}")
                response_parts.append(f"   Score: {result['score']:.3f}\n")
        
        response_message = '\n'.join(response_parts)
        
        # Send results via WebSocket
        send_websocket_message(connection_id, {
            "status": "search_complete",
            "message": response_message,
            "results": results,
            "query": query_text,
            "total_results": len(results)
        })
        
        return {"status": "success", "message": "Search completed successfully"}
        
    except Exception as e:
        error_msg = f"Error in semantic search: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        
        send_websocket_message(connection_id, {
            "status": "search_error",
            "message": f"Sorry, I encountered an error while searching: {str(e)}",
            "results": [],
            "query": query_text
        })
        
        return {"status": "error", "message": error_msg}

@app.route('/process-search', methods=['POST', 'OPTIONS'])
def process_search_endpoint():
    """Endpoint to trigger async semantic search"""
    if request.method == 'OPTIONS':
        return '', 204

    try:
        body = request.json
        if not body or 'query' not in body or 'connection_id' not in body:
            return jsonify(error='Missing query or connection_id in request body.'), 400
        
        query_text = body['query']
        connection_id = body['connection_id']
        
        # Start async processing
        process_semantic_search(query_text, connection_id)
        
        return jsonify({
            "message": "Semantic search processing started. Results will be sent via WebSocket.",
            "query": query_text,
            "connection_id": connection_id
        }), 202
        
    except Exception as e:
        return jsonify(error=f'Failed to start semantic search: {str(e)}'), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    config_status = {
        'opensearch_configured': bool(OPENSEARCH_ENDPOINT),
        'websocket_configured': bool(WEBSOCKET_API_ENDPOINT),
        'bedrock_model': MODEL_ID,
        'aws_region': AWS_REGION,
        'index_name': INDEX_NAME
    }
    
    return jsonify({
        'status': 'healthy',
        'service': 'semantic-search-backend',
        'configuration': config_status
    }), 200

if __name__ == '__main__':
    app.run(debug=True)
