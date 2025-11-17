"""
STM32 TCD1304 CCD Controller
Handles firmware-specific timing and command generation for STM32 devices
Compatible with STM32F40x and STM32F103 firmware
"""
import struct
import math


class STM32Controller:
    """Controller for STM32-based TCD1304 CCD spectrometer"""
    
    # Firmware configurations
    FIRMWARE_CONFIGS = {
        'STM32F40x': {
            'mclk': 2000000,  # 2 MHz master clock
            'min_sh': 20,      # Minimum SH period in ticks
            'max_sh': 4294967295,  # 32-bit max
            'description': 'STM32F40x (2MHz MCLK)'
        },
        'STM32F103': {
            'mclk': 800000,   # 800 kHz master clock
            'min_sh': 8,       # Minimum SH period in ticks
            'max_sh': 4294967295,  # 32-bit max
            'description': 'STM32F103 (800kHz MCLK)'
        }
    }
    
    # TCD1304 constraints
    MIN_ICG_TICKS = 14776  # Minimum ICG period (readout time)
    MAX_AVERAGES = 255     # Maximum number of averages
    MIN_AVERAGES = 1       # Minimum number of averages
    
    def __init__(self, firmware='STM32F40x'):
        """
        Initialize STM32 controller
        
        Args:
            firmware: Firmware type ('STM32F40x' or 'STM32F103')
        """
        self.exposure_time = 0.01  # Default 10ms exposure
        self.averages = 1          # Default no averaging
        self._sh_period = None
        self._icg_period = None
        self.set_firmware(firmware)
    
    def set_firmware(self, firmware):
        """Set the firmware type"""
        if firmware not in self.FIRMWARE_CONFIGS:
            raise ValueError(f"Unknown firmware: {firmware}. Must be one of {list(self.FIRMWARE_CONFIGS.keys())}")
        
        self.firmware = firmware
        self.config = self.FIRMWARE_CONFIGS[firmware]
        self.mclk = self.config['mclk']
        self.min_sh = self.config['min_sh']
        self.max_sh = self.config['max_sh']
        
        # Recalculate timing when firmware changes
        self._update_timing()
    
    def get_firmware_list(self):
        """Get list of available firmware types"""
        return list(self.FIRMWARE_CONFIGS.keys())
    
    def get_firmware_description(self, firmware=None):
        """Get description of firmware"""
        if firmware is None:
            firmware = self.firmware
        return self.FIRMWARE_CONFIGS[firmware]['description']
    
    def set_exposure_time(self, exposure_seconds):
        """
        Set exposure time in seconds
        
        Args:
            exposure_seconds: Exposure time in seconds (e.g., 0.01 for 10ms)
        
        Returns:
            tuple: (actual_exposure_seconds, sh_ticks, icg_ticks)
        """
        # Calculate SH period in clock ticks
        sh_ticks = int(exposure_seconds * self.mclk)
        
        # Enforce minimum SH
        if sh_ticks < self.min_sh:
            sh_ticks = self.min_sh
        
        # Enforce maximum SH
        if sh_ticks > self.max_sh:
            sh_ticks = self.max_sh
        
        self.exposure_time = sh_ticks / self.mclk
        self._update_timing()
        
        return (self.exposure_time, self._sh_period, self._icg_period)
    
    def set_averages(self, averages):
        """
        Set number of averages
        
        Args:
            averages: Number of spectra to average (1-255)
        
        Returns:
            int: Actual averages value set
        """
        averages = int(averages)
        
        if averages < self.MIN_AVERAGES:
            averages = self.MIN_AVERAGES
        elif averages > self.MAX_AVERAGES:
            averages = self.MAX_AVERAGES
        
        self.averages = averages
        return self.averages
    
    def _update_timing(self):
        """Calculate SH and ICG periods based on current settings"""
        # Calculate SH period in ticks
        self._sh_period = int(self.exposure_time * self.mclk)
        
        # Ensure SH meets minimum
        if self._sh_period < self.min_sh:
            self._sh_period = self.min_sh
        
        # Calculate minimum ICG as multiple of SH that satisfies readout constraint
        # ICG must be >= MIN_ICG_TICKS and must be a multiple of SH
        min_multiplier = math.ceil(self.MIN_ICG_TICKS / self._sh_period)
        self._icg_period = min_multiplier * self._sh_period
        
        # Ensure ICG meets absolute minimum
        if self._icg_period < self.MIN_ICG_TICKS:
            self._icg_period = self.MIN_ICG_TICKS
    
    def generate_command(self):
        """
        Generate 12-byte command for STM32 firmware
        
        Command format (12 bytes):
        - Bytes 0-1: Header (0xAA, 0x55)
        - Bytes 2-5: SH period (32-bit big-endian)
        - Bytes 6-9: ICG period (32-bit big-endian)
        - Byte 10: Reserved (0x00)
        - Byte 11: Averages (1-255)
        
        Returns:
            bytes: 12-byte command
        """
        # Ensure timing is up to date
        self._update_timing()
        
        # Build command
        command = bytearray(12)
        
        # Header
        command[0] = 0xAA
        command[1] = 0x55
        
        # SH period (32-bit big-endian)
        command[2:6] = struct.pack('>I', self._sh_period)
        
        # ICG period (32-bit big-endian)
        command[6:10] = struct.pack('>I', self._icg_period)
        
        # Reserved byte
        command[10] = 0x00
        
        # Averages
        command[11] = self.averages
        
        return bytes(command)
    
    def get_timing_info(self):
        """
        Get detailed timing information
        
        Returns:
            dict: Timing parameters and constraints
        """
        self._update_timing()
        
        # Calculate actual frame time
        frame_time = (self._icg_period / self.mclk) * self.averages
        
        return {
            'firmware': self.firmware,
            'mclk_hz': self.mclk,
            'exposure_time_s': self.exposure_time,
            'exposure_time_ms': self.exposure_time * 1000,
            'sh_period_ticks': self._sh_period,
            'sh_period_us': (self._sh_period / self.mclk) * 1e6,
            'icg_period_ticks': self._icg_period,
            'icg_period_ms': (self._icg_period / self.mclk) * 1000,
            'averages': self.averages,
            'frame_time_s': frame_time,
            'frame_time_ms': frame_time * 1000,
            'acquisition_rate_hz': 1.0 / frame_time if frame_time > 0 else 0,
            'min_sh_ticks': self.min_sh,
            'min_icg_ticks': self.MIN_ICG_TICKS,
            'icg_sh_ratio': self._icg_period / self._sh_period if self._sh_period > 0 else 0
        }
    
    def get_exposure_limits(self):
        """
        Get exposure time limits for current firmware
        
        Returns:
            dict: Min and max exposure times in seconds
        """
        min_exposure_s = self.min_sh / self.mclk
        max_exposure_s = self.max_sh / self.mclk
        
        return {
            'min_exposure_s': min_exposure_s,
            'min_exposure_ms': min_exposure_s * 1000,
            'max_exposure_s': max_exposure_s,
            'max_exposure_ms': max_exposure_s * 1000
        }
    
    def format_command_hex(self):
        """Get command as hex string for debugging"""
        cmd = self.generate_command()
        return ' '.join(f'{b:02X}' for b in cmd)
    
    def validate_timing(self):
        """
        Validate current timing parameters
        
        Returns:
            tuple: (is_valid, error_message)
        """
        self._update_timing()
        
        # Check SH minimum
        if self._sh_period < self.min_sh:
            return (False, f"SH period {self._sh_period} is below minimum {self.min_sh}")
        
        # Check ICG minimum
        if self._icg_period < self.MIN_ICG_TICKS:
            return (False, f"ICG period {self._icg_period} is below minimum {self.MIN_ICG_TICKS}")
        
        # Check ICG is multiple of SH
        if self._icg_period % self._sh_period != 0:
            return (False, f"ICG period {self._icg_period} is not a multiple of SH period {self._sh_period}")
        
        # Check averages range
        if self.averages < self.MIN_AVERAGES or self.averages > self.MAX_AVERAGES:
            return (False, f"Averages {self.averages} out of range [{self.MIN_AVERAGES}, {self.MAX_AVERAGES}]")
        
        return (True, "OK")
