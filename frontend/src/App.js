import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Card, CardContent, CardHeader } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Separator } from './components/ui/separator';
import { ScrollArea } from './components/ui/scroll-area';
import { MessageCircle, Zap, Send, Smile, Sparkles, Users } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const EMOJI_OPTIONS = ['👍', '❤️', '😂', '😮', '😢', '🚀', '🎉', '👏'];

const SplashScreen = ({ onComplete }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onComplete();
    }, 2000);
    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <div className="splash-screen">
      <div className="splash-content">
        <div className="logo-container">
          <div className="app-logo">
            <MessageCircle className="chat-bubble" size={48} />
            <Zap className="lightning-bolt" size={24} />
          </div>
        </div>
        <h1 className="app-title">NextTalk Dash</h1>
        <p className="app-subtitle">Fast Chat Dashboard</p>
      </div>
    </div>
  );
};

const EmojiPicker = ({ onEmojiSelect, onClose, position }) => {
  const pickerStyle = position ? {
    position: 'fixed',
    left: `${position.x}px`,
    top: `${position.y - 60}px`,
    zIndex: 9999
  } : {};

  return (
    <div className="emoji-picker" style={pickerStyle}>
      {EMOJI_OPTIONS.map((emoji) => (
        <button
          key={emoji}
          className="emoji-button"
          onClick={(e) => {
            e.stopPropagation();
            onEmojiSelect(emoji);
            onClose();
          }}
        >
          {emoji}
        </button>
      ))}
    </div>
  );
};

const MessageBubble = ({ message, onReaction }) => {
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [pickerPosition, setPickerPosition] = useState(null);
  const isCurrentUser = message.sender_id === 'current_user';
  
  const handleReactionClick = (e) => {
    const rect = e.target.getBoundingClientRect();
    setPickerPosition({
      x: rect.left,
      y: rect.top
    });
    setShowEmojiPicker(!showEmojiPicker);
  };
  
  const handleReaction = (emoji) => {
    onReaction(message.id, emoji);
    setShowEmojiPicker(false);
  };

  return (
    <div className={`message-bubble ${isCurrentUser ? 'message-own' : 'message-other'}`}>
      <Card className="message-card">
        <CardContent className="message-content">
          {!isCurrentUser && (
            <div className="message-sender">{message.sender_name}</div>
          )}
          <div className="message-text">{message.content}</div>
          <div className="message-footer">
            <span className="message-time">
              {new Date(message.timestamp).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
              })}
            </span>
            <div className="message-actions">
              <button
                className="reaction-button"
                onClick={handleReactionClick}
              >
                <Smile size={16} />
              </button>
            </div>
          </div>
          {message.reactions && message.reactions.length > 0 && (
            <div className="message-reactions">
              {message.reactions.map((reaction, index) => (
                <Badge key={index} variant="secondary" className="reaction-badge">
                  {reaction.emoji} {reaction.username}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      {showEmojiPicker && (
        <EmojiPicker
          onEmojiSelect={handleReaction}
          onClose={() => setShowEmojiPicker(false)}
          position={pickerPosition}
        />
      )}
    </div>
  );
};

const ChatSummary = ({ roomId, isOpen, onClose }) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchSummary = async () => {
    if (!roomId) return;
    setLoading(true);
    try {
      const response = await axios.get(`${API}/summary/${roomId}`);
      setSummary(response.data);
    } catch (error) {
      console.error('Error fetching summary:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && roomId) {
      fetchSummary();
    }
  }, [isOpen, roomId]);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="summary-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles size={20} />
            Last 50 Messages Summary
          </DialogTitle>
        </DialogHeader>
        <div className="summary-content">
          {loading ? (
            <div className="summary-loading">
              <div className="loading-spinner"></div>
              <p>Generating AI summary...</p>
            </div>
          ) : summary ? (
            <div className="summary-results">
              <div className="summary-meta">
                <span className="summary-count">{summary.message_count} messages</span>
                <span className="summary-range">{summary.time_range}</span>
              </div>
              <Separator className="my-4" />
              <div className="summary-points">
                {summary.summary_points.map((point, index) => (
                  <div key={index} className="summary-point">
                    <span className="point-bullet">•</span>
                    <span>{point}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p>No summary available</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

function App() {
  const [showSplash, setShowSplash] = useState(true);
  const [rooms, setRooms] = useState([]);
  const [messages, setMessages] = useState([]);
  const [currentRoom, setCurrentRoom] = useState(null);
  const [newMessage, setNewMessage] = useState('');
  const [showSummary, setShowSummary] = useState(false);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchRooms = async () => {
    try {
      const response = await axios.get(`${API}/rooms`);
      setRooms(response.data);
      if (response.data.length > 0 && !currentRoom) {
        setCurrentRoom(response.data[0]);
      }
    } catch (error) {
      console.error('Error fetching rooms:', error);
    }
  };

  const fetchMessages = async (roomId) => {
    if (!roomId) return;
    try {
      const response = await axios.get(`${API}/rooms/${roomId}/messages`);
      setMessages(response.data);
      setTimeout(scrollToBottom, 100);
    } catch (error) {
      console.error('Error fetching messages:', error);
    }
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !currentRoom) return;
    
    try {
      await axios.post(`${API}/messages`, {
        room_id: currentRoom.id,
        content: newMessage
      });
      setNewMessage('');
      fetchMessages(currentRoom.id);
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };

  const handleReaction = async (messageId, emoji) => {
    try {
      await axios.post(`${API}/reactions`, {
        message_id: messageId,
        emoji: emoji
      });
      fetchMessages(currentRoom.id);
    } catch (error) {
      console.error('Error adding reaction:', error);
    }
  };

  const handleRoomChange = async (roomId) => {
    const room = rooms.find(r => r.id === roomId);
    setCurrentRoom(room);
    fetchMessages(roomId);
    
    // Mark room as read
    try {
      await axios.post(`${API}/rooms/${roomId}/mark-read`);
      fetchRooms(); // Refresh unread counts
    } catch (error) {
      console.error('Error marking room as read:', error);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  useEffect(() => {
    if (!showSplash) {
      fetchRooms();
    }
  }, [showSplash]);

  useEffect(() => {
    if (currentRoom) {
      fetchMessages(currentRoom.id);
      // Poll for new messages every 10 seconds
      const interval = setInterval(() => {
        fetchMessages(currentRoom.id);
      }, 10000);
      return () => clearInterval(interval);
    }
  }, [currentRoom]);

  if (showSplash) {
    return <SplashScreen onComplete={() => setShowSplash(false)} />;
  }

  return (
    <div className="app">
      <div className="nexttalk-widget">
        <Card className="widget-card">
          <CardHeader className="widget-header">
            <div className="header-content">
              <div className="header-left">
                <div className="header-logo">
                  <MessageCircle className="chat-bubble" size={24} />
                  <Zap className="lightning-bolt" size={12} />
                </div>
                <span className="header-title">NextTalk Dash</span>
              </div>
              <div className="header-right">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowSummary(true)}
                  className="summary-button"
                >
                  <Sparkles size={16} />
                  Summarize
                </Button>
              </div>
            </div>
          </CardHeader>
          
          <CardContent className="widget-content">
            <div className="room-selector">
              <Select value={currentRoom?.id || ''} onValueChange={handleRoomChange}>
                <SelectTrigger className="room-trigger">
                  <div className="flex items-center gap-2">
                    <Users size={16} />
                    <SelectValue placeholder="Select Room" />
                  </div>
                </SelectTrigger>
                <SelectContent>
                  {rooms.map((room) => (
                    <SelectItem key={room.id} value={room.id}>
                      <div className="room-option">
                        <span className="room-name">{room.name}</span>
                        {room.unread_count > 0 && (
                          <Badge variant="destructive" className="unread-badge">
                            {room.unread_count}
                          </Badge>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Separator className="my-4" />

            <ScrollArea className="messages-area">
              <div className="messages-container">
                {messages.map((message) => (
                  <MessageBubble
                    key={message.id}
                    message={message}
                    onReaction={handleReaction}
                  />
                ))}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            <div className="message-input">
              <div className="input-container">
                <Input
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type your message..."
                  className="message-field"
                />
                <Button
                  onClick={sendMessage}
                  disabled={!newMessage.trim()}
                  className="send-button"
                >
                  <Send size={16} />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <ChatSummary
        roomId={currentRoom?.id}
        isOpen={showSummary}
        onClose={() => setShowSummary(false)}
      />
    </div>
  );
}

export default App;