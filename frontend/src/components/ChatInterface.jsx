import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2 } from 'lucide-react';

const ChatInterface = () => {
    const [messages, setMessages] = useState([
        {
            id: 1,
            type: 'agent',
            content: 'Hello! I am your Business Analytics Agent. How can I assist you with analyzing your business processes today?'
        }
    ]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (!inputValue.trim()) return;

        const userMessage = {
            id: Date.now(),
            type: 'user',
            content: inputValue
        };

        setMessages(prev => [...prev, userMessage]);
        setInputValue('');
        setIsLoading(true);

        try {
            const response = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: userMessage.content }),
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();

            const agentMessage = {
                id: Date.now() + 1,
                type: 'agent',
                content: data.response,
                image: data.image
            };

            setMessages(prev => [...prev, agentMessage]);
        } catch (error) {
            console.error('Error:', error);
            const errorMessage = {
                id: Date.now() + 1,
                type: 'agent',
                content: "I apologize, but I'm having trouble connecting to the analytics engine. Please ensure the backend server is running."
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="container">
            <div className="chat-container">
                <header className="chat-header">
                    <div className="logo-container">
                        <img src="/forte_logo.jpg" alt="Forte Bank Logo" />
                    </div>
                    <div>
                        <h1>Forte Business Analytics</h1>
                        <div className="status-badge">
                            <span className="status-indicator"></span>
                            Online Agent
                        </div>
                    </div>
                </header>

                <div className="messages-area">
                    {messages.map((msg) => (
                        <div key={msg.id} className={`message ${msg.type}`}>
                            <div className="message-content">
                                {msg.type === 'agent' && (
                                    <div className="icon-wrapper">
                                        <Bot size={20} className="text-accent" />
                                    </div>
                                )}
                                <div>
                                    {msg.content}
                                    {msg.image && (
                                        <div className="mt-3 rounded-lg overflow-hidden border border-gray-200">
                                            <img
                                                src={`data:image/png;base64,${msg.image}`}
                                                alt="Generated Chart"
                                                style={{ maxWidth: '100%', display: 'block' }}
                                            />
                                        </div>
                                    )}
                                </div>
                                {msg.type === 'user' && (
                                    <div className="icon-wrapper">
                                        <User size={20} />
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                    {isLoading && (
                        <div className="message agent">
                            <div className="message-content">
                                <div className="icon-wrapper">
                                    <Bot size={20} className="text-accent" />
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
                                    <Loader2 className="animate-spin" size={16} />
                                    Analyzing...
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                <form className="input-area" onSubmit={handleSendMessage}>
                    <input
                        type="text"
                        className="chat-input"
                        placeholder="Describe a business situation or ask for analysis..."
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        disabled={isLoading}
                    />
                    <button type="submit" className="send-button" disabled={isLoading || !inputValue.trim()}>
                        <Send size={20} />
                    </button>
                </form>
            </div>
        </div>
    );
};

export default ChatInterface;
