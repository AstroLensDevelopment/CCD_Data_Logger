"""
Kivy Mobile App for CCD Data Logger
Supports Bluetooth SPP and USB Serial connections to ESP32/STM32/TCD1304 CCD
"""
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button, ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window
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
        # Disabled should be a neutral gray
        self.disabled_color = get_color_from_hex('#9e9e9e')
        
        self.background_normal = ''
        self.background_down = ''
        self.background_disabled_normal = ''
        self.background_color = (0, 0, 0, 0)  # Transparent
        
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
        # Text color: black on yellow/pressed, white on disabled
        if self.disabled:
            self.color = (1, 1, 1, 1)
        else:
            self.color = (0, 0, 0, 1)


class OverlayRoundedButton(RoundedButton):
    """RoundedButton that overlays a Label so text remains visible (black) when disabled.

    Use this for buttons that must show their text at all times even when disabled.
    The underlying Button's `text` is cleared to avoid duplicate rendering; the overlay
    Label is positioned and sized to match the button.
    """

    def __init__(self, **kwargs):
        # extract the text so we can use it for the overlay
        overlay_text = kwargs.pop('text', '')
        super(OverlayRoundedButton, self).__init__(**kwargs)

        # clear the base widget text so default drawing doesn't conflict
        self.text = ''

        # create overlay label which will always show black text
        self.overlay = Label(
            text=overlay_text,
            color=(0, 0, 0, 1),
            halign='center',
            valign='middle'
        )
        # ensure text is centered inside the label
        self.overlay.bind(size=self.overlay.setter('text_size'))

        # add overlay as a child so it renders on top of the button canvas
        self.add_widget(self.overlay)

        # keep overlay positioned and sized with the button
        self.bind(pos=self._update_overlay, size=self._update_overlay)

    def _update_overlay(self, *args):
        self.overlay.pos = self.pos
        self.overlay.size = self.size

    def set_overlay_text(self, text):
        self.overlay.text = text


class RoundedSpinner(Spinner):
    """Spinner with rounded background matching RoundedButton styling"""
    def __init__(self, **kwargs):
        super(RoundedSpinner, self).__init__(**kwargs)
        self.normal_color = get_color_from_hex('#fecb48')
        self.pressed_color = get_color_from_hex('#ffc531')
        self.disabled_color = get_color_from_hex('#9e9e9e')

        # remove any default background images/colors so our canvas shows
        self.background_normal = ''
        self.background_down = ''
        self.background_disabled_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.color = (0, 0, 0, 1)

        self._pressed = False
        self.bind(pos=self.update_canvas, size=self.update_canvas, disabled=self.update_canvas, state=self.update_canvas)
        self.update_canvas()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._pressed = True
            self.update_canvas()
        return super(RoundedSpinner, self).on_touch_down(touch)

    def on_touch_up(self, touch):
        if self._pressed:
            self._pressed = False
            # update after touch up to show released state
            Clock.schedule_once(lambda dt: self.update_canvas(), 0)
        return super(RoundedSpinner, self).on_touch_up(touch)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.disabled:
                Color(*self.disabled_color)
            elif getattr(self, 'state', '') == 'down' or getattr(self, '_pressed', False):
                Color(*self.pressed_color)
            else:
                Color(*self.normal_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[15])


class RoundedSpinnerOption(SpinnerOption):
    """Dropdown option for Spinner styled like RoundedButton"""
    def __init__(self, **kwargs):
        super(RoundedSpinnerOption, self).__init__(**kwargs)
        self.normal_color = get_color_from_hex('#fecb48')
        self.pressed_color = get_color_from_hex('#ffc531')
        self.disabled_color = get_color_from_hex('#9e9e9e')

        # remove default backgrounds and ensure visuals come from canvas
        self.background_normal = ''
        self.background_down = ''
        self.background_disabled_normal = ''
        self.bind(pos=self.update_canvas, size=self.update_canvas, state=self.update_canvas, disabled=self.update_canvas)
        self.update_canvas()

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.disabled:
                Color(*self.disabled_color)
            elif getattr(self, 'state', '') == 'down':
                Color(*self.pressed_color)
            else:
                Color(*self.normal_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[15])

        # Text color: black on yellow/pressed, white on disabled
        if self.disabled:
            self.color = (1, 1, 1, 1)
        else:
            self.color = (0, 0, 0, 1)


class RoundedTextInput(TextInput):
    """TextInput with rounded corners and plain white background"""
    def __init__(self, **kwargs):
        # Remove background images before calling super
        kwargs['background_normal'] = ''
        kwargs['background_active'] = ''
        
        super(RoundedTextInput, self).__init__(**kwargs)
        
        # Set colors for plain white background with true-black text
        self.background_color = (1, 1, 1, 1)  # Solid white fill
        self.foreground_color = (0, 0, 0, 1)  # Black text even when focused
        self.disabled_foreground_color = (0, 0, 0, 1)  # Keep black when readonly/disabled
        self.cursor_color = (0, 0, 0, 1)  # Black cursor
        
        # Add padding so text doesn't touch edges
        self.padding = [15, 21, 10, 10]
        
        # Bind to update canvas when position or size changes
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        self.update_canvas()
    
    def update_canvas(self, *args):
        # Draw the rounded rectangle as background
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 0)  # Solid white background
            RoundedRectangle(pos=self.pos, size=self.size, radius=[15])
            # Draw a subtle border for definition
            Color(1, 1, 1, 1)  # Light gray border
            from kivy.graphics import Line
            Line(rounded_rectangle=(self.pos[0], self.pos[1], self.size[0], self.size[1], 15), width=1)


class CCDDataLoggerApp(App):
    status_text = StringProperty("Disconnected")
    is_connected = BooleanProperty(False)
    
    def build(self):
        self.title = "pySPEC"
        # Set default window size to 19.5:9 aspect ratio on desktop
        # (has no effect on Android fullscreen)
        if platform != 'android':
            ratio = 9.0 / 19.5
            desired_width = 450
            desired_height = int(desired_width / ratio)
            Window.size = (desired_width, desired_height)
        
        # Initialize managers
        self.bt_manager = BluetoothManager()
        self.usb_manager = USBManager()
        self.data_handler = DataHandler()
        self.stm32_controller = STM32Controller()
        # Track whether a device was found during scan
        self.device_found = False
        
        # Main layout
        self.root = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Status bar (initialized here; added to layout later for better placement)
        self.status_label = Label(
            text=self.status_text,
            size_hint=(1, 1),
            color=get_color_from_hex('#ffc200')
        )
        
        # Connection type selector
        connection_layout = BoxLayout(size_hint=(1, 0.05), spacing=10)
        connection_layout.add_widget(Label(text="Connection:", size_hint=(0.3, 1)))
        
        self.connection_spinner = RoundedSpinner(
            text='Bluetooth SPP',
            values=('Bluetooth SPP', 'USB Serial'),
            size_hint=(0.7, 1),
            option_cls=RoundedSpinnerOption
        )
        # Style spinner to match yellow buttons (same as averages spinner)
        self.connection_spinner.background_normal = ''
        self.connection_spinner.background_down = ''
        self.connection_spinner.background_disabled_normal = ''
        self.connection_spinner.color = (0, 0, 0, 1)
        connection_layout.add_widget(self.connection_spinner)
        self.root.add_widget(connection_layout)
        
        # Firmware selector (for STM32)
        firmware_layout = BoxLayout(size_hint=(1, 0.05), spacing=10)
        firmware_layout.add_widget(Label(text="Firmware:", size_hint=(0.3, 1)))
        
        self.firmware_spinner = RoundedSpinner(
            text='STM32F40x',
            values=('STM32F40x', 'STM32F103'),
            size_hint=(0.7, 1),
            option_cls=RoundedSpinnerOption
        )
        self.firmware_spinner.bind(text=self.on_firmware_changed)
        self.firmware_spinner.background_normal = ''
        self.firmware_spinner.background_down = ''
        self.firmware_spinner.background_disabled_normal = ''
        self.firmware_spinner.color = (0, 0, 0, 1)
        firmware_layout.add_widget(self.firmware_spinner)
        self.root.add_widget(firmware_layout)
        
        # Device selector
        device_layout = BoxLayout(size_hint=(1, 0.05), spacing=10)
        device_layout.add_widget(Label(text="Device:", size_hint=(0.3, 1)))
        
        self.device_spinner = RoundedSpinner(
            text='Select Device',
            values=('Select Device',),
            size_hint=(0.5, 1),
            option_cls=RoundedSpinnerOption
        )
        self.device_spinner.background_normal = ''
        self.device_spinner.background_down = ''
        self.device_spinner.background_disabled_normal = ''
        self.device_spinner.color = (0, 0, 0, 1)
        device_layout.add_widget(self.device_spinner)
        
        self.scan_button = RoundedButton(text="Scan", size_hint=(0.2, 1))
        self.scan_button.bind(on_press=self.scan_devices)
        device_layout.add_widget(self.scan_button)
        self.root.add_widget(device_layout)
        
        # Connect/Disconnect buttons
        button_layout = BoxLayout(size_hint=(1, 0.05), spacing=10)
        
        self.connect_button = RoundedButton(text="Connect")
        self.connect_button.bind(on_press=self.connect_device)
        button_layout.add_widget(self.connect_button)
        
        self.disconnect_button = OverlayRoundedButton(text="Disconnect", disabled=True)
        self.disconnect_button.bind(on_press=self.disconnect_device)
        button_layout.add_widget(self.disconnect_button)
        self.root.add_widget(button_layout)

        # Status label positioning between connection buttons and exposure controls
        # Combine status and timing in one centered horizontal layout
        status_layout = BoxLayout(size_hint=(1, 0.02), padding=(5, 0, 5, 0), spacing=10)
        status_layout.add_widget(self.status_label)
        # Timing info display (moved here to be next to status)
        self.timing_label = Label(
            text="SH: -- | ICG: -- | Frame: --",
            size_hint=(1, 1),
            font_size='12sp'
        )
        status_layout.add_widget(self.timing_label)
        self.root.add_widget(status_layout)
        
        # STM32 Exposure Time control
        exposure_layout = BoxLayout(size_hint=(1, 0.05), spacing=10)
        exposure_layout.add_widget(Label(text="Exposure (ms):", size_hint=(0.3, 1)))
        
        self.exposure_input = RoundedTextInput(
            text='10',
            multiline=False,
            input_filter='float',
            size_hint=(0.5, 1)
        )
        exposure_layout.add_widget(self.exposure_input)
        
        self.apply_exposure_button = OverlayRoundedButton(text="Apply", size_hint=(0.2, 1), disabled=True)
        self.apply_exposure_button.bind(on_press=self.apply_exposure)
        exposure_layout.add_widget(self.apply_exposure_button)
        self.root.add_widget(exposure_layout)
        
        # STM32 Averages control
        averages_layout = BoxLayout(size_hint=(1, 0.05), spacing=10)
        averages_layout.add_widget(Label(text="Averages:", size_hint=(0.3, 1)))
        
        self.averages_spinner = RoundedSpinner(
            text='1',
            values=tuple(str(i) for i in [1, 2, 5, 10, 20, 50, 100, 255]),
            size_hint=(0.7, 1),
            option_cls=RoundedSpinnerOption
        )
        self.averages_spinner.bind(text=self.on_averages_changed)
        averages_layout.add_widget(self.averages_spinner)
        self.root.add_widget(averages_layout)
        
        # Data controls
        data_layout = BoxLayout(size_hint=(1, 0.05), spacing=10)
        
        self.start_capture_button = OverlayRoundedButton(text="Start Capture", disabled=True)
        self.start_capture_button.bind(on_press=self.start_capture)
        data_layout.add_widget(self.start_capture_button)
        
        # single-capture mode: no Stop button
        
        self.save_button = OverlayRoundedButton(text="Save Data", disabled=True)
        self.save_button.bind(on_press=self.save_data)
        data_layout.add_widget(self.save_button)
        self.root.add_widget(data_layout)
        
        # Filename input
        filename_layout = BoxLayout(size_hint=(1, 0.05), spacing=10)
        filename_layout.add_widget(Label(text="Filename:", size_hint=(0.3, 1)))
        self.filename_input = RoundedTextInput(
            text=f"ccd_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dat",
            multiline=False,
            size_hint=(0.7, 1)
        )
        filename_layout.add_widget(self.filename_input)
        self.root.add_widget(filename_layout)
        
        # Data display (limited height with ScrollView so it cannot grow above other controls)
        from kivy.uix.scrollview import ScrollView
        scroll_view = ScrollView(size_hint=(1, 0.2))
        self.data_display = RoundedTextInput(
            text="Waiting for data...\n",
            multiline=True,
            readonly=True,
            size_hint_y=None
        )

        # Ensure the text widget height is at least its content height but never exceeds the scroll viewport
        def _cap_height(inst, value):
            # value is the minimum_height of the TextInput (content height)
            # cap to the scroll_view height so it doesn't grow beyond other controls
            inst.height = max(value, scroll_view.height)

        # When content height changes, update height (but cap to scroll viewport height)
        self.data_display.bind(minimum_height=_cap_height)

        # Also ensure the console height updates if the scroll_view size changes (e.g., on window resize)
        def _on_scroll_resize(inst, value):
            # cap current height to new scroll_view height
            if self.data_display.minimum_height < scroll_view.height:
                self.data_display.height = scroll_view.height
            else:
                self.data_display.height = self.data_display.minimum_height

        scroll_view.bind(height=_on_scroll_resize)

        scroll_view.add_widget(self.data_display)
        self.root.add_widget(scroll_view)
        
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
                # select first discovered device by default
                try:
                    self.device_spinner.text = list(devices.keys())[0]
                except Exception:
                    pass
                self.device_found = True
                # set status color to white when devices found
                self.status_label.color = (1, 1, 1, 1)
                self.update_display(f"Found {len(devices)} Bluetooth devices")
            else:
                self.device_found = False
                self.status_label.color = get_color_from_hex('#ffc200')
                self.update_display("No Bluetooth devices found")
                
        elif connection_type == 'USB Serial':
            devices = self.usb_manager.scan_devices()
            if devices:
                self.device_spinner.values = devices
                try:
                    self.device_spinner.text = devices[0]
                except Exception:
                    pass
                self.device_found = True
                self.status_label.color = (1, 1, 1, 1)
                self.update_display(f"Found {len(devices)} USB devices")
            else:
                self.device_found = False
                self.status_label.color = get_color_from_hex('#ffc200')
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
        self.update_display("Disconnected")
        
        self.connect_button.disabled = False
        self.disconnect_button.disabled = True
        self.start_capture_button.disabled = True
        self.save_button.disabled = True
        self.apply_exposure_button.disabled = True
        self.device_spinner.disabled = False
        self.connection_spinner.disabled = False
        self.scan_button.disabled = False
    
    def start_capture(self, instance):
        """Capture a single averaged frame (or single frame if averages=1)."""
        if not self.is_connected:
            self.update_display("Not connected")
            return

        # Prepare for single capture
        self.data_handler.clear_buffer()
        self.data_handler.start_capture()
        self.update_display("Capturing single frame...")
        self.start_capture_button.disabled = True
        self.save_button.disabled = True

        # Send STM32 configuration (includes averages)
        self.send_stm32_config()

        # mark single-capture mode so we stop reading after first frame
        self._single_capture_mode = True

        # Start reading data
        connection_type = self.connection_spinner.text
        if connection_type == 'Bluetooth SPP':
            self.bt_manager.start_reading(self.on_data_received)
        elif connection_type == 'USB Serial':
            self.usb_manager.start_reading(self.on_data_received)
    
    def stop_capture(self, instance):
        # Deprecated: single-capture mode no longer uses a Stop button.
        # Keep method for compatibility but perform a safe stop.
        connection_type = self.connection_spinner.text
        if connection_type == 'Bluetooth SPP':
            try:
                self.bt_manager.stop_reading()
            except Exception:
                pass
        elif connection_type == 'USB Serial':
            try:
                self.usb_manager.stop_reading()
            except Exception:
                pass

        try:
            self.data_handler.stop_capture()
        except Exception:
            pass

        self._single_capture_mode = False
        self.start_capture_button.disabled = False
    
    def on_data_received(self, data):
        """Callback when data is received"""
        # Add incoming data (thread-safe; data_handler uses a lock)
        self.data_handler.add_data(data)

        # Prepare UI update on main thread
        def _finish_and_update(dt=None):
            # If in single-capture mode, stop reading and finish capture
            if getattr(self, '_single_capture_mode', False):
                connection_type = self.connection_spinner.text
                try:
                    if connection_type == 'Bluetooth SPP':
                        self.bt_manager.stop_reading()
                    elif connection_type == 'USB Serial':
                        self.usb_manager.stop_reading()
                except Exception:
                    pass

                try:
                    self.data_handler.stop_capture()
                except Exception:
                    pass

                self._single_capture_mode = False
                # Enable Save and Start buttons on the UI
                self.save_button.disabled = False
                self.start_capture_button.disabled = False
                self.update_display("Capture complete")

            # Update display with the latest buffered data (safe on main thread)
            display_text = self.data_handler.get_display_text(max_lines=20)
            self.update_data_display(display_text)

        # Schedule UI updates on the main Kivy thread
        Clock.schedule_once(_finish_and_update, 0)
    
    def save_data(self, instance):
        """Save captured data to file"""
        filename = self.filename_input.text
        
        # Determine save path based on platform
        if platform == 'android':
            # imports may not be resolvable on desktop; guard them
            try:
                from android.permissions import request_permissions, Permission  # type: ignore[import]
            except Exception:
                request_permissions = None
                Permission = None

            if request_permissions and Permission:
                try:
                    request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
                except Exception:
                    pass

            try:
                from android.storage import app_storage_path  # type: ignore[import]
            except Exception:
                app_storage_path = None

            if app_storage_path:
                try:
                    save_path = os.path.join(app_storage_path(), filename)
                except Exception:
                    save_path = os.path.join(os.getcwd(), filename)
            else:
                save_path = os.path.join(os.getcwd(), filename)
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

        # Color precedence:
        # 1) connected -> green
        # 2) device found (scanned) -> white
        # 3) nothing found / idle -> yellow (#ffc200)
        if self.is_connected:
            self.status_label.color = (0, 1, 0, 1)  # Green when connected
        elif getattr(self, 'device_found', False):
            self.status_label.color = (1, 1, 1, 1)  # White when devices were found
        else:
            self.status_label.color = get_color_from_hex('#ffc200')

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
