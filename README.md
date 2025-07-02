# aws_semantic_search_app
Serverless AWS app for real-time semantic search using OpenSearch, WebSockets, and React.

## Deployment Instructions

### Prerequisites
- AWS CLI configured with appropriate credentials
- SAM CLI installed
- Python 3.13 runtime available

### Deploy with SAM

1. **Build your application using your specific template:**
   ```cmd
   sam build --template web_socket_formation.yaml
   ```

2. **Deploy your application (guided):**
   ```cmd
   sam deploy --guided --template web_socket_formation.yaml --capabilities CAPABILITY_NAMED_IAM
   ```
   - Follow the prompts to set stack name, region, and save configuration for future deploys.

3. **(Optional) Test locally:**
   ```cmd
   sam local invoke SemanticSearchConnectFunction --event events/connect.json --template web_socket_formation.yaml
   ```
   - You can create test event files in an `events/` folder.

### After Deployment
- The WebSocket API endpoint will be available in the CloudFormation outputs
- The React website S3 bucket will be created and ready for your frontend deployment
- Lambda functions will be deployed and ready to handle WebSocket connections

## React Frontend Setup

### 1. Install Dependencies
```cmd
cd react-frontend
npm install
```

### 2. Update WebSocket Configuration
Edit `src/App.jsx` and update the `WEBSOCKET_URL` constant with your deployed WebSocket API endpoint:
```javascript
const WEBSOCKET_URL = 'wss://your-api-id.execute-api.your-region.amazonaws.com/prod/'
```

### 3. Development
```cmd
npm run dev
```

### 4. Build and Deploy to S3
```cmd
npm run build
aws s3 sync dist/ s3://your-bucket-name --delete
```

## Features
- 🔍 **Semantic Search**: Real-time search using WebSocket connections
- 💬 **Chat Interface**: Modern chat UI similar to ChatGPT/DeepSeek
- 🔄 **Auto-reconnect**: Automatic WebSocket reconnection on disconnect
- 📱 **Responsive**: Mobile-friendly design
- ⚡ **Real-time**: Instant message delivery and typing indicators
