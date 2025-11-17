# pyCCD Spectrometer Command Reference

## 1. Firmware Selection

### Configuration
Two firmware types are supported via dropdown in CCDpanelsetup.py:

- **STM32F40x** (default)
  - MCLK: 2,000,000 Hz
  - min_sh: 20
  - max_sh: 4,294,967,295
  
- **STM32F103**
  - MCLK: 800,000 Hz  
  - min_sh: 8
  - max_sh: 65,535

### Implementation
Firmware selection updates the master clock (`config.MCLK`) and SH period limits. No explicit command is sent to device - this affects timing calculations only.

---

## 2. Serial Communication Protocol

### Command Format (12 bytes)
The firmware expects exactly 12 bytes in one transmission:

```
byte[0-1]:   'E', 'R'  (0x45, 0x52) - Start key
byte[2-5]:   SH-period (32-bit int, big-endian)
byte[6-9]:   ICG-period (32-bit int, big-endian)
byte[10]:    Continuous flag (0=one-shot, 1=continuous)
byte[11]:    Number of averages (1-255)
```

### Python Implementation (CCDserial.py)
```python
config.txfull[0] = 69   # 'E'
config.txfull[1] = 82   # 'R'
# SH-period split into bytes
config.txfull[2] = (config.SHperiod >> 24) & 0xFF
config.txfull[3] = (config.SHperiod >> 16) & 0xFF
config.txfull[4] = (config.SHperiod >> 8) & 0xFF
config.txfull[5] = config.SHperiod & 0xFF
# ICG-period split into bytes
config.txfull[6] = (config.ICGperiod >> 24) & 0xFF
config.txfull[7] = (config.ICGperiod >> 16) & 0xFF
config.txfull[8] = (config.ICGperiod >> 8) & 0xFF
config.txfull[9] = config.ICGperiod & 0xFF
# Mode and averages
config.txfull[10] = config.AVGn[0]  # 0 or 1
config.txfull[11] = config.AVGn[1]  # 1-255

ser.write(config.txfull)  # Send all 12 bytes at once
```

---

## 3. Exposure Time Control

### SH (Sample and Hold) Period
- **Units**: Clock ticks
- **Calculation**: `SH_period = exposure_time_seconds × MCLK`
- **Example**: For 100 µs exposure @ 2 MHz MCLK:
  - SH = 100e-6 × 2,000,000 = 200 ticks

### ICG (Integration Clear Gate) Period
- **Units**: Clock ticks
- **Requirement**: MUST be a multiple of SH-period
- **Minimum**: 14,776 ticks (TCD1304 readout time constraint)
- **Calculation**: `ICG_period = n × SH_period` where `n = ceil(14776 / SH_period)`

### Timing Constraints (TCD1304)
1. **SH minimum**: 20 ticks (STM32F40x) or 8 ticks (STM32F103)
2. **ICG minimum**: 14,776 ticks (absolute minimum for CCD readout)
3. **ICG % SH = 0**: ICG must be exact multiple of SH
4. **Violation**: Software displays "CCD pulse timing violation!" if constraints not met

### Auto-Calculation (CCDpanelsetup.py)
```python
def calculate_timings(self, *args):
    # Convert user input to seconds
    tint_sec = tint_num * unit_multiplier
    
    # Calculate SH-period
    sh_period = int(round(tint_sec * config.MCLK))
    sh_period = max(config.min_sh, min(sh_period, config.max_sh))
    
    # Calculate minimum n to satisfy ICG constraint
    min_n = math.ceil(14776 / sh_period)
    n = max(1, min_n)
    
    # Calculate ICG-period
    icg_period = n * sh_period
    
    config.SHperiod = np.uint32(sh_period)
    config.ICGperiod = np.uint32(icg_period)
```

### Exposure Time Examples
| Exposure | MCLK (Hz) | SH (ticks) | ICG (ticks) | n |
|----------|-----------|------------|-------------|---|
| 100 µs   | 2,000,000 | 200        | 14,800      | 74 |
| 1 ms     | 2,000,000 | 2,000      | 16,000      | 8 |
| 10 ms    | 2,000,000 | 20,000     | 20,000      | 1 |
| 100 µs   | 800,000   | 80         | 14,880      | 186 |

---

## 4. Averaging Control

### Parameter
- **byte[11]**: Number of averages
- **Range**: 1-255 (uint8)
- **Default**: 1 (no averaging)
- **GUI**: Slider from 1 to 255

### Implementation
```python
config.AVGn = np.array([continuous_flag, num_averages], dtype=np.uint8)
# continuous_flag: 0 = one-shot, 1 = continuous
# num_averages: 1-255
```

### Data Reception
- Firmware returns 7,388 bytes (3,694 pixels × 2 bytes/pixel)
- For N averages: firmware averages N acquisitions before returning data
- Total acquisition time = `(ICG_period / MCLK) × num_averages`

---

## 5. ESP32 Bridge (Bluetooth/WiFi)

Both ESP32_Bluetooth.txt and ESP32_WiFI.txt show simple passthrough bridges:

### Bluetooth Bridge
- Device name: "AstroLens"
- Passthrough between PC ↔ ESP32 (Bluetooth) ↔ STM32 (UART @ 115200)

### WiFi Bridge  
- SSID: "AstroLens"
- Password: "AstroLens"
- TCP Server on port 5000
- Passthrough between PC ↔ ESP32 (WiFi) ↔ STM32 (UART @ 115200)

**Note**: ESP32 is transparent - same 12-byte command format applies

---

## 6. Key Notes for Implementation

1. **All 12 bytes must be sent in one transmission** - USB firmware requires this
2. **Big-endian byte order** for 32-bit integers
3. **Wait for full response** (7,388 bytes) before closing serial port
4. **ICG/SH constraint** is critical - firmware may hang if violated
5. **Clear buffers** before transmission to avoid data corruption
6. **Baudrate**: 115,200 (standard across all configurations)

---

## 7. Response Format

### Received Data (7,388 bytes)
- 3,694 pixels × 2 bytes per pixel
- 16-bit little-endian values
- Range: 0-4095 (12-bit ADC typical)

### Python Reconstruction
```python
config.rxData8 = ser.read(7388)  # Read all bytes
for i in range(3694):
    config.rxData16[i] = (config.rxData8[2*i + 1] << 8) + config.rxData8[2*i]
```
