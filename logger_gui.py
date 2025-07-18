import tkinter as tk
from tkinter import scrolledtext, messagebox
import logging
import queue
import threading
import time
import subprocess
import os
import sys
from datetime import datetime
import psutil
import atexit
import tempfile
import platform
import pystray
from PIL import Image

class LogGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Yoombot Log Viewer")
        self.root.geometry("800x600")
        
        # Set window icon for Tkinter
        try:
            icon_path = os.path.join(self.get_base_path(), "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(default=icon_path)  # Use 'default' to support PyInstaller
                logging.info(f"Set Tkinter window icon to {icon_path}")
            else:
                logging.warning(f"Icon file not found at {icon_path}, skipping Tkinter icon")
        except Exception as e:
            logging.error(f"Error setting Tkinter window icon: {str(e)}")
        
        # Create lock file to prevent multiple instances
        self.lock_file = os.path.join(tempfile.gettempdir(), "yoombot_log_viewer.lock")
        if not self.acquire_lock():
            error_msg = "Another instance of Yoombot Log Viewer is already running. Exiting."
            logging.error(error_msg)
            messagebox.showerror("Error", error_msg)
            sys.exit(1)
        
        # Create scrolled text widget for logs
        self.log_text = scrolledtext.ScrolledText(
            root, 
            wrap=tk.WORD, 
            width=90, 
            height=30, 
            font=("Courier", 10)
        )
        self.log_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Create button frame
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(pady=5)
        
        # Create Start button
        self.start_button = tk.Button(self.button_frame, text="Start Bot", command=self.start_bot)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Create Stop button
        self.stop_button = tk.Button(self.button_frame, text="Stop Bot", command=self.stop_bot)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Create Minimize to Tray button
        self.minimize_button = tk.Button(self.button_frame, text="Minimize to Tray", command=self.minimize_to_tray)
        self.minimize_button.pack(side=tk.LEFT, padx=5)
        
        # Configure logging
        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        logging.getLogger().addHandler(self.queue_handler)
        logging.getLogger().setLevel(logging.DEBUG)
        
        # Initialize bot process variable
        self.bot_process = None
        
        # Initialize system tray icon
        self.icon = None
        self.setup_system_tray()
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start checking queue for logs
        self.check_queue()
        
        # Start bot process
        self.start_bot()
        
        # Clean up lock file and system tray on exit
        atexit.register(self.release_lock)
        atexit.register(self.stop_system_tray)
    
    def acquire_lock(self):
        """Acquire a lock file to prevent multiple instances."""
        try:
            if os.path.exists(self.lock_file):
                with open(self.lock_file, 'r') as f:
                    pid = int(f.read().strip())
                    if psutil.pid_exists(pid):
                        return False
                # Remove stale lock file
                os.remove(self.lock_file)
            with open(self.lock_file, 'w') as f:
                f.write(str(os.getpid()))
            logging.info(f"Acquired lock file {self.lock_file} with PID {os.getpid()}")
            return True
        except Exception as e:
            logging.error(f"Error acquiring lock file: {str(e)}")
            return False
    
    def release_lock(self):
        """Release the lock file on exit."""
        try:
            if os.path.exists(self.lock_file):
                with open(self.lock_file, 'r') as f:
                    pid = int(f.read().strip())
                    if pid == os.getpid():
                        os.remove(self.lock_file)
                        logging.info(f"Released lock file {self.lock_file}")
        except Exception as e:
            logging.error(f"Error releasing lock file: {str(e)}")
    
    def get_base_path(self):
        """Get the base path for bundled or development environment."""
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Running as PyInstaller executable
            return sys._MEIPASS
        else:
            # Running as a regular Python script
            return os.path.dirname(os.path.abspath(__file__))
    
    def setup_system_tray(self):
        """Set up system tray icon."""
        try:
            icon_path = os.path.join(self.get_base_path(), "icon.ico")
            if not os.path.exists(icon_path):
                logging.warning(f"Icon file not found at {icon_path}, using default icon")
                # Create a blank image if icon is missing
                image = Image.new('RGB', (64, 64), color='blue')
            else:
                image = Image.open(icon_path)
            
            menu = (
                pystray.MenuItem("Restore", self.restore_window),
                pystray.MenuItem("Exit", self.on_closing)
            )
            self.icon = pystray.Icon("Yoombot", image, "Yoombot Log Viewer", menu)
            threading.Thread(target=self.icon.run, daemon=True).start()
            logging.info("System tray icon set up successfully")
        except Exception as e:
            logging.error(f"Error setting up system tray icon: {str(e)}")
    
    def stop_system_tray(self):
        """Stop the system tray icon."""
        if self.icon:
            self.icon.stop()
            logging.info("System tray icon stopped")
    
    def minimize_to_tray(self):
        """Minimize the window to system tray."""
        self.root.withdraw()  # Hide the window
        self.log_queue.put("Window minimized to system tray")
        logging.info("Window minimized to system tray")
    
    def restore_window(self):
        """Restore the window from system tray."""
        self.root.deiconify()  # Show the window
        self.log_queue.put("Window restored from system tray")
        logging.info("Window restored from system tray")
    
    def on_closing(self):
        """Handle window close event."""
        if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
            self.stop_bot()  # Stop the bot process
            self.stop_system_tray()  # Stop system tray icon
            self.root.destroy()  # Close the window
            sys.exit(0)
    
    def start_bot(self):
        """Start the bot in a separate process without opening a console window."""
        if hasattr(self, 'bot_process') and self.bot_process and self.bot_process.poll() is None:
            self.log_queue.put("Bot is already running")
            logging.info("Bot is already running")
            return
        
        base_path = self.get_base_path()
        bot_script = os.path.join(base_path, "main.py")
        
        # Verify that main.py exists
        if not os.path.exists(bot_script):
            error_msg = f"Error: main.py not found at {bot_script}"
            self.log_queue.put(error_msg)
            logging.error(error_msg)
            return
        
        try:
            # Use system Python for executable mode, sys.executable for development
            python_executable = "python" if getattr(sys, 'frozen', False) else sys.executable
            logging.debug(f"Starting subprocess: {[python_executable, bot_script]} with cwd={base_path}")
            
            # Configure subprocess to avoid opening a console window on Windows
            creationflags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            self.bot_process = subprocess.Popen(
                [python_executable, bot_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=base_path,
                creationflags=creationflags
            )
            # Start threads to capture bot output
            threading.Thread(target=self.read_process_output, args=(self.bot_process.stdout,), daemon=True).start()
            threading.Thread(target=self.read_process_output, args=(self.bot_process.stderr,), daemon=True).start()
            self.log_queue.put("Bot process started successfully")
            logging.info("Bot process started successfully")
        except Exception as e:
            error_msg = f"Error starting bot process: {str(e)}"
            self.log_queue.put(error_msg)
            logging.error(error_msg)
    
    def stop_bot(self):
        """Stop the bot process."""
        if hasattr(self, 'bot_process') and self.bot_process and self.bot_process.poll() is None:
            try:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=5)
                self.log_queue.put("Bot process terminated successfully")
                logging.info("Bot process terminated successfully")
            except subprocess.TimeoutExpired:
                self.bot_process.kill()
                self.log_queue.put("Bot process forcefully terminated after timeout")
                logging.warning("Bot process forcefully terminated after timeout")
            except Exception as e:
                error_msg = f"Error stopping bot process: {str(e)}"
                self.log_queue.put(error_msg)
                logging.error(error_msg)
            self.bot_process = None
        else:
            self.log_queue.put("No running bot process to stop")
            logging.info("No running bot process to stop")
    
    def read_process_output(self, pipe):
        """Read output from bot process and put into queue."""
        while True:
            line = pipe.readline()
            if not line:
                break
            self.log_queue.put(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {line.strip()}")
    
    def check_queue(self):
        """Check queue for new log messages and display them."""
        while True:
            try:
                log_message = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, log_message + "\n")
                self.log_text.see(tk.END)
            except queue.Empty:
                break
        self.root.after(100, self.check_queue)

class QueueHandler(logging.Handler):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self.queue.put(msg)
        except Exception:
            self.handleError(record)

def main():
    root = tk.Tk()
    app = LogGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()