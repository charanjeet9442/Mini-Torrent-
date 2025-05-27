import socket
import threading
import json
import hashlib
import os
import pyperclip
from collections import defaultdict
import time

class Peer:
    def __init__(self, tracker_host='localhost', tracker_port=5000, peer_port=5001):
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port
        self.peer_port = peer_port
        self.shared_files = {}  # {file_path: file_hash}
        self.downloaded_pieces = defaultdict(dict)  # {file_hash: {piece_index: data}}
        self.lock = threading.Lock()
        self.running = False
        
    def start(self):
        """Main method for CLI version"""
        self.running = True
        threading.Thread(target=self.run_server, daemon=True).start()
        self.cli_interface()
        
    def start_server(self):
        """Method for GUI version to start the server"""
        self.running = True
        self.run_server()
        
    def stop_server(self):
        """Method to stop the server"""
        self.running = False
        
    def cli_interface(self):
        """Command line interface for the peer"""
        while self.running:
            print("\n1. Share file")
            print("2. Download file")
            print("3. Exit")
            choice = input("Enter choice: ")
            
            if choice == '1':
                self.cli_share_file()
            elif choice == '2':
                self.cli_download_file()
            elif choice == '3':
                self.running = False
                break
    
    def cli_share_file(self):
        """CLI method to share file"""
        file_path = input("Enter file path to share: ")
        try:
            file_hash = self.share_file(file_path)
            print(f"File shared with hash: {file_hash}")
            try:
                pyperclip.copy(file_hash)
                print("Hash copied to clipboard!")
            except Exception as e:
                print(f"Could not copy hash to clipboard: {e}")
        except Exception as e:
            print(f"Error sharing file: {e}")
    
    def cli_download_file(self):
        """CLI method to download file"""
        file_hash = input("Enter file hash to download: ").strip()
        try:
            save_path = f"downloaded_{file_hash[:8]}"
            self.download_file(file_hash, save_path)
            print(f"File downloaded to {save_path}")
        except Exception as e:
            print(f"Error downloading file: {e}")
    
    def run_server(self):
        """Run the peer server to handle incoming requests"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)  # Allows for periodic checking of self.running
            s.bind(('0.0.0.0', self.peer_port))
            s.listen()
            print(f"Peer server running on port {self.peer_port}")
            
            while self.running:
                try:
                    conn, addr = s.accept()
                    threading.Thread(target=self.handle_peer, args=(conn, addr)).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"Error in server: {e}")
    
    def handle_peer(self, conn, addr):
        """Handle incoming connection from another peer"""
        with conn:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    return
                    
                message = json.loads(data)
                if message['type'] == 'request_piece':
                    file_hash = message['file_hash']
                    piece_index = message['piece_index']
                    
                    if file_hash in self.shared_files.values():
                        file_path = next(k for k, v in self.shared_files.items() if v == file_hash)
                        piece_data = self.get_piece(file_path, piece_index)
                        conn.sendall(piece_data)
            except Exception as e:
                print(f"Error handling peer connection: {e}")
    
    def share_file(self, file_path):
        """
        Share a file and return its hash
        Args:
            file_path: Path to the file to share
        Returns:
            str: The SHA-256 hash of the file
        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            
        with self.lock:
            self.shared_files[file_path] = file_hash
        
        self.register_with_tracker(file_hash)
        return file_hash
    
    def download_file(self, file_hash, save_path):
        """
        Download a file from peers
        Args:
            file_hash: The hash of the file to download
            save_path: Where to save the downloaded file
        Raises:
            Exception: If no peers available or download fails
        """
        peers = self.get_peers_from_tracker(file_hash)
        if not peers:
            raise Exception("No peers available for this file")
            
        print(f"Found {len(peers)} peers with this file")
        
        # Simple download from first peer
        peer_ip, peer_port = next(iter(peers.items()))
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((peer_ip, peer_port))
            message = {
                'type': 'request_piece',
                'file_hash': file_hash,
                'piece_index': 0  # Requesting first piece
            }
            s.sendall(json.dumps(message).encode())
            
            data = s.recv(1024)
            if not data:
                raise Exception("No data received from peer")
            
            with open(save_path, 'wb') as f:
                f.write(data)
    
    def register_with_tracker(self, file_hash):
        """Register a shared file with the tracker"""
        message = {
            'type': 'register',
            'file_hash': file_hash,
            'port': self.peer_port
        }
        
        self.send_to_tracker(message)
    
    def get_peers_from_tracker(self, file_hash):
        """Get list of peers sharing a file from tracker"""
        message = {
            'type': 'get_peers',
            'file_hash': file_hash
        }
        
        response = self.send_to_tracker(message, expect_response=True)
        return json.loads(response) if response else {}
    
    def send_to_tracker(self, message, expect_response=False):
        """Send a message to the tracker server"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((self.tracker_host, self.tracker_port))
                s.sendall(json.dumps(message).encode())
                
                if expect_response:
                    return s.recv(1024).decode()
        except Exception as e:
            print(f"Error communicating with tracker: {e}")
            return None
    
    def get_piece(self, file_path, piece_index, piece_size=1024):
        """Get a specific piece of a file"""
        with open(file_path, 'rb') as f:
            f.seek(piece_index * piece_size)
            return f.read(piece_size)

if __name__ == "__main__":
    peer_port = int(input("Enter peer port (default 5001): ") or 5001)
    peer = Peer(peer_port=peer_port)
    peer.start()