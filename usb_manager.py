"""
USB Serial Manager for USB Communication
Handles USB serial connections on Android using usb4a library
"""
import threading
from kivy.utils import platform


class USBManager:
    def __init__(self):
        self.device = None
        self.connection = None
        self.connected = False
        self.reading = False
        self.read_thread = None
        self.serial_port = None
        
        if platform == 'android':
            try:
                from usb4a import usb
                from usbserial4a import serial4a
                self.usb = usb
                self.serial4a = serial4a
            except ImportError:
                print("USB libraries not available on Android")
                self.usb = None
                self.serial4a = None
        else:
            # For desktop, try to use pyserial
            try:
                import serial
                import serial.tools.list_ports
                self.serial = serial
                self.list_ports = serial.tools.list_ports
            except ImportError:
                print("pyserial not installed for desktop testing")
                self.serial = None
    
    def scan_devices(self):
        """Scan for USB serial devices"""
        devices = []
        
        if platform == 'android':
            if not self.usb:
                return devices
            
            try:
                usb_device_list = self.usb.get_usb_device_list()
                
                for device_name in usb_device_list:
                    device_info = self.usb.get_usb_device(device_name)
                    if device_info:
                        vendor_id = device_info.getVendorId()
                        product_id = device_info.getProductId()
                        devices.append(f"{device_name} (VID:{vendor_id:04X} PID:{product_id:04X})")
                        
            except Exception as e:
                print(f"Error scanning USB devices: {e}")
        else:
            # Desktop scanning with pyserial
            if self.serial:
                try:
                    ports = self.list_ports.comports()
                    for port in ports:
                        devices.append(f"{port.device} - {port.description}")
                except Exception as e:
                    print(f"Error scanning serial ports: {e}")
            else:
                # Mock devices for testing
                devices = [
                    "/dev/ttyUSB0 - USB Serial Device",
                    "/dev/ttyUSB1 - ESP32 Dev Module"
                ]
        
        return devices
    
    def connect(self, device_name, baudrate=115200):
        """Connect to USB serial device"""
        if platform == 'android':
            return self._connect_android(device_name, baudrate)
        else:
            return self._connect_desktop(device_name, baudrate)
    
    def _connect_android(self, device_name, baudrate):
        """Connect to USB device on Android"""
        if not self.usb or not self.serial4a:
            print("USB libraries not available")
            return False
        
        try:
            # Extract device name (before VID:PID info)
            actual_device_name = device_name.split(' (')[0]
            
            # Get USB device
            device = self.usb.get_usb_device(actual_device_name)
            if not device:
                print(f"Device {actual_device_name} not found")
                return False
            
            # Request permission if needed
            if not self.usb.has_usb_permission(device):
                self.usb.request_usb_permission(device)
                # Note: Permission request is async, may need to retry connection
                return False
            
            # Create serial connection
            self.serial_port = self.serial4a.get_serial_port(
                actual_device_name,
                baudrate,
                8,  # data bits
                'N',  # parity
                1,  # stop bits
                timeout=1
            )
            
            if self.serial_port:
                self.connected = True
                print(f"Connected to {device_name} at {baudrate} baud")
                return True
            else:
                print("Failed to create serial port")
                return False
                
        except Exception as e:
            print(f"USB connection error: {e}")
            return False
    
    def _connect_desktop(self, device_name, baudrate):
        """Connect to serial device on desktop"""
        if not self.serial:
            print("[Desktop Mode] Mock USB connection")
            self.connected = True
            return True
        
        try:
            # Extract device path
            device_path = device_name.split(' - ')[0]
            
            self.serial_port = self.serial.Serial(
                device_path,
                baudrate=baudrate,
                timeout=1
            )
            
            self.connected = True
            print(f"Connected to {device_path} at {baudrate} baud")
            return True
            
        except Exception as e:
            print(f"Serial connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from USB device"""
        self.stop_reading()
        
        if self.serial_port:
            try:
                self.serial_port.close()
            except Exception as e:
                print(f"Error closing serial port: {e}")
        
        self.serial_port = None
        self.connected = False
        print("USB disconnected")
    
    def start_reading(self, callback):
        """Start reading data from USB connection"""
        if not self.connected:
            print("Not connected to USB device")
            return
        
        self.reading = True
        self.read_thread = threading.Thread(
            target=self._read_loop,
            args=(callback,),
            daemon=True
        )
        self.read_thread.start()
    
    def stop_reading(self):
        """Stop reading data"""
        self.reading = False
        if self.read_thread:
            self.read_thread.join(timeout=1.0)
    
    def _read_loop(self, callback):
        """Read data loop (runs in separate thread)"""
        buffer = ""
        
        while self.reading and self.connected:
            try:
                if self.serial_port:
                    # Read available data
                    if platform == 'android':
                        data = self.serial_port.read(size=1024)
                    else:
                        data = self.serial_port.read(self.serial_port.in_waiting or 1)
                    
                    if data:
                        if isinstance(data, bytes):
                            data = data.decode('utf-8', errors='ignore')
                        
                        buffer += data
                        
                        # Process complete lines
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            if line.strip():
                                callback(line + '\n')
                else:
                    # Mock data for testing
                    import time
                    import random
                    time.sleep(0.1)
                    
                    # Generate mock CCD data
                    sample_num = int(time.time() * 10) % 10000
                    data_values = [str(random.randint(0, 4095)) for _ in range(3648)]
                    data_line = f"{sample_num}\t" + "\t".join(data_values) + "\n"
                    callback(data_line)
                    
            except Exception as e:
                print(f"Error reading USB data: {e}")
                import time
                time.sleep(0.1)
    
    def write(self, data):
        """Write data to USB device"""
        if not self.connected or not self.serial_port:
            print("Not connected to USB device")
            return False
        
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            self.serial_port.write(data)
            return True
            
        except Exception as e:
            print(f"Error writing to USB: {e}")
            return False
