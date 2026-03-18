// frontend/src/services/websocket.js
class WebSocketService {
    constructor() {
        this.ws = null;
        this.messageHandlers = [];
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
    }

    connect(conversationId) {
        const token = localStorage.getItem('token');
        const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost/ws';
        
        this.ws = new WebSocket(`${WS_URL}/${conversationId}?token=${token}`);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.notifyHandlers({ type: 'connected' });
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.notifyHandlers(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.attemptReconnect(conversationId);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.notifyHandlers({ type: 'error', error: 'Connection error' });
        };
    }

    attemptReconnect(conversationId) {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            setTimeout(() => {
                this.connect(conversationId);
            }, this.reconnectDelay * this.reconnectAttempts);
        } else {
            this.notifyHandlers({ 
                type: 'error', 
                error: 'Unable to connect to server. Please refresh the page.' 
            });
        }
    }

    sendMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ message }));
        } else {
            console.error('WebSocket is not connected');
        }
    }

    addMessageHandler(handler) {
        this.messageHandlers.push(handler);
    }

    removeMessageHandler(handler) {
        this.messageHandlers = this.messageHandlers.filter(h => h !== handler);
    }

    notifyHandlers(data) {
        this.messageHandlers.forEach(handler => handler(data));
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

export default new WebSocketService();