import { useEffect, useRef, useState } from 'react'
import { FiSend, FiUser } from 'react-icons/fi'
import { RiRobot2Line } from 'react-icons/ri'
import './App.css'

// WebSocket endpoint - Loaded from environment variable
const WEBSOCKET_URL = import.meta.env.VITE_WEBSOCKET_URL

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
        // Attempt to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000)
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setWsStatus('disconnected')
      }

      ws.onmessage = (event) => {
        console.log('Received message:', event.data)
        
        try {
          const data = JSON.parse(event.data)
          
          // Handle connection ID
          if (data.connectionId) {
            setConnectionId(data.connectionId)
          }
          
          // Handle search results or responses
          if (data.message || data.response || data.results) {
            setIsTyping(false)
            const content = data.message || data.response || 
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
  const sendMessage = () => {
    if (!inputMessage.trim() || wsStatus !== 'connected') return

    // Add user message to chat
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, userMessage])

    // Send message via WebSocket
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const payload = {
        action: 'sendmessage',
        message: inputMessage.trim(),
        type: 'semantic_search' // Indicate this is a semantic search request
      }
      
      wsRef.current.send(JSON.stringify(payload))
      setIsTyping(true)
    }

    // Clear input
    setInputMessage('')
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
            disabled={wsStatus !== 'connected'}
            rows={1}
            style={{
              height: Math.min(Math.max(44, inputMessage.split('\n').length * 20 + 24), 120)
            }}
          />
          <button
            className="send-button"
            onClick={sendMessage}
            disabled={!inputMessage.trim() || wsStatus !== 'connected'}
          >
            <FiSend size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}

export default App
