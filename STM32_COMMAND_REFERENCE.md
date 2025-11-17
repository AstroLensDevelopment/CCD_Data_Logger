# STM32 TCD1304 Command Reference

## Quick Start Guide

### 1. Select Firmware
Choose the correct firmware type for your STM32 device:
- **STM32F40x**: 2 MHz MCLK, faster acquisition
- **STM32F103**: 800 kHz MCLK, lower power

### 2. Set Exposure Time
Enter exposure time in milliseconds:
- Minimum: ~0.01 ms (10 µs)
- Maximum: ~2147 seconds (STM32F40x)
- Example: Enter "10" for 10ms exposure

### 3. Set Averages
Select number of spectra to average:
- Range: 1 to 255
- Higher values = better SNR but slower frame rate
- Example: 10 averages at 10ms = 100ms total frame time

### 4. Apply Settings
- Tap "Apply" button after changing exposure
- Averages are applied automatically when changed
- Device receives 12-byte configuration command

## Timing Relationships

### Exposure Time → SH Period
```
SH_ticks = exposure_time (seconds) × MCLK (Hz)
```

Examples for STM32F40x (2 MHz):
- 1 ms = 2,000 ticks
- 10 ms = 20,000 ticks
- 100 ms = 200,000 ticks

### SH Period → ICG Period
```
ICG_ticks = n × SH_ticks
where n ≥ ceil(14776 / SH_ticks)
```

The ICG period must:
1. Be at least 14,776 ticks (TCD1304 readout time)
2. Be an exact multiple of SH period

### Frame Time Calculation
```
Frame_time = (ICG_period / MCLK) × Averages
```

Example with 10ms exposure and 10 averages:
- SH = 20,000 ticks
- ICG = 20,000 ticks (n=1, since 20000 > 14776)
- Frame time = (20,000 / 2,000,000) × 10 = 100 ms
- Acquisition rate = 10 Hz

## Command Structure

### 12-Byte Command Format

```
[0xAA] [0x55] [SH_3] [SH_2] [SH_1] [SH_0] [ICG_3] [ICG_2] [ICG_1] [ICG_0] [0x00] [AVG]
```

| Bytes | Field | Type | Description |
|-------|-------|------|-------------|
| 0-1   | Header | Fixed | Always 0xAA 0x55 |
| 2-5   | SH Period | uint32_be | Sample & Hold period in ticks |
| 6-9   | ICG Period | uint32_be | Integration Clear Gate period |
| 10    | Reserved | uint8 | Always 0x00 |
| 11    | Averages | uint8 | Number of spectra to average (1-255) |

### Example Commands

**10ms exposure, 1 average, STM32F40x:**
```
AA 55 00 00 4E 20 00 00 4E 20 00 01
       └─ SH=20000 ─┘ └─ ICG=20000─┘    └AVG=1
```

**10ms exposure, 10 averages, STM32F40x:**
```
AA 55 00 00 4E 20 00 00 4E 20 00 0A
       └─ SH=20000 ─┘ └─ ICG=20000─┘    └AVG=10
```

**1ms exposure, 50 averages, STM32F40x:**
```
AA 55 00 00 07 D0 00 00 3E 80 00 32
       └─ SH=2000 ──┘ └─ ICG=16000 ─┘   └AVG=50
```

**100ms exposure, 1 average, STM32F40x:**
```
AA 55 00 03 0D 40 00 03 0D 40 00 01
       └─ SH=200000 ┘ └─ ICG=200000┘    └AVG=1
```

## Timing Display

The app shows real-time timing information:

```
SH: 10000.0µs | ICG: 10.00ms | Frame: 100.00ms | Rate: 10.00Hz
```

- **SH**: Sample & Hold period (exposure time)
- **ICG**: Integration Clear Gate period (readout cycle)
- **Frame**: Total time per averaged spectrum
- **Rate**: Acquisition rate (spectra per second)

## Troubleshooting

### "Timing error" messages

The app validates timing before sending commands:

1. **SH too small**: Increase exposure time
2. **ICG not multiple of SH**: Automatically corrected by app
3. **Averages out of range**: Use 1-255

### Expected Data Format

STM32 should send data as:
```
sample_num\tval1\tval2\tval3\t...\tval3648\n
```

- 3648 values (TCD1304 pixels)
- Tab-separated
- Values 0-4095 (12-bit ADC)
- Newline terminated

## Performance Tips

### For Fast Acquisition
- Use STM32F40x firmware (2 MHz)
- Short exposure (1-10 ms)
- Low averages (1-5)
- Can achieve 100+ Hz frame rates

### For High SNR
- Longer exposure (50-500 ms)
- High averages (50-255)
- Trades speed for signal quality
- Good for low-light spectra

### For Low Power
- Use STM32F103 firmware (800 kHz)
- Moderate exposure and averaging
- Lower clock speed saves energy

## Firmware Constraints

### STM32F40x (2 MHz MCLK)
- Min SH: 20 ticks (10 µs)
- Max SH: 4,294,967,295 ticks (~35 minutes)
- Min ICG: 14,776 ticks (7.4 ms)

### STM32F103 (800 kHz MCLK)
- Min SH: 8 ticks (10 µs)
- Max SH: 4,294,967,295 ticks (~89 minutes)
- Min ICG: 14,776 ticks (18.5 ms)

## Testing Without Hardware

The app includes mock data mode for desktop testing:
1. Run `python3 main.py` on desktop
2. Select connection type
3. Mock devices will appear in device list
4. Connect and capture simulated CCD data
5. Test exposure and averaging controls
6. Verify .dat file saving works

Mock data generates random 12-bit values for 3648 pixels, simulating real TCD1304 output.
