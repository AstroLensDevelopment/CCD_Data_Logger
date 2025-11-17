# CCD Data Logger - Kivy Android App

A Kivy-based Android application for logging CCD (Charge-Coupled Device) data from ESP32 or other microcontrollers via Bluetooth SPP or USB Serial connections.

## Features

- **Bluetooth SPP Support**: Connect to ESP32/STM32 devices via Bluetooth Classic (Serial Port Profile)
- **USB Serial Support**: Connect to devices via USB serial (OTG cable required)
- **STM32 TCD1304 Control**: Full firmware support for STM32F40x and STM32F103
  - Firmware selection (2MHz or 800kHz MCLK)
  - Exposure time control with automatic SH/ICG period calculation
  - Configurable averaging (1-255 spectra)
  - Real-time timing parameter display
- **Data Logging**: Capture and buffer incoming data streams
- **File Export**: Save data as `.dat` files with timestamps
- **Real-time Display**: View incoming data in real-time
- **Cross-Platform**: Works on Android devices and can be tested on desktop

## Requirements

### For Building Android APK

- Linux system (Ubuntu/Debian recommended) or WSL on Windows
- Python 3.8+
- Buildozer
- Android SDK/NDK (automatically downloaded by buildozer)

### For Desktop Testing

- Python 3.8+
- Kivy 2.2.1+
- pyserial (optional, for USB testing)

## Installation

### Desktop Testing Setup

1. **Install Python dependencies:**
```bash
pip install kivy==2.2.1
pip install pyserial  # Optional, for USB testing
```

2. **Run the app:**
```bash
python main.py
```

### Android Build Setup

1. **Install Buildozer on Linux/WSL:**
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt update
sudo apt install -y git zip unzip openjdk-11-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

# Install Buildozer
pip3 install buildozer

# Install Cython (required for Kivy)
pip3 install cython==0.29.33
```

2. **Initialize Buildozer (if needed):**
```bash
cd /path/to/CCD_Data_Logger
buildozer init  # Creates buildozer.spec if not present
```

3. **Build APK for Android:**

**Debug APK (for testing):**
```bash
buildozer android debug
```

**Release APK (for distribution):**
```bash
buildozer android release
```

The APK will be created in `bin/` directory.

4. **Deploy to connected Android device:**
```bash
buildozer android debug deploy run
```

## Usage

### STM32 TCD1304 Setup

Your STM32 device should be programmed with TCD1304 CCD firmware:

1. **Supported Firmware:**
   - STM32F40x (2MHz MCLK) - Faster acquisition
   - STM32F103 (800kHz MCLK) - Lower power

2. **Command Protocol:**
   - Receives 12-byte configuration commands
   - Format: `AA 55 [SH:4 bytes] [ICG:4 bytes] [Reserved:1] [Averages:1]`
   - All timing values in big-endian format

3. **Data Output:**
   - Sends 3648 pixel values per spectrum (TCD1304)
   - Tab-separated format: `sample_num\tval1\tval2\t...\tval3648\n`
   - Values are 12-bit ADC readings (0-4095)

4. **Connection Options:**
   - **Bluetooth SPP**: Wireless connection, ~115200 baud
   - **USB Serial**: Wired connection via USB OTG, configurable baud rate

### ESP32 Setup

For non-STM32 ESP32 devices:

1. **For Bluetooth SPP:**
   - Initialize Bluetooth Classic with SPP profile
   - Send data as tab-separated values ending with newline
   - Example format: `sample_num\tvalue1\tvalue2\t...\tvalueN\n`

2. **For USB Serial:**
   - Configure USB CDC (Serial)
   - Send data at specified baud rate (default: 115200)
   - Use same data format as Bluetooth

### Expected Data Format

The app expects data in the following format (compatible with CCD sensors like TCD1304):

```
1	0	150	210	305	...	3890	4095
2	0	145	215	308	...	3885	4090
3	0	148	218	312	...	3892	4088
...
```

- Each line represents one sample/scan
- Values are tab-separated
- First value is typically the sample number
- Remaining values are pixel intensities (0-4095 for 12-bit ADC)
- Line ends with newline character

### App Usage

1. **Launch the app** on your Android device

2. **Select Firmware Type** (for STM32 devices):
   - Choose "STM32F40x" for 2MHz MCLK firmware
   - Choose "STM32F103" for 800kHz MCLK firmware

3. **Select Connection Type:**
   - Choose "Bluetooth SPP" for wireless connection
   - Choose "USB Serial" for wired USB OTG connection

4. **Scan for Devices:**
   - Tap "Scan" button to discover available devices
   - Select your device from the dropdown

5. **Connect:**
   - Tap "Connect" to establish connection
   - Wait for "Connected successfully!" message
   - Initial configuration is sent automatically

6. **Configure STM32 Parameters** (optional):
   - **Exposure Time**: Enter value in milliseconds (e.g., 10 for 10ms)
   - Tap "Apply" to send new exposure setting
   - **Averages**: Select number of spectra to average (1-255)
   - Changes are sent immediately to device
   - **Timing Display**: Shows calculated SH, ICG periods and frame rate

7. **Capture Data:**
   - Tap "Start Capture" to begin logging data
   - Watch real-time data display
   - Tap "Stop Capture" when done

8. **Save Data:**
   - Enter desired filename (or use auto-generated)
   - Tap "Save Data" to export as `.dat` file
   - File is saved to app's storage directory

9. **Disconnect:**
   - Tap "Disconnect" when finished

### Android Permissions

The app requires the following permissions:

- **Bluetooth**: For Bluetooth Classic connections
- **Location**: Required by Android for Bluetooth scanning
- **Storage**: To save `.dat` files
- **USB**: For USB OTG connections

Permissions are requested at runtime when needed.

## File Structure

```
CCD_Data_Logger/
├── main.py                 # Main Kivy application
├── bluetooth_manager.py    # Bluetooth SPP connection manager
├── usb_manager.py         # USB serial connection manager
├── data_handler.py        # Data buffering and file I/O
├── stm32_controller.py    # STM32 TCD1304 timing and command generation
├── buildozer.spec         # Android build configuration
├── requirements.txt       # Python dependencies
├── test_stm32.py          # Test script for STM32 controller
└── README.md             # This file
```

## STM32 TCD1304 Technical Details

### Timing Calculations

The app automatically calculates proper SH (Sample & Hold) and ICG (Integration Clear Gate) periods based on:

- **SH Period** = exposure_time × MCLK (in clock ticks)
- **ICG Period** = n × SH_period where n ≥ ceil(14776/SH)

### Constraints

- **Minimum ICG**: 14,776 clock ticks (TCD1304 readout time)
- **ICG must be multiple of SH**: ICG % SH = 0
- **Minimum SH**: 
  - STM32F40x: 20 ticks (10 µs)
  - STM32F103: 8 ticks (10 µs)

### Command Format

12-byte command structure:
```
Byte 0-1:   Header (0xAA 0x55)
Byte 2-5:   SH period (32-bit big-endian)
Byte 6-9:   ICG period (32-bit big-endian)
Byte 10:    Reserved (0x00)
Byte 11:    Averages (1-255)
```

Example command (10ms exposure, 10 averages, STM32F40x):
```
AA 55 00 00 4E 20 00 00 4E 20 00 0A
```

## Troubleshooting

### Bluetooth Issues

- **Can't find device**: Ensure ESP32 Bluetooth is enabled and discoverable
- **Connection fails**: Make sure device is paired in Android Settings first
- **Permission denied**: Grant Location permission when prompted

### USB Issues

- **No devices found**: 
  - Use USB OTG adapter/cable
  - Enable OTG in Android settings (if available)
  - Grant USB permission when prompted
- **Connection fails**: Try different baud rate (modify in usb_manager.py)

### Build Issues

- **Buildozer fails**: 
  - Ensure you're on Linux or WSL
  - Update buildozer: `pip install -U buildozer`
  - Clean build: `buildozer android clean`
- **Out of memory**: Increase system swap space
- **NDK/SDK errors**: Delete `.buildozer` folder and rebuild

### Data Format Issues

- Ensure ESP32 sends tab-separated values
- Each line must end with `\n`
- Values should be numeric
- Sample format: `sample\tval1\tval2\t...\n`

## Development

### Testing on Desktop

The app includes mock data generators for testing without actual hardware:

```bash
python main.py
```

- Bluetooth: Generates random CCD-like data
- USB: Simulates serial data stream

### Modifying for Different Data Formats

Edit `data_handler.py` to customize:
- Data parsing logic
- File format
- Display formatting

### Customizing UI

- Modify `main.py` to change layout, colors, buttons
- Create `.kv` file for more complex UI designs

## License

This project is provided as-is for educational and research purposes.

## Support

For issues related to:
- **Kivy**: https://kivy.org/doc/stable/
- **Buildozer**: https://buildozer.readthedocs.io/
- **ESP32**: https://docs.espressif.com/

## Version History

- **v1.0.0** (2025-11-17)
  - Initial release
  - Bluetooth SPP support
  - USB Serial support
  - Data logging and export
