import threading
import json
from collections import defaultdict

class Tracker:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.peers = defaultdict(dict)  # {file_hash: {peer_ip: peer_port}}
        self.lock = threading.Lock()
        
    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            print(f"Tracker running on {self.host}:{self.port}")
            
            while True:
                conn, addr = s.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr)).start()
    
    def handle_client(self, conn, addr):
        with conn:
            data = conn.recv(1024).decode()
            if not data:
                return
                
            try:
                message = json.loads(data)
                if message['type'] == 'register':
                    self.register_peer(message, addr[0])
                elif message['type'] == 'get_peers':
                    peers = self.get_peers(message['file_hash'])
                    conn.sendall(json.dumps(peers).encode())
            except Exception as e:
                print(f"Error handling client: {e}")
    
    def register_peer(self, message, ip):
        file_hash = message['file_hash']
        port = message['port']
        
        with self.lock:
            self.peers[file_hash][ip] = port
            print(f"Registered peer {ip}:{port} for file {file_hash[:8]}...")
    
    def get_peers(self, file_hash):
        with self.lock:
            print(f"\n[TRACKER DEBUG] Peers for {file_hash}: {self.peers.get(file_hash, {})}")
            return dict(self.peers.get(file_hash, {}))

if __name__ == "__main__":
    tracker = Tracker()
    tracker.start()
