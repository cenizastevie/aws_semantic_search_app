# aws_semantic_search_app
Serverless AWS app for real-time semantic search using OpenSearch, Zappa Flask backend, WebSockets, Bedrock embeddings, and React.

## Architecture Overview
- **Frontend**: React chat interface with WebSocket + HTTP API fallback
- **Backend**: Zappa Flask application with async task processing
- **Search**: Amazon OpenSearch with k-NN vector search  
- **Embeddings**: Amazon Bedrock Titan Text Embeddings
- **WebSocket**: Optional real-time communication
- **Storage**: S3 for frontend hosting

## Deployment Instructions

### Prerequisites
- AWS CLI configured with appropriate credentials
- Python 3.11+ and pip
- Node.js and npm for React frontend
- Zappa for serverless deployment

### 1. Deploy Zappa Backend

**Navigate to the backend directory:**
```cmd
cd zappa_backend
```

**Install Python dependencies:**
```cmd
pip install -r requirements.txt
```

**Configure environment variables:**
Copy `.env.example` to `.env` and update with your values:
```bash
OPENSEARCH_ENDPOINT=your-opensearch-endpoint.us-east-1.es.amazonaws.com
WEBSOCKET_API_ENDPOINT=https://your-websocket-api-id.execute-api.us-east-1.amazonaws.com/prod
MODEL_ID=amazon.titan-embed-text-v1
AWS_REGION=us-east-1
INDEX_NAME=semantic-search-index
```

**Update Zappa settings:**
Edit `zappa_settings.json` and update:
- `s3_bucket`: Create a unique S3 bucket for Zappa deployments
- `environment_variables`: Set your actual values

**Deploy to AWS:**
```cmd
zappa deploy dev
```

**For updates:**
```cmd
zappa update dev
```

### 2. Setup OpenSearch (if needed)

If you don't have OpenSearch set up, run:
```cmd
python setup_opensearch.py
```

### 3. Configure React Frontend

**Install dependencies:**
```cmd
cd react-frontend
npm install
```

**Update environment configuration:**
Copy `.env.example` to `.env` and update:
```env
VITE_WEBSOCKET_URL=wss://your-websocket-api-id.execute-api.your-region.amazonaws.com/prod
VITE_API_BASE_URL=https://your-zappa-api-id.execute-api.your-region.amazonaws.com/dev
```

**Development:**
```cmd
npm run dev
```

**Build and deploy to S3:**
```cmd
npm run build
aws s3 sync dist/ s3://your-frontend-bucket --delete
```

## API Endpoints

### Zappa Backend Endpoints

- `GET /` - Health check
- `GET /health` - Detailed health status
- `POST /search` - Direct semantic search
- `POST /process-search` - Async search with WebSocket notifications

### Example API Usage

**Direct Search:**
```bash
curl -X POST https://your-zappa-api.execute-api.us-east-1.amazonaws.com/dev/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning benefits"}'
```

**Async Search with WebSocket:**
```bash
curl -X POST https://your-zappa-api.execute-api.us-east-1.amazonaws.com/dev/process-search \
  -H "Content-Type: application/json" \
  -d '{"query": "cloud computing", "connection_id": "abc123"}'
```

## Features
- 🔍 **Semantic Search**: Real-time search using vector embeddings
- 💬 **Chat Interface**: Modern chat UI similar to ChatGPT/DeepSeek
- 🔄 **Dual Connectivity**: WebSocket + HTTP API fallback
- 📱 **Responsive**: Mobile-friendly design
- ⚡ **Async Processing**: Zappa task-based processing
- 🎯 **Sentiment Analysis**: Results categorized by positive/negative sentiment
- 🤖 **AI-Powered**: Uses Amazon Bedrock for text embeddings
- 🚀 **Serverless**: Fully serverless architecture with Zappa

## How It Works

### WebSocket Flow:
1. User connects to WebSocket API
2. Message sent via WebSocket to Lambda
3. Lambda processes search and responds via WebSocket

### HTTP API Flow (Fallback):
1. User types query in React interface
2. HTTP request sent to Zappa Flask backend
3. Backend processes search using Bedrock + OpenSearch
4. Results returned directly via HTTP response

## Environment Variables

### Zappa Backend
- `OPENSEARCH_ENDPOINT`: OpenSearch domain endpoint
- `WEBSOCKET_API_ENDPOINT`: WebSocket API endpoint (optional)
- `MODEL_ID`: Bedrock model ID (default: amazon.titan-embed-text-v1)
- `INDEX_NAME`: OpenSearch index name (default: semantic-search-index)
- `AWS_REGION`: AWS region (default: us-east-1)

### React Frontend
- `VITE_WEBSOCKET_URL`: WebSocket API endpoint (optional)
- `VITE_API_BASE_URL`: Zappa backend API endpoint

## Development Commands

### Backend (Zappa)
```cmd
# Local development
python app.py

# Deploy
zappa deploy dev

# Update
zappa update dev

# View logs
zappa tail dev

# Undeploy
zappa undeploy dev
```

### Frontend (React)
```cmd
# Development
npm run dev

# Build
npm run build

# Preview production build
npm run preview
```

## Troubleshooting

### Zappa Deployment Issues
- Ensure your S3 bucket for deployments exists and is accessible
- Check IAM permissions for Zappa deployment
- Verify Python version compatibility (3.11+)

### OpenSearch Issues
- Ensure k-NN is enabled in your index settings
- Check that documents have embeddings in the `embedding` field
- Verify IAM permissions for accessing OpenSearch

### API Connection Issues
- Check CORS settings in Zappa configuration
- Verify API endpoints in environment variables
- Check CloudWatch logs for detailed error messages
