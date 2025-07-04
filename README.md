# aws_semantic_search_app
Serverless AWS app for real-time semantic search using OpenSearch, Zappa Flask backend, WebSockets, Bedrock embeddings, and React.

### 1. Deploy Zappa Backend

**Navigate to the backend directory:**
```cmd
cd zappa_backend
```

**Create and activate a Python virtual environment (required for Zappa):**
```cmd
python -m venv venv
venv\Scripts\activate
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
