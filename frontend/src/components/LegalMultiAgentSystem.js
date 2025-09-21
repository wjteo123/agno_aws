import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, FileText, Search, Shield, Edit, Scale, MessageSquare, History, Upload, File, Plus, X, CheckCircle2, AlertCircle, ChevronDown, ChevronRight, Code, Table, FileCode, Eye, Maximize2 } from 'lucide-react';

const LegalMultiAgentSystem = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [selectedAgent, setSelectedAgent] = useState('team');
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => `session-${Date.now()}`);
  const [showHistory, setShowHistory] = useState(false);
  const [sessionHistory, setSessionHistory] = useState([]);
  
  // File Upload States
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadDocType, setUploadDocType] = useState('pdf');
  const [uploadCategory, setUploadCategory] = useState('general');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadError, setUploadError] = useState('');
  
  // Artifact and thinking states
  const [expandedThinking, setExpandedThinking] = useState({});
  const [expandedArtifacts, setExpandedArtifacts] = useState({});
  
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  
  // Agent configurations with Apple-style colors
  const agents = {
    team: { name: 'Legal Team', icon: Scale, color: 'bg-blue-500', description: 'Complete collaborative legal assistance' },
    researcher: { name: 'Legal Researcher', icon: Search, color: 'bg-indigo-500', description: 'Legal research and case law analysis' },
    contract_analyzer: { name: 'Contract Analyzer', icon: FileText, color: 'bg-green-500', description: 'Contract analysis and risk assessment' },
    compliance_advisor: { name: 'Compliance Advisor', icon: Shield, color: 'bg-orange-500', description: 'Regulatory compliance guidance' },
    document_drafter: { name: 'Document Drafter', icon: Edit, color: 'bg-red-500', description: 'Legal document drafting' },
    legal_advisor: { name: 'Legal Advisor', icon: Bot, color: 'bg-purple-500', description: 'General legal consultation' }
  };

  // Helper function to extract artifacts from content
  const extractArtifacts = (content) => {
    const artifacts = [];
    let remainingContent = content;
    
    // Extract code blocks
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
    let match;
    while ((match = codeBlockRegex.exec(content)) !== null) {
      artifacts.push({
        type: 'code',
        language: match[1] || 'text',
        content: match[2].trim(),
        title: `${match[1] || 'Code'} Block`
      });
      remainingContent = remainingContent.replace(match[0], '');
    }
    
    // Extract tables
    const tableRegex = /(\|.*\|[\s\S]*?\n(?:\|.*\|[\s\S]*?\n)*)/g;
    while ((match = tableRegex.exec(content)) !== null) {
      const tableContent = match[1].trim();
      const rows = tableContent.split('\n').filter(row => row.trim());
      if (rows.length >= 2) {
        artifacts.push({
          type: 'table',
          content: tableContent,
          title: 'Data Table'
        });
        remainingContent = remainingContent.replace(match[0], '[Table shown in artifact]');
      }
    }
    
    // Extract structured documents (contracts, memos, etc.)
    const docRegex = /((?:CONTRACT|AGREEMENT|MEMO|POLICY|PROCEDURE|DOCUMENT)[\s\S]{200,})/i;
    if ((match = docRegex.exec(content)) !== null) {
      artifacts.push({
        type: 'document',
        content: match[1],
        title: 'Legal Document'
      });
      remainingContent = remainingContent.replace(match[0], '[Document shown in artifact]');
    }
    
    // Clean up remaining content
    remainingContent = remainingContent
      .replace(/\n{3,}/g, '\n\n') // Remove excessive line breaks
      .replace(/^\s*\[.*?\]\s*$/gm, '') // Remove artifact placeholders if they're on their own line
      .trim();
    
    // If we removed everything and have artifacts, provide a default message
    if (!remainingContent && artifacts.length > 0) {
      if (artifacts.some(a => a.type === 'table')) {
        remainingContent = "I've created a table with the requested information.";
      } else if (artifacts.some(a => a.type === 'code')) {
        remainingContent = "I've created the code for you.";
      } else if (artifacts.some(a => a.type === 'document')) {
        remainingContent = "I've prepared the document as requested.";
      }
    }
    
    return {
      artifacts,
      conversationalContent: remainingContent
    };
  };

  // Helper function to detect if content has artifacts
  const detectArtifact = (content) => {
    const { artifacts } = extractArtifacts(content);
    return artifacts.length > 0;
  };

  // Helper function to parse markdown tables for display
  const parseMarkdownTable = (content) => {
    const rows = content.trim().split('\n').filter(row => row.trim());
    if (rows.length < 2) return content;
    
    const headerRow = rows[0];
    const separatorRow = rows[1];
    const dataRows = rows.slice(2);
    
    // Check if it's a valid table
    if (!headerRow.includes('|') || !separatorRow.includes('-')) return content;
    
    const headers = headerRow.split('|').map(h => h.trim()).filter(h => h);
    const data = dataRows.map(row => 
      row.split('|').map(cell => cell.trim()).filter(cell => cell)
    );
    
    let tableHtml = '<div class="artifact-table-container"><table class="artifact-table">';
    
    // Header
    tableHtml += '<thead><tr>';
    headers.forEach(header => {
      tableHtml += `<th>${header}</th>`;
    });
    tableHtml += '</tr></thead>';
    
    // Body
    tableHtml += '<tbody>';
    data.forEach(row => {
      tableHtml += '<tr>';
      row.forEach(cell => {
        tableHtml += `<td>${cell}</td>`;
      });
      tableHtml += '</tr>';
    });
    tableHtml += '</tbody></table></div>';
    
    return tableHtml;
  };

  // Helper function to format conversational content
  const formatConversationalContent = (content) => {
    let formatted = content;
    
    // Handle inline code
    formatted = formatted.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
    
    // Handle bold text
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Handle bullet points
    formatted = formatted.replace(/^- (.+)$/gm, '<li>$1</li>');
    formatted = formatted.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    
    return formatted;
  };

  // Helper function to format artifact content
  const formatArtifactContent = (artifact) => {
    if (artifact.type === 'code') {
      return `<div class="code-block">
        <div class="code-header">
          <span class="code-lang">${artifact.language}</span>
        </div>
        <pre><code>${artifact.content}</code></pre>
      </div>`;
    } else if (artifact.type === 'table') {
      return parseMarkdownTable(artifact.content);
    } else if (artifact.type === 'document') {
      return `<div class="document-content">${formatConversationalContent(artifact.content)}</div>`;
    }
    return artifact.content;
  };

  // WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);
      
      ws.onopen = () => {
        setIsConnected(true);
        console.log('Connected to WebSocket');
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.done) {
          setIsLoading(false);
          return;
        }
        
        if (data.error) {
          setMessages(prev => [...prev, {
            id: Date.now(),
            content: `Error: ${data.error}`,
            isBot: true,
            agent: 'System',
            timestamp: new Date().toISOString(),
            isError: true
          }]);
          setIsLoading(false);
          return;
        }
        
        if (data.content) {
          setMessages(prev => {
            const lastMessage = prev[prev.length - 1];
            if (lastMessage && lastMessage.isBot && lastMessage.isStreaming) {
              const updatedContent = lastMessage.content + data.content;
              const { artifacts, conversationalContent } = extractArtifacts(updatedContent);
              return prev.map((msg, index) => 
                index === prev.length - 1 
                  ? { 
                      ...msg, 
                      content: updatedContent,
                      conversationalContent,
                      artifacts,
                      hasArtifact: artifacts.length > 0,
                      thinking: data.thinking || msg.thinking
                    }
                  : msg
              );
            } else {
              const { artifacts, conversationalContent } = extractArtifacts(data.content);
              return [...prev, {
                id: Date.now(),
                content: data.content,
                conversationalContent,
                artifacts,
                isBot: true,
                agent: data.agent || 'Legal Assistant',
                timestamp: data.timestamp || new Date().toISOString(),
                isStreaming: true,
                hasArtifact: artifacts.length > 0,
                thinking: data.thinking
              }];
            }
          });
        }
      };
      
      ws.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket disconnected');
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };
      
      wsRef.current = ws;
    };

    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [sessionId]);

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!inputMessage.trim() || !isConnected || isLoading) return;
    
    const userMessage = {
      id: Date.now(),
      content: inputMessage,
      isBot: false,
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    
    // Send message via WebSocket
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        message: inputMessage,
        agent_type: selectedAgent,
        session_id: sessionId
      }));
    }
    
    setInputMessage('');
  };

  const loadSessionHistory = async () => {
    try {
      const response = await fetch(`http://localhost:8000/sessions/${sessionId}/history`);
      const data = await response.json();
      setSessionHistory(data.messages || []);
      setShowHistory(true);
    } catch (error) {
      console.error('Error loading session history:', error);
    }
  };

  const handleFileUpload = async () => {
    if (!uploadFile) return;
    
    setIsUploading(true);
    setUploadError('');
    
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('document_type', uploadDocType);
      formData.append('category', uploadCategory);
      
      const response = await fetch('http://localhost:8000/knowledge/upload', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error('Upload failed');
      }
      
      const result = await response.json();
      console.log('Upload successful:', result);
      
      setUploadSuccess(true);
      setTimeout(() => {
        setShowUploadModal(false);
        setUploadSuccess(false);
        setUploadFile(null);
        setUploadDocType('pdf');
        setUploadCategory('general');
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }, 2000);
      
    } catch (error) {
      console.error('Error uploading file:', error);
      setUploadError('Failed to upload file. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const createNewSession = () => {
    const newSessionId = `session-${Date.now()}`;
    setSessionId(newSessionId);
    setMessages([]);
    if (wsRef.current) {
      wsRef.current.close();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const toggleThinking = (messageId) => {
    setExpandedThinking(prev => ({
      ...prev,
      [messageId]: !prev[messageId]
    }));
  };

  const toggleArtifact = (artifactKey) => {
    setExpandedArtifacts(prev => ({
      ...prev,
      [artifactKey]: !prev[artifactKey]
    }));
  };

  const AgentIcon = agents[selectedAgent]?.icon || Bot;

  return (
    <>
      <style jsx>{`
        * {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
        }
        .artifact-table-container {
          margin: 16px 0;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          overflow: hidden;
          background: white;
        }
        .artifact-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 14px;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
        }
        .artifact-table th {
          background: #f9fafb;
          padding: 12px;
          text-align: left;
          font-weight: 600;
          border-bottom: 1px solid #e5e7eb;
          color: #374151;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
        }
        .artifact-table td {
          padding: 12px;
          border-bottom: 1px solid #f3f4f6;
          color: #1f2937;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
        }
        .artifact-table tr:last-child td {
          border-bottom: none;
        }
        .artifact-table tr:hover {
          background: #f9fafb;
        }
        .code-block {
          margin: 16px 0;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          overflow: hidden;
          background: #f8fafc;
        }
        .code-header {
          background: #f1f5f9;
          padding: 8px 16px;
          border-bottom: 1px solid #e2e8f0;
          font-size: 12px;
          color: #64748b;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
        }
        .code-block pre {
          margin: 0;
          padding: 16px;
          overflow-x: auto;
          background: #f8fafc;
        }
        .code-block code {
          font-family: 'SF Mono', 'Monaco', 'Menlo', 'Consolas', 'Liberation Mono', 'Courier New', monospace;
          font-size: 13px;
          line-height: 1.5;
          color: #1e293b;
        }
        .inline-code {
          background: #f1f5f9;
          color: #e11d48;
          padding: 2px 6px;
          border-radius: 4px;
          font-family: 'SF Mono', 'Monaco', 'Menlo', 'Consolas', 'Liberation Mono', 'Courier New', monospace;
          font-size: 13px;
        }
        .message-content ul {
          margin: 8px 0;
          padding-left: 20px;
        }
        .message-content li {
          margin: 4px 0;
          color: inherit;
        }
        .document-content {
          line-height: 1.6;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
        }
        .document-content h1, .document-content h2, .document-content h3 {
          margin: 16px 0 8px 0;
          font-weight: 600;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
        }
      `}</style>
      
      <div className="flex h-screen bg-gray-50" style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif' }}>
        {/* Sidebar */}
        <div className="w-80 bg-white border-r border-gray-200 p-6 overflow-y-auto shadow-sm">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900 mb-2 flex items-center">
              <Scale className="mr-3 text-blue-500" />
              Legal AI System
            </h1>
            <p className="text-gray-600 text-sm">Multi-Agent Legal Intelligence</p>
          </div>

          {/* Session Controls */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <span className="text-gray-900 font-medium">Session Controls</span>
              <div className="flex space-x-2">
                <button
                  onClick={loadSessionHistory}
                  className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Load History"
                >
                  <History size={16} />
                </button>
                <button
                  onClick={() => setShowUploadModal(true)}
                  className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Upload Document"
                >
                  <Plus size={16} />
                </button>
              </div>
            </div>
            <button
              onClick={createNewSession}
              className="w-full px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors mb-2 font-medium"
            >
              New Session
            </button>
            <p className="text-xs text-gray-500">Session: {sessionId.split('-')[1]}</p>
          </div>

          {/* Agent Selection */}
          <div className="mb-6">
            <h3 className="text-gray-900 font-medium mb-3">Select Agent</h3>
            <div className="space-y-2">
              {Object.entries(agents).map(([key, agent]) => {
                const Icon = agent.icon;
                return (
                  <button
                    key={key}
                    onClick={() => setSelectedAgent(key)}
                    className={`w-full p-3 rounded-lg transition-all text-left ${
                      selectedAgent === key 
                        ? `${agent.color} text-white shadow-md` 
                        : 'bg-gray-50 text-gray-700 hover:bg-gray-100 border border-gray-200'
                    }`}
                  >
                    <div className="flex items-center">
                      <Icon size={20} className="mr-3" />
                      <div>
                        <div className="font-medium">{agent.name}</div>
                        <div className="text-xs opacity-75">{agent.description}</div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Connection Status */}
          <div className="mb-6">
            <div className={`flex items-center p-3 rounded-lg border ${
              isConnected 
                ? 'bg-green-50 text-green-700 border-green-200' 
                : 'bg-red-50 text-red-700 border-red-200'
            }`}>
              <div className={`w-3 h-3 rounded-full mr-3 ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`} />
              {isConnected ? 'Connected' : 'Disconnected'}
            </div>
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <div className="bg-white border-b border-gray-200 p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <AgentIcon className={`mr-3 p-2 rounded-lg ${agents[selectedAgent]?.color} text-white`} size={40} />
                <div>
                  <h2 className="text-xl font-bold text-gray-900">{agents[selectedAgent]?.name}</h2>
                  <p className="text-gray-600 text-sm">{agents[selectedAgent]?.description}</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                {isLoading && (
                  <div className="flex items-center text-blue-500">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500 mr-2"></div>
                    Processing...
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50">
            {messages.length === 0 && (
              <div className="text-center text-gray-500 py-12">
                <MessageSquare size={48} className="mx-auto mb-4 text-gray-300" />
                <p className="text-lg mb-2 text-gray-700">Welcome to the Legal AI System</p>
                <p className="text-sm">Select an agent and start your legal consultation</p>
              </div>
            )}
            
            {messages.map((message) => (
              <div key={message.id} className="space-y-3">
                <div className={`flex ${message.isBot ? 'justify-start' : 'justify-end'}`}>
                  <div className={`max-w-4xl ${message.isBot ? 'w-full' : ''}`}>
                    {/* Thinking Section */}
                    {message.isBot && message.thinking && (
                      <div className="mb-3">
                        <button
                          onClick={() => toggleThinking(message.id)}
                          className="flex items-center text-sm text-gray-600 hover:text-gray-800 transition-colors"
                        >
                          {expandedThinking[message.id] ? (
                            <ChevronDown size={16} className="mr-1" />
                          ) : (
                            <ChevronRight size={16} className="mr-1" />
                          )}
                          <Bot size={14} className="mr-1" />
                          Claude is thinking...
                        </button>
                        
                        {expandedThinking[message.id] && (
                          <div className="mt-2 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                            <div className="text-sm text-gray-700 italic">
                              {message.thinking}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Main Message */}
                    <div
                      className={`p-4 rounded-2xl ${
                        message.isBot
                          ? message.isError 
                            ? 'bg-red-50 text-red-700 border border-red-200'
                            : 'bg-white text-gray-900 shadow-sm border border-gray-200'
                          : 'bg-blue-500 text-white shadow-sm'
                      }`}
                    >
                      {message.isBot && (
                        <div className="flex items-center mb-3">
                          <Bot size={16} className="mr-2 text-gray-500" />
                          <span className="text-xs font-medium text-gray-600">
                            {message.agent}
                          </span>
                          <div className="text-xs opacity-60 ml-auto">
                            {new Date(message.timestamp).toLocaleTimeString()}
                          </div>
                        </div>
                      )}
                      
                      <div 
                        className="message-content prose max-w-none"
                        dangerouslySetInnerHTML={{ 
                          __html: formatConversationalContent(
                            message.conversationalContent || 
                            (message.hasArtifact ? "I've prepared the content in the artifact below." : message.content)
                          ) 
                        }}
                      />
                      
                      {!message.isBot && (
                        <div className="text-xs opacity-60 mt-2">
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </div>
                      )}
                    </div>

                    {/* Artifact Section */}
                    {message.isBot && message.hasArtifact && message.artifacts && message.artifacts.length > 0 && (
                      <div className="mt-3">
                        {message.artifacts.map((artifact, artifactIndex) => (
                          <div key={artifactIndex} className="mb-3">
                            <button
                              onClick={() => toggleArtifact(`${message.id}-${artifactIndex}`)}
                              className="flex items-center w-full p-3 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors border border-gray-200"
                            >
                              <div className="flex items-center flex-1">
                                {artifact.type === 'code' ? (
                                  <Code size={16} className="mr-2 text-blue-600" />
                                ) : artifact.type === 'table' ? (
                                  <Table size={16} className="mr-2 text-green-600" />
                                ) : (
                                  <FileCode size={16} className="mr-2 text-purple-600" />
                                )}
                                <span className="text-sm font-medium text-gray-700">
                                  {expandedArtifacts[`${message.id}-${artifactIndex}`] ? 'Hide' : 'View'} {artifact.title}
                                </span>
                              </div>
                              <div className="flex items-center space-x-2">
                                <Eye size={14} className="text-gray-500" />
                                {expandedArtifacts[`${message.id}-${artifactIndex}`] ? (
                                  <ChevronDown size={16} className="text-gray-500" />
                                ) : (
                                  <ChevronRight size={16} className="text-gray-500" />
                                )}
                              </div>
                            </button>
                            
                            {expandedArtifacts[`${message.id}-${artifactIndex}`] && (
                              <div className="mt-2 p-4 bg-white border border-gray-200 rounded-lg shadow-sm">
                                <div className="flex items-center justify-between mb-3">
                                  <span className="text-sm font-medium text-gray-700">{artifact.title}</span>
                                  <button className="p-1 text-gray-400 hover:text-gray-600">
                                    <Maximize2 size={14} />
                                  </button>
                                </div>
                                <div 
                                  className="artifact-content"
                                  dangerouslySetInnerHTML={{ 
                                    __html: formatArtifactContent(artifact) 
                                  }}
                                />
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="bg-white border-t border-gray-200 p-4">
            <div className="flex space-x-3">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask your legal question..."
                className="flex-1 p-3 bg-gray-50 text-gray-900 rounded-xl border border-gray-200 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200 resize-none text-sm leading-5"
                rows="1"
                style={{
                  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif',
                  minHeight: '44px',
                  maxHeight: '120px'
                }}
                disabled={!isConnected || isLoading}
                onInput={(e) => {
                  // Auto-resize textarea
                  e.target.style.height = 'auto';
                  e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                }}
              />
              <button
                onClick={sendMessage}
                disabled={!isConnected || isLoading || !inputMessage.trim()}
                className="px-5 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 text-white rounded-xl transition-colors flex items-center justify-center shadow-sm min-w-[52px]"
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>

        {/* Upload Modal */}
        {showUploadModal && (
          <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4 z-50" style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif' }}>
            <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-bold text-gray-900 flex items-center">
                  <Upload className="mr-2 text-blue-500" size={20} />
                  Upload Document
                </h3>
                <button
                  onClick={() => setShowUploadModal(false)}
                  className="text-gray-400 hover:text-gray-600 p-1"
                >
                  <X size={20} />
                </button>
              </div>

              {uploadSuccess ? (
                <div className="text-center py-8">
                  <CheckCircle2 size={48} className="mx-auto mb-4 text-green-500" />
                  <p className="text-lg font-medium text-gray-900 mb-2">Upload Successful!</p>
                  <p className="text-sm text-gray-600">Your document has been processed and added to the knowledge base.</p>
                </div>
              ) : (
                <>
                  <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Select File
                    </label>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.docx,.doc,.txt,.md"
                      onChange={(e) => setUploadFile(e.target.files[0])}
                      className="w-full p-3 border border-gray-200 rounded-lg text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                      style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif' }}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Document Type
                      </label>
                      <select
                        value={uploadDocType}
                        onChange={(e) => setUploadDocType(e.target.value)}
                        className="w-full p-3 border border-gray-200 rounded-lg text-gray-700 focus:border-blue-500 focus:outline-none"
                        style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif' }}
                      >
                        <option value="pdf">PDF</option>
                        <option value="docx">Word Document</option>
                        <option value="text">Text File</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Category
                      </label>
                      <input
                        type="text"
                        value={uploadCategory}
                        onChange={(e) => setUploadCategory(e.target.value)}
                        placeholder="e.g., contracts"
                        className="w-full p-3 border border-gray-200 rounded-lg text-gray-700 focus:border-blue-500 focus:outline-none"
                        style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif' }}
                      />
                    </div>
                  </div>

                  {uploadError && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center">
                      <AlertCircle size={16} className="mr-2 text-red-500" />
                      <span className="text-sm text-red-700">{uploadError}</span>
                    </div>
                  )}

                  <div className="flex space-x-3">
                    <button
                      onClick={() => setShowUploadModal(false)}
                      className="flex-1 px-4 py-3 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors font-medium"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleFileUpload}
                      disabled={!uploadFile || isUploading}
                      className="flex-1 px-4 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 text-white rounded-lg transition-colors font-medium"
                    >
                      {isUploading ? 'Uploading...' : 'Upload'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* History Modal */}
        {showHistory && (
          <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center p-4 z-50" style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif' }}>
            <div className="bg-white rounded-2xl p-6 max-w-2xl w-full max-h-96 overflow-y-auto shadow-2xl">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-gray-900">Session History</h3>
                <button
                  onClick={() => setShowHistory(false)}
                  className="text-gray-400 hover:text-gray-600 p-1"
                >
                  <X size={20} />
                </button>
              </div>
              <div className="space-y-2">
                {sessionHistory.map((msg, index) => (
                  <div key={index} className="p-3 bg-gray-50 rounded-lg text-sm text-gray-700">
                    <strong className="text-gray-900">{msg.role}:</strong> {msg.content}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default LegalMultiAgentSystem;
