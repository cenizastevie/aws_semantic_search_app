import os
import json
from bedrock_embeddings import get_bedrock_embedding
from opensearch_client import search_opensearch_by_embedding
import boto3
from jinja2 import Environment, FileSystemLoader

# Jinja2 template setup
template_dir = os.path.dirname(__file__)
env = Environment(loader=FileSystemLoader(template_dir))
template = env.get_template('llm_prompt_template.j2')

# Bedrock LLM config
def get_bedrock_llm_response(prompt, model_id=None, region=None):
    """
    Call Bedrock LLM (e.g., Claude, Titan Text, etc.) with the given prompt.
    Handles Titan and Claude schemas automatically.
    """
    model_id = model_id or os.environ.get('LLM_MODEL_ID', 'amazon.titan-text-lite-v1')
    region = region or os.environ.get('AWS_REGION', 'us-east-1')
    bedrock = boto3.client('bedrock-runtime', region_name=region)

    if model_id.startswith('amazon.titan-text'):
        # Titan Text models require 'inputText' and 'textGenerationConfig'
        body = json.dumps({
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": 1024,
                "temperature": 0.2
            }
        })
    else:
        # Claude/Anthropic and others
        body = json.dumps({
            "prompt": prompt,
            "max_tokens_to_sample": 1024,
            "temperature": 0.2
        })

    response = bedrock.invoke_model(
        body=body,
        modelId=model_id,
        accept='application/json',
        contentType='application/json'
    )
    response_body = json.loads(response.get('body').read())
    # Titan returns 'results', Claude returns 'completion' or 'outputText'
    if 'results' in response_body and response_body['results']:
        return response_body['results'][0].get('outputText', '')
    return response_body.get('completion') or response_body.get('outputText')

def format_snippets_for_prompt(snippets):
    """
    Format OpenSearch results as text for the LLM prompt.
    """
    formatted = []
    for i, hit in enumerate(snippets):
        src = hit.get('_source', {})
        title = src.get('title', '')
        summary = src.get('summary', '')
        content = src.get('content', '')
        sentiment = src.get('sentiment_label', '')
        formatted.append(f"Snippet {i+1} (Sentiment: {sentiment}):\nTitle: {title}\nSummary: {summary}\nContent: {content}\n")
    return '\n'.join(formatted)

def llm_summarize(query, k=5):
    """Run LLM summarization workflow for a query and return the output as a string."""
    # Step 1: Embed the query
    embedding = get_bedrock_embedding(query)
    # Step 2: Search OpenSearch
    results = search_opensearch_by_embedding(embedding, k=k)
    hits = results.get('hits', {}).get('hits', [])
    if not hits:
        return 'No relevant results found.'
    # Step 3: Format snippets for prompt
    snippets_text = format_snippets_for_prompt(hits)
    # Step 4: Render prompt with Jinja2 template
    template_dir = os.path.dirname(__file__)
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('llm_prompt_template.j2')
    prompt = template.render(snippets=snippets_text)
    llm_response = get_bedrock_llm_response(prompt)
    return f'{llm_response}'
