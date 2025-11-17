"""
Kivy Mobile App for CCD Data Logger
Supports Bluetooth SPP and USB Serial connections to ESP32/STM32/TCD1304 CCD
"""
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button, ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform, get_color_from_hex
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.graphics import Color, RoundedRectangle
from datetime import datetime
import threading

from bluetooth_manager import BluetoothManager
from usb_manager import USBManager
from data_handler import DataHandler
from stm32_controller import STM32Controller


class RoundedButton(Button):
    """Custom button with rounded corners and custom colors"""
    
    def __init__(self, **kwargs):
        super(RoundedButton, self).__init__(**kwargs)
        
        # Define colors
        self.normal_color = get_color_from_hex('#fecb48')
        self.pressed_color = get_color_from_hex('#ffc531')
        self.disabled_color = get_color_from_hex('#808080')  # Gray for disabled
        
        self.background_normal = ''
        self.background_down = ''
        self.background_disabled_normal = ''
        self.background_color = (0, 0, 0, 0)  # Transparent
        
        # Set text color to black
        self.color = (0, 0, 0, 1)
        
        self.bind(pos=self.update_canvas, size=self.update_canvas, 
                  disabled=self.update_canvas, state=self.update_canvas)
        self.update_canvas()
    
    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.disabled:
                Color(*self.disabled_color)
            elif self.state == 'down':
                Color(*self.pressed_color)
            else:
                Color(*self.normal_color)
            
            RoundedRectangle(pos=self.pos, size=self.size, radius=[15])


class CCDDataLoggerApp(App):
    status_text = StringProperty("Disconnected")
    is_connected = BooleanProperty(False)
    
    def build(self):
        self.title = "CCD Data Logger"
        
        # Initialize managers
        self.bt_manager = BluetoothManager()
        self.usb_manager = USBManager()
        self.data_handler = DataHandler()
        self.stm32_controller = STM32Controller()
        
        # Main layout
        self.root = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Status bar
        self.status_label = Label(
            text=self.status_text,
            size_hint=(1, 0.1),
            color=get_color_from_hex('#ffc200')  # Orange when disconnected
        )
        self.root.add_widget(self.status_label)
        
        # Connection type selector
        connection_layout = BoxLayout(size_hint=(1, 0.1), spacing=10)
        connection_layout.add_widget(Label(text="Connection:", size_hint=(0.3, 1)))
        
        self.connection_spinner = Spinner(
            text='Bluetooth SPP',
            values=('Bluetooth SPP', 'USB Serial'),
            size_hint=(0.7, 1)
        )
        connection_layout.add_widget(self.connection_spinner)
        self.root.add_widget(connection_layout)
        
        # Firmware selector (for STM32)
        firmware_layout = BoxLayout(size_hint=(1, 0.1), spacing=10)
        firmware_layout.add_widget(Label(text="Firmware:", size_hint=(0.3, 1)))
        
        self.firmware_spinner = Spinner(
            text='STM32F40x',
            values=('STM32F40x', 'STM32F103'),
            size_hint=(0.7, 1)
        )
        self.firmware_spinner.bind(text=self.on_firmware_changed)
        firmware_layout.add_widget(self.firmware_spinner)
        self.root.add_widget(firmware_layout)
        
        # Device selector
        device_layout = BoxLayout(size_hint=(1, 0.1), spacing=10)
        device_layout.add_widget(Label(text="Device:", size_hint=(0.3, 1)))
        
        self.device_spinner = Spinner(
            text='Select Device',
            values=('Select Device',),
            size_hint=(0.5, 1)
        )
        device_layout.add_widget(self.device_spinner)
        
        self.scan_button = RoundedButton(text="Scan", size_hint=(0.2, 1))
        self.scan_button.bind(on_press=self.scan_devices)
        device_layout.add_widget(self.scan_button)
        self.root.add_widget(device_layout)
        
        # Connect/Disconnect buttons
        button_layout = BoxLayout(size_hint=(1, 0.1), spacing=10)
        
        self.connect_button = RoundedButton(text="Connect")
        self.connect_button.bind(on_press=self.connect_device)
        button_layout.add_widget(self.connect_button)
        
        self.disconnect_button = RoundedButton(text="Disconnect", disabled=True)
        self.disconnect_button.bind(on_press=self.disconnect_device)
        button_layout.add_widget(self.disconnect_button)
        self.root.add_widget(button_layout)
        
        # STM32 Exposure Time control
        exposure_layout = BoxLayout(size_hint=(1, 0.1), spacing=10)
        exposure_layout.add_widget(Label(text="Exposure (ms):", size_hint=(0.3, 1)))
        
        self.exposure_input = TextInput(
            text='10',
            multiline=False,
            input_filter='float',
            size_hint=(0.5, 1)
        )
        exposure_layout.add_widget(self.exposure_input)
        
        self.apply_exposure_button = RoundedButton(text="Apply", size_hint=(0.2, 1), disabled=True)
        self.apply_exposure_button.bind(on_press=self.apply_exposure)
        exposure_layout.add_widget(self.apply_exposure_button)
        self.root.add_widget(exposure_layout)
        
        # STM32 Averages control
        averages_layout = BoxLayout(size_hint=(1, 0.1), spacing=10)
        averages_layout.add_widget(Label(text="Averages:", size_hint=(0.3, 1)))
        
        self.averages_spinner = Spinner(
            text='1',
            values=tuple(str(i) for i in [1, 2, 5, 10, 20, 50, 100, 255]),
            size_hint=(0.7, 1)
        )
        self.averages_spinner.bind(text=self.on_averages_changed)
        averages_layout.add_widget(self.averages_spinner)
        self.root.add_widget(averages_layout)
        
        # Timing info display
        self.timing_label = Label(
            text="SH: -- | ICG: -- | Frame: --",
            size_hint=(1, 0.08),
            font_size='12sp'
        )
        self.root.add_widget(self.timing_label)
        
        # Data controls
        data_layout = BoxLayout(size_hint=(1, 0.1), spacing=10)
        
        self.start_capture_button = RoundedButton(text="Start Capture", disabled=True)
        self.start_capture_button.bind(on_press=self.start_capture)
        data_layout.add_widget(self.start_capture_button)
        
        self.stop_capture_button = RoundedButton(text="Stop Capture", disabled=True)
        self.stop_capture_button.bind(on_press=self.stop_capture)
        data_layout.add_widget(self.stop_capture_button)
        
        self.save_button = RoundedButton(text="Save Data", disabled=True)
        self.save_button.bind(on_press=self.save_data)
        data_layout.add_widget(self.save_button)
        self.root.add_widget(data_layout)
        
        # Filename input
        filename_layout = BoxLayout(size_hint=(1, 0.1), spacing=10)
        filename_layout.add_widget(Label(text="Filename:", size_hint=(0.3, 1)))
        self.filename_input = TextInput(
            text=f"ccd_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dat",
            multiline=False,
            size_hint=(0.7, 1)
        )
        filename_layout.add_widget(self.filename_input)
        self.root.add_widget(filename_layout)
        
        # Data display
        scroll_view = ScrollView(size_hint=(1, 0.4))
        self.data_display = TextInput(
            text="Waiting for data...\n",
            multiline=True,
            readonly=True,
            size_hint_y=None
        )
        self.data_display.bind(minimum_height=self.data_display.setter('height'))
        scroll_view.add_widget(self.data_display)
        self.root.add_widget(scroll_view)
        
        # Stats display
        self.stats_label = Label(
            text="Samples: 0 | Last update: --",
            size_hint=(1, 0.1)
        )
        self.root.add_widget(self.stats_label)
        
        # Schedule status updates
        Clock.schedule_interval(self.update_status, 0.5)
        
        return self.root
    
    def scan_devices(self, instance):
        """Scan for available devices"""
        self.update_display("Scanning for devices...")
        connection_type = self.connection_spinner.text
        
        if connection_type == 'Bluetooth SPP':
            devices = self.bt_manager.scan_devices()
            if devices:
                self.device_spinner.values = list(devices.keys())
                self.status_label.color = (1, 1, 1, 1)  # White when devices found
                self.update_display(f"Found {len(devices)} Bluetooth devices")
            else:
                self.update_display("No Bluetooth devices found")
                
        elif connection_type == 'USB Serial':
            devices = self.usb_manager.scan_devices()
            if devices:
                self.device_spinner.values = devices
                self.status_label.color = (1, 1, 1, 1)  # White when devices found
                self.update_display(f"Found {len(devices)} USB devices")
            else:
                self.update_display("No USB devices found")
    
    def connect_device(self, instance):
        """Connect to selected device"""
        device = self.device_spinner.text
        connection_type = self.connection_spinner.text
        
        if device == 'Select Device':
            self.update_display("Please select a device first")
            return
        
        self.update_display(f"Connecting to {device}...")
        
        def connect_thread():
            success = False
            if connection_type == 'Bluetooth SPP':
                success = self.bt_manager.connect(device)
            elif connection_type == 'USB Serial':
                success = self.usb_manager.connect(device)
            
            Clock.schedule_once(lambda dt: self.on_connection_result(success), 0)
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def on_connection_result(self, success):
        """Handle connection result"""
        if success:
            self.is_connected = True
            self.status_text = "Connected"
            self.status_label.color = (1, 1, 1, 1)  # White when connected
            self.update_display("Connected successfully!")
            self.connect_button.disabled = True
            self.disconnect_button.disabled = False
            self.start_capture_button.disabled = False
            self.apply_exposure_button.disabled = False
            self.device_spinner.disabled = True
            self.connection_spinner.disabled = True
            self.scan_button.disabled = True
            
            # Send initial STM32 configuration
            self.send_stm32_config()
        else:
            self.update_display("Connection failed!")
    
    def disconnect_device(self, instance):
        """Disconnect from device"""
        connection_type = self.connection_spinner.text
        
        if connection_type == 'Bluetooth SPP':
            self.bt_manager.disconnect()
        elif connection_type == 'USB Serial':
            self.usb_manager.disconnect()
        
        self.is_connected = False
        self.status_text = "Disconnected"
        self.status_label.color = get_color_from_hex('#ffc200')  # Orange when disconnected
        self.update_display("Disconnected")
        
        self.connect_button.disabled = False
        self.disconnect_button.disabled = True
        self.start_capture_button.disabled = True
        self.stop_capture_button.disabled = True
        self.save_button.disabled = True
        self.apply_exposure_button.disabled = True
        self.device_spinner.disabled = False
        self.connection_spinner.disabled = False
        self.scan_button.disabled = False
    
    def start_capture(self, instance):
        """Start capturing data"""
        self.data_handler.start_capture()
        self.update_display("Capturing data...")
        self.start_capture_button.disabled = True
        self.stop_capture_button.disabled = False
        self.save_button.disabled = False
        
        # Start reading data
        connection_type = self.connection_spinner.text
        if connection_type == 'Bluetooth SPP':
            self.bt_manager.start_reading(self.on_data_received)
        elif connection_type == 'USB Serial':
            self.usb_manager.start_reading(self.on_data_received)
    
    def stop_capture(self, instance):
        """Stop capturing data"""
        connection_type = self.connection_spinner.text
        if connection_type == 'Bluetooth SPP':
            self.bt_manager.stop_reading()
        elif connection_type == 'USB Serial':
            self.usb_manager.stop_reading()
        
        self.data_handler.stop_capture()
        self.update_display("Capture stopped")
        self.start_capture_button.disabled = False
        self.stop_capture_button.disabled = True
    
    def on_data_received(self, data):
        """Callback when data is received"""
        self.data_handler.add_data(data)
        
        # Update display (limit to last few lines)
        display_text = self.data_handler.get_display_text(max_lines=20)
        Clock.schedule_once(lambda dt: self.update_data_display(display_text), 0)
    
    def update_data_display(self, text):
        """Update data display on main thread"""
        self.data_display.text = text
        
        # Update stats
        sample_count = self.data_handler.get_sample_count()
        last_update = self.data_handler.get_last_update_time()
        self.stats_label.text = f"Samples: {sample_count} | Last update: {last_update}"
    
    def save_data(self, instance):
        """Save captured data to file"""
        filename = self.filename_input.text
        
        # Determine save path based on platform
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
            # Save to app's external storage directory
            from android.storage import app_storage_path
            save_path = os.path.join(app_storage_path(), filename)
        else:
            # Save to current directory for desktop testing
            save_path = os.path.join(os.getcwd(), filename)
        
        success = self.data_handler.save_to_file(save_path)
        
        if success:
            self.update_display(f"Data saved to: {save_path}")
        else:
            self.update_display("Failed to save data")
    
    def update_display(self, message):
        """Update the data display with a message"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.data_display.text += f"[{timestamp}] {message}\n"
    
    def on_firmware_changed(self, spinner, text):
        """Handle firmware selection change"""
        self.stm32_controller.set_firmware(text)
        self.update_timing_display()
        self.update_display(f"Firmware changed to {text}")
        
        # If connected, send new config
        if self.is_connected:
            self.send_stm32_config()
    
    def on_averages_changed(self, spinner, text):
        """Handle averages selection change"""
        averages = int(text)
        self.stm32_controller.set_averages(averages)
        self.update_timing_display()
        
        # If connected, send new config
        if self.is_connected:
            self.send_stm32_config()
    
    def apply_exposure(self, instance):
        """Apply exposure time setting"""
        try:
            exposure_ms = float(self.exposure_input.text)
            exposure_s = exposure_ms / 1000.0
            
            actual_exp, sh, icg = self.stm32_controller.set_exposure_time(exposure_s)
            self.update_timing_display()
            
            # Update input with actual value
            self.exposure_input.text = f"{actual_exp * 1000:.3f}"
            
            # Send config to device
            if self.is_connected:
                self.send_stm32_config()
            
            self.update_display(f"Exposure set to {actual_exp * 1000:.3f} ms")
            
        except ValueError:
            self.update_display("Invalid exposure time value")
    
    def send_stm32_config(self):
        """Send STM32 configuration command to device"""
        try:
            # Generate command
            command = self.stm32_controller.generate_command()
            
            # Validate timing
            is_valid, error_msg = self.stm32_controller.validate_timing()
            if not is_valid:
                self.update_display(f"Timing error: {error_msg}")
                return
            
            # Send via appropriate connection
            connection_type = self.connection_spinner.text
            success = False
            
            if connection_type == 'Bluetooth SPP':
                success = self.bt_manager.write(command)
            elif connection_type == 'USB Serial':
                success = self.usb_manager.write(command)
            
            if success:
                timing = self.stm32_controller.get_timing_info()
                self.update_display(
                    f"Config sent: Exp={timing['exposure_time_ms']:.2f}ms, "
                    f"Avg={timing['averages']}, Frame={timing['frame_time_ms']:.2f}ms"
                )
            else:
                self.update_display("Failed to send configuration")
                
        except Exception as e:
            self.update_display(f"Error sending config: {e}")
    
    def update_timing_display(self):
        """Update timing information display"""
        timing = self.stm32_controller.get_timing_info()
        self.timing_label.text = (
            f"SH: {timing['sh_period_us']:.1f}µs | "
            f"ICG: {timing['icg_period_ms']:.2f}ms | "
            f"Frame: {timing['frame_time_ms']:.2f}ms | "
            f"Rate: {timing['acquisition_rate_hz']:.2f}Hz"
        )
    
    def update_status(self, dt):
        """Update status label"""
        self.status_label.text = f"Status: {self.status_text}"
        
        # Update color based on connection status
        if self.is_connected:
            self.status_label.color = (0, 1, 0, 1)  # Green
        else:
            self.status_label.color = (1, 0, 0, 1)  # Red
        
        # Update timing display if connected
        if self.is_connected:
            self.update_timing_display()
    
    def on_stop(self):
        """Cleanup when app closes"""
        if self.is_connected:
            connection_type = self.connection_spinner.text
            if connection_type == 'Bluetooth SPP':
                self.bt_manager.disconnect()
            elif connection_type == 'USB Serial':
                self.usb_manager.disconnect()


if __name__ == '__main__':
    CCDDataLoggerApp().run()
