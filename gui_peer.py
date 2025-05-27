import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from peer import Peer
import threading
import pyperclip  # For clipboard operations

class TorrentGUI:
    def __init__(self, root):
        self.root = root
        self.peer = None
        self.setup_ui()
        
    def setup_ui(self):
        self.root.title("Mini Torrent Client")
        self.root.geometry("800x600")  # Increased window size
        
        # Connection Frame
        conn_frame = ttk.LabelFrame(self.root, text="Connection Settings")
        conn_frame.pack(pady=10, padx=10, fill="x")
        
        ttk.Label(conn_frame, text="Tracker Host:").grid(row=0, column=0, padx=5, pady=5)
        self.tracker_host = ttk.Entry(conn_frame)
        self.tracker_host.insert(0, "localhost")
        self.tracker_host.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(conn_frame, text="Tracker Port:").grid(row=0, column=2, padx=5, pady=5)
        self.tracker_port = ttk.Entry(conn_frame, width=10)
        self.tracker_port.insert(0, "5000")
        self.tracker_port.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(conn_frame, text="Peer Port:").grid(row=1, column=0, padx=5, pady=5)
        self.peer_port = ttk.Entry(conn_frame, width=10)
        self.peer_port.insert(0, "5001")
        self.peer_port.grid(row=1, column=1, padx=5, pady=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="Start Peer", command=self.start_peer)
        self.connect_btn.grid(row=1, column=3, padx=5, pady=5)
        
        # File Sharing Frame
        share_frame = ttk.LabelFrame(self.root, text="File Sharing")
        share_frame.pack(pady=10, padx=10, fill="x")
        
        self.share_file_btn = ttk.Button(share_frame, text="Select File to Share", command=self.select_file, state=tk.DISABLED)
        self.share_file_btn.pack(pady=5)
        
        self.shared_file_label = ttk.Label(share_frame, text="No file selected")
        self.shared_file_label.pack()
        
        # Hash display with copy button
        hash_frame = ttk.Frame(share_frame)
        hash_frame.pack(fill="x", padx=5, pady=5)
        
        self.file_hash_label = ttk.Label(hash_frame, text="File hash: ")
        self.file_hash_label.pack(side=tk.LEFT)
        
        self.copy_hash_btn = ttk.Button(hash_frame, text="Copy Hash", command=self.copy_hash, state=tk.DISABLED)
        self.copy_hash_btn.pack(side=tk.LEFT, padx=5)
        
        # File Download Frame
        download_frame = ttk.LabelFrame(self.root, text="File Download")
        download_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        ttk.Label(download_frame, text="Enter File Hash:").pack(pady=5)
        self.download_hash = ttk.Entry(download_frame)
        self.download_hash.pack(fill="x", padx=10, pady=5)
        
        self.download_btn = ttk.Button(download_frame, text="Download File", command=self.download_file, state=tk.DISABLED)
        self.download_btn.pack(pady=10)
        
        # Status Bar
        self.status_var = tk.StringVar()
        self.status_var.set("Not connected")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill="x", padx=10, pady=5)
    
    def copy_hash(self):
        hash_text = self.file_hash_label.cget("text").replace("File hash: ", "")
        pyperclip.copy(hash_text)
        self.status_var.set("Hash copied to clipboard!")
    
    def start_peer(self):
        try:
            tracker_host = self.tracker_host.get()
            tracker_port = int(self.tracker_port.get())
            peer_port = int(self.peer_port.get())
            
            self.peer = Peer(tracker_host=tracker_host, tracker_port=tracker_port, peer_port=peer_port)
            
            # Start peer server in background thread
            threading.Thread(target=self.peer.start_server, daemon=True).start()
            
            self.connect_btn.config(state=tk.DISABLED)
            self.share_file_btn.config(state=tk.NORMAL)
            self.download_btn.config(state=tk.NORMAL)
            self.status_var.set(f"Connected as peer on port {peer_port}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start peer: {str(e)}")
    
    def select_file(self):
        filepath = filedialog.askopenfilename()
        if filepath:
            try:
                self.shared_file_label.config(text=filepath)
                file_hash = self.peer.share_file(filepath)
                self.file_hash_label.config(text=f"File hash: {file_hash}")
                self.copy_hash_btn.config(state=tk.NORMAL)
                self.status_var.set(f"File shared successfully! Hash: {file_hash}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to share file: {str(e)}")
    
    def download_file(self):
        file_hash = self.download_hash.get().strip()
        if not file_hash:
            messagebox.showwarning("Warning", "Please enter a file hash")
            return
            
        try:
            save_path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=f"downloaded_{file_hash[:8]}")
            if save_path:
                threading.Thread(target=self._download_thread, args=(file_hash, save_path), daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Download failed: {str(e)}")
    
    def _download_thread(self, file_hash, save_path):
        self.status_var.set(f"Downloading file {file_hash[:8]}...")
        try:
            self.peer.download_file(file_hash, save_path)
            self.status_var.set(f"File downloaded to {save_path}")
            messagebox.showinfo("Success", "File downloaded successfully!")
        except Exception as e:
            self.status_var.set("Download failed")
            messagebox.showerror("Error", f"Download failed: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = TorrentGUI(root)
    root.mainloop()

