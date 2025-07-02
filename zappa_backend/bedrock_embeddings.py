import os
import json
import boto3
import traceback

# Configuration
MODEL_ID = os.environ.get('MODEL_ID', 'amazon.titan-embed-text-v1')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

def get_bedrock_embedding(text, model_id=MODEL_ID, region=AWS_REGION):
    """
    Get embedding from Amazon Bedrock using Titan Text Embeddings
    
    Args:
        text (str): Text to embed
        model_id (str): Bedrock model ID
        region (str): AWS region
        
    Returns:
        list: Embedding vector or None if failed
    """
    try:
        bedrock = boto3.client('bedrock-runtime', region_name=region)
        
        # Prepare the request body for Titan embeddings
        body = json.dumps({"inputText": text})
        
        response = bedrock.invoke_model(
            body=body,
            modelId=model_id,
            accept='application/json',
            contentType='application/json'
        )
        
        response_body = json.loads(response.get('body').read())
        embedding = response_body.get('embedding')
        
        if embedding:
            print(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
        else:
            print("No embedding returned from Bedrock")
            return None
            
    except Exception as e:
        print(f"Error getting Bedrock embedding: {str(e)}")
        print(traceback.format_exc())
        raise e

def get_bedrock_embedding_batch(texts, model_id=MODEL_ID, region=AWS_REGION):
    """
    Get embeddings for multiple texts (batch processing)
    
    Args:
        texts (list): List of texts to embed
        model_id (str): Bedrock model ID
        region (str): AWS region
        
    Returns:
        list: List of embedding vectors
    """
    embeddings = []
    
    for i, text in enumerate(texts):
        try:
            embedding = get_bedrock_embedding(text, model_id, region)
            embeddings.append(embedding)
            print(f"Processed embedding {i+1}/{len(texts)}")
        except Exception as e:
            print(f"Failed to get embedding for text {i+1}: {str(e)}")
            embeddings.append(None)
    
    return embeddings

def test_bedrock_connection(model_id=MODEL_ID, region=AWS_REGION):
    """
    Test connection to Bedrock service
    
    Args:
        model_id (str): Bedrock model ID
        region (str): AWS region
        
    Returns:
        bool: True if connection successful
    """
    try:
        test_text = "This is a test sentence for embedding."
        embedding = get_bedrock_embedding(test_text, model_id, region)
        
        if embedding and len(embedding) > 0:
            print(f"✅ Bedrock connection successful!")
            print(f"   Model: {model_id}")
            print(f"   Region: {region}")
            print(f"   Embedding dimensions: {len(embedding)}")
            return True
        else:
            print("❌ Bedrock connection failed: No embedding returned")
            return False
            
    except Exception as e:
        print(f"❌ Bedrock connection failed: {str(e)}")
        return False

def get_available_bedrock_models(region=AWS_REGION):
    """
    Get list of available Bedrock foundation models
    
    Args:
        region (str): AWS region
        
    Returns:
        list: List of available models
    """
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        
        response = bedrock.list_foundation_models()
        models = response.get('modelSummaries', [])
        
        # Filter for embedding models
        embedding_models = [
            model for model in models 
            if 'embed' in model.get('modelId', '').lower()
        ]
        
        print(f"Found {len(embedding_models)} embedding models:")
        for model in embedding_models:
            print(f"  - {model.get('modelId')}: {model.get('modelName', 'N/A')}")
        
        return embedding_models
        
    except Exception as e:
        print(f"Error getting Bedrock models: {str(e)}")
        return []

if __name__ == "__main__":
    print("🤖 Testing Bedrock Embeddings...")
    
    # Test connection
    if test_bedrock_connection():
        print("\n📋 Available embedding models:")
        get_available_bedrock_models()
        
        print("\n🧪 Testing with sample text:")
        sample_text = "Machine learning is transforming how we process and understand data."
        embedding = get_bedrock_embedding(sample_text)
        
        if embedding:
            print(f"✅ Successfully generated embedding for: '{sample_text}'")
            print(f"   Embedding length: {len(embedding)}")
            print(f"   First 5 values: {embedding[:5]}")
        else:
            print("❌ Failed to generate embedding")
    else:
        print("❌ Cannot proceed - Bedrock connection failed")
        print("\nTroubleshooting:")
        print("1. Check AWS credentials are configured")
        print("2. Verify Bedrock service is available in your region")
        print("3. Ensure you have permissions to invoke Bedrock models")
        print("4. Check if the model ID is correct and available")
