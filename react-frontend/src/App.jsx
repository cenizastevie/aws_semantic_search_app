import { useEffect, useRef, useState } from 'react'
import { FiSend, FiUser } from 'react-icons/fi'
import { RiRobot2Line } from 'react-icons/ri'
import './App.css'

// WebSocket endpoint - Loaded from environment variable
const WEBSOCKET_URL = import.meta.env.VITE_WEBSOCKET_URL
// API endpoint for direct HTTP requests (Zappa backend)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

function App() {
  // WebSocket state
  const [wsStatus, setWsStatus] = useState('connecting')
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'assistant',
      content: 'Hello! I\'m your semantic search assistant. Ask me anything and I\'ll help you find relevant information.',
      timestamp: new Date()
    }
  ])
  const [isTyping, setIsTyping] = useState(false)
  const wsRef = useRef(null)
  const messagesEndRef = useRef(null)

  // Input state
  const [inputMessage, setInputMessage] = useState('')
  const [connectionId, setConnectionId] = useState('')

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  // WebSocket setup
  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket(WEBSOCKET_URL)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        setWsStatus('connected')
        // Request connection ID after connecting
        ws.send(JSON.stringify({ action: 'get_connection_id' }))
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setWsStatus('disconnected')
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setWsStatus('disconnected')
      }

      ws.onmessage = (event) => {
        console.log('Received message:', event.data)
        
        try {
          const data = JSON.parse(event.data)
          
          // Skip "Forbidden" messages
          if (data.message === "Forbidden") {
            return
          }
          
          // Handle connection ID
          if (data.connectionId) {
            setConnectionId(data.connectionId)
          }
          
          // Handle search results or responses
          if (data.message || data.response || data.results || data.processed_message) {
            setIsTyping(false)
            const content = data.message || data.response || data.processed_message ||
                           (data.results ? `Found ${data.results.length} results:\n\n${data.results.map((r, i) => `${i+1}. ${r.title || r.text || r}`).join('\n')}` : 'No results found')
            
            const newMessage = {
              id: Date.now(),
              type: 'assistant',
              content: content,
              timestamp: new Date()
            }
            
            setMessages(prev => [...prev, newMessage])
          }
          
          // Handle typing indicator
          if (data.status === 'processing') {
            setIsTyping(true)
          }
          
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
          // Handle plain text messages
          setIsTyping(false)
          const newMessage = {
            id: Date.now(),
            type: 'assistant',
            content: event.data,
            timestamp: new Date()
          }
          setMessages(prev => [...prev, newMessage])
        }
      }
    }

    connectWebSocket()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  // Send message function
  const sendMessage = async () => {
    if (!inputMessage.trim()) return

    // Add user message to chat
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, userMessage])
    const currentInput = inputMessage.trim()
    setInputMessage('')

    // Always send to HTTP API (Zappa backend)
    try {
      setIsTyping(true)
      const response = await fetch(`${API_BASE_URL}/llm-summarize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: currentInput,
          connection_id: connectionId
        })
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      setIsTyping(false)
      // If LLM synthesis is present, show it as the assistant message
      let responseMessage = ''
      if (data.llm_synthesis) {
        // Remove 'Prompting LLM...' and '===== LLM SYNTHESIS =====' if present
        responseMessage = data.llm_synthesis.replace(/^Prompting LLM\.{3,}\n?/i, '').replace(/={3,} LLM SYNTHESIS ={3,}\n?/i, '').trim()
      } else if (data.results && data.results.length > 0) {
        responseMessage = `Found ${data.total_results} results for "${currentInput}"\n`
        data.results.slice(0, 5).forEach((result, index) => {
          responseMessage += `${index + 1}. **${result.title}**\n`
          responseMessage += `   ${result.summary}\n`
          responseMessage += `   Score: ${result.score.toFixed(3)}`
          if (result.sentiment && result.sentiment.label !== 'Unknown') {
            responseMessage += ` | Sentiment: ${result.sentiment.label} (${result.sentiment.score.toFixed(3)})`
          }
          responseMessage += '\n\n'
        })
      } else {
        responseMessage = `No results found for "${currentInput}". Try rephrasing your query.`
      }
      const assistantMessage = {
        id: Date.now(),
        type: 'assistant',
        content: responseMessage,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      setIsTyping(false)
      console.error('HTTP API error:', error)
      const errorMessage = {
        id: Date.now(),
        type: 'assistant',
        content: `Sorry, I encountered an error: ${error.message}. Please check your connection and try again.`,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    }
  }

  // Handle input key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // Get status display
  const getStatusDisplay = () => {
    switch (wsStatus) {
      case 'connected':
        return '🟢 Connected'
      case 'connecting':
        return '🟡 Connecting...'
      case 'disconnected':
        return '🔴 Disconnected'
      default:
        return '⚠️ Unknown'
    }
  }

  return (
    <div className="chat-container">
      {/* Connection Status */}
      <div className={`connection-status ${wsStatus}`}>
        {getStatusDisplay()}
        {connectionId && (
          <div style={{ fontSize: '10px', opacity: 0.8 }}>
            ID: {connectionId.substring(0, 8)}...
          </div>
        )}
      </div>

      {/* Chat Messages */}
      <div className="chat-messages">
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.type}`}>
            <div className="message-avatar">
              {message.type === 'user' ? <FiUser /> : <RiRobot2Line />}
            </div>
            <div className="message-content">
              {message.content}
            </div>
          </div>
        ))}
        
        {/* Typing indicator */}
        {isTyping && (
          <div className="message assistant">
            <div className="message-avatar">
              <RiRobot2Line />
            </div>
            <div className="typing-indicator">
              <div className="typing-dots">
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input */}
      <div className="chat-input-container">
        <div className="chat-input-wrapper">
          <textarea
            className="chat-input"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me anything about your documents..."
            disabled={false}
            rows={1}
            style={{
              height: Math.min(Math.max(44, inputMessage.split('\n').length * 20 + 24), 120)
            }}
          />
          <button
            className="send-button"
            onClick={sendMessage}
            disabled={!inputMessage.trim()}
          >
            <FiSend size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}

export default App
