"""
Bluetooth Manager for ESP32 SPP Bluetooth Communication
Handles Bluetooth Classic SPP (Serial Port Profile) connections on Android
"""
import threading
from kivy.utils import platform


class BluetoothManager:
    def __init__(self):
        self.socket = None
        self.connected = False
        self.reading = False
        self.read_thread = None
        self.devices = {}
        
        if platform == 'android':
            from jnius import autoclass
            self.BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
            self.BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
            self.BluetoothSocket = autoclass('android.bluetooth.BluetoothSocket')
            self.UUID = autoclass('java.util.UUID')
            # Standard SPP UUID
            self.SPP_UUID = self.UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
        
    def scan_devices(self):
        """Scan for paired Bluetooth devices"""
        self.devices = {}
        
        if platform == 'android':
            try:
                adapter = self.BluetoothAdapter.getDefaultAdapter()
                if adapter is None:
                    print("Bluetooth not supported")
                    return self.devices
                
                if not adapter.isEnabled():
                    print("Bluetooth is not enabled")
                    return self.devices
                
                # Get paired devices
                paired_devices = adapter.getBondedDevices().toArray()
                for device in paired_devices:
                    name = device.getName()
                    address = device.getAddress()
                    self.devices[f"{name} ({address})"] = address
                    
            except Exception as e:
                print(f"Error scanning Bluetooth devices: {e}")
        else:
            # Mock devices for desktop testing
            self.devices = {
                "ESP32-DEV (00:11:22:33:44:55)": "00:11:22:33:44:55",
                "ESP32-CAM (AA:BB:CC:DD:EE:FF)": "AA:BB:CC:DD:EE:FF"
            }
        
        return self.devices
    
    def connect(self, device_name):
        """Connect to a Bluetooth device by name"""
        if device_name not in self.devices:
            print(f"Device {device_name} not found")
            return False
        
        address = self.devices[device_name]
        
        if platform == 'android':
            try:
                adapter = self.BluetoothAdapter.getDefaultAdapter()
                device = adapter.getRemoteDevice(address)
                
                # Create RFCOMM socket using SPP UUID
                self.socket = device.createRfcommSocketToServiceRecord(self.SPP_UUID)
                
                # Connect
                self.socket.connect()
                self.connected = True
                print(f"Connected to {device_name}")
                return True
                
            except Exception as e:
                print(f"Bluetooth connection error: {e}")
                self.connected = False
                return False
        else:
            # Mock connection for desktop testing
            print(f"[Desktop Mode] Connected to {device_name}")
            self.connected = True
            return True
    
    def disconnect(self):
        """Disconnect from Bluetooth device"""
        self.stop_reading()
        
        if platform == 'android' and self.socket:
            try:
                self.socket.close()
            except Exception as e:
                print(f"Error closing Bluetooth socket: {e}")
        
        self.socket = None
        self.connected = False
        print("Bluetooth disconnected")
    
    def start_reading(self, callback):
        """Start reading data from Bluetooth connection"""
        if not self.connected:
            print("Not connected to Bluetooth device")
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
        if platform == 'android':
            self._read_loop_android(callback)
        else:
            self._read_loop_mock(callback)
    
    def _read_loop_android(self, callback):
        """Read data from Android Bluetooth socket"""
        try:
            input_stream = self.socket.getInputStream()
            
            while self.reading and self.connected:
                try:
                    # Read available bytes
                    available = input_stream.available()
                    if available > 0:
                        # Read bytes
                        from jnius import autoclass
                        bytes_array = autoclass('byte[]')(available)
                        input_stream.read(bytes_array)
                        
                        # Convert to Python string
                        data = bytes(bytes_array).decode('utf-8', errors='ignore')
                        
                        if data:
                            callback(data)
                    else:
                        # Small delay to prevent busy waiting
                        import time
                        time.sleep(0.01)
                        
                except Exception as e:
                    print(f"Error reading Bluetooth data: {e}")
                    break
                    
        except Exception as e:
            print(f"Bluetooth read loop error: {e}")
            self.connected = False
    
    def _read_loop_mock(self, callback):
        """Mock data reading for desktop testing"""
        import time
        import random
        
        sample_num = 0
        while self.reading:
            # Simulate CCD data (3648 pixels)
            time.sleep(0.1)  # 10 Hz update rate
            sample_num += 1
            
            # Generate mock data line
            data_values = [str(random.randint(0, 4095)) for _ in range(3648)]
            data_line = f"{sample_num}\t" + "\t".join(data_values) + "\n"
            
            callback(data_line)
    
    def write(self, data):
        """Write data to Bluetooth device"""
        if not self.connected:
            print("Not connected to Bluetooth device")
            return False
        
        if platform == 'android':
            try:
                output_stream = self.socket.getOutputStream()
                output_stream.write(data.encode('utf-8'))
                output_stream.flush()
                return True
            except Exception as e:
                print(f"Error writing to Bluetooth: {e}")
                return False
        else:
            print(f"[Desktop Mode] Would write: {data}")
            return True
