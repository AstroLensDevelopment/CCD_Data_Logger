"""
Data Handler for CCD Data Logger
Manages data collection, buffering, and saving to .dat files
"""
import os
from datetime import datetime
import threading


class DataHandler:
    def __init__(self):
        self.data_buffer = []
        self.is_capturing = False
        self.sample_count = 0
        self.last_update_time = "--"
        self.lock = threading.Lock()
        
    def start_capture(self):
        """Start capturing data"""
        with self.lock:
            self.is_capturing = True
            self.data_buffer = []
            self.sample_count = 0
            print("Data capture started")
    
    def stop_capture(self):
        """Stop capturing data"""
        with self.lock:
            self.is_capturing = False
            print(f"Data capture stopped. Total samples: {self.sample_count}")
    
    def add_data(self, data):
        """Add data to buffer"""
        if not self.is_capturing:
            return
        
        with self.lock:
            # Data should be in format: "sample_num\tvalue1\tvalue2\t...\n"
            # or raw values separated by tabs
            self.data_buffer.append(data)
            self.sample_count += 1
            self.last_update_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    
    def get_display_text(self, max_lines=20):
        """Get text for display (last N lines)"""
        with self.lock:
            if not self.data_buffer:
                return "Waiting for data...\n"
            
            # Get last N lines
            display_lines = self.data_buffer[-max_lines:]
            
            # Format for display (show abbreviated data)
            formatted_lines = []
            for line in display_lines:
                # If line is very long (e.g., 3648 pixels), abbreviate it
                if '\t' in line:
                    parts = line.strip().split('\t')
                    if len(parts) > 10:
                        # Show first value (sample number) and a few data points
                        abbreviated = f"{parts[0]}\t{parts[1]}\t{parts[2]}\t{parts[3]}\t...\t{parts[-2]}\t{parts[-1]}"
                        formatted_lines.append(abbreviated)
                    else:
                        formatted_lines.append(line.strip())
                else:
                    formatted_lines.append(line.strip())
            
            return "\n".join(formatted_lines) + "\n"
    
    def get_sample_count(self):
        """Get total number of samples captured"""
        with self.lock:
            return self.sample_count
    
    def get_last_update_time(self):
        """Get time of last data update"""
        with self.lock:
            return self.last_update_time
    
    def save_to_file(self, filepath):
        """Save buffered data to .dat file"""
        with self.lock:
            if not self.data_buffer:
                print("No data to save")
                return False
            
            try:
                # Ensure directory exists
                directory = os.path.dirname(filepath)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                
                # Write data to file
                with open(filepath, 'w') as f:
                    # Write header with metadata
                    f.write(f"# CCD Data Logger\n")
                    f.write(f"# Saved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# Total Samples: {self.sample_count}\n")
                    f.write("#\n")
                    
                    # Write data
                    for line in self.data_buffer:
                        # Ensure line ends with newline
                        if not line.endswith('\n'):
                            line += '\n'
                        f.write(line)
                
                print(f"Data saved successfully to {filepath}")
                print(f"Total samples: {self.sample_count}")
                return True
                
            except Exception as e:
                print(f"Error saving data: {e}")
                return False
    
    def clear_buffer(self):
        """Clear the data buffer"""
        with self.lock:
            self.data_buffer = []
            self.sample_count = 0
            print("Data buffer cleared")
    
    def get_buffer_size(self):
        """Get current buffer size in bytes (approximate)"""
        with self.lock:
            total_size = sum(len(line) for line in self.data_buffer)
            return total_size
    
    def get_buffer_stats(self):
        """Get buffer statistics"""
        with self.lock:
            stats = {
                'sample_count': self.sample_count,
                'buffer_size_bytes': sum(len(line) for line in self.data_buffer),
                'is_capturing': self.is_capturing,
                'last_update': self.last_update_time
            }
            return stats
