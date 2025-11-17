"""
Test script for STM32Controller
Verifies timing calculations and command generation
"""
from stm32_controller import STM32Controller


def test_stm32_controller():
    """Test STM32 controller functionality"""
    
    print("=" * 70)
    print("STM32 TCD1304 Controller Test")
    print("=" * 70)
    
    # Test STM32F40x firmware
    print("\n--- Testing STM32F40x (2MHz MCLK) ---")
    controller = STM32Controller('STM32F40x')
    
    # Test exposure times
    test_exposures = [0.001, 0.01, 0.1, 1.0]  # 1ms, 10ms, 100ms, 1s
    
    for exp_s in test_exposures:
        controller.set_exposure_time(exp_s)
        timing = controller.get_timing_info()
        
        print(f"\nExposure: {exp_s * 1000:.1f} ms")
        print(f"  SH period: {timing['sh_period_ticks']} ticks ({timing['sh_period_us']:.2f} µs)")
        print(f"  ICG period: {timing['icg_period_ticks']} ticks ({timing['icg_period_ms']:.2f} ms)")
        print(f"  ICG/SH ratio: {timing['icg_sh_ratio']:.1f}")
        print(f"  Command: {controller.format_command_hex()}")
        
        # Validate
        is_valid, msg = controller.validate_timing()
        print(f"  Valid: {is_valid} - {msg}")
    
    # Test averages
    print("\n--- Testing Averages ---")
    controller.set_exposure_time(0.01)  # 10ms
    
    for avg in [1, 10, 50, 100, 255]:
        controller.set_averages(avg)
        timing = controller.get_timing_info()
        
        print(f"\nAverages: {avg}")
        print(f"  Frame time: {timing['frame_time_ms']:.2f} ms")
        print(f"  Acquisition rate: {timing['acquisition_rate_hz']:.2f} Hz")
        print(f"  Command: {controller.format_command_hex()}")
    
    # Test STM32F103 firmware
    print("\n\n--- Testing STM32F103 (800kHz MCLK) ---")
    controller.set_firmware('STM32F103')
    controller.set_exposure_time(0.01)  # 10ms
    
    timing = controller.get_timing_info()
    print(f"\nExposure: 10 ms")
    print(f"  SH period: {timing['sh_period_ticks']} ticks ({timing['sh_period_us']:.2f} µs)")
    print(f"  ICG period: {timing['icg_period_ticks']} ticks ({timing['icg_period_ms']:.2f} ms)")
    print(f"  Command: {controller.format_command_hex()}")
    
    # Test exposure limits
    print("\n--- Exposure Limits ---")
    for fw in ['STM32F40x', 'STM32F103']:
        controller.set_firmware(fw)
        limits = controller.get_exposure_limits()
        print(f"\n{fw}:")
        print(f"  Min exposure: {limits['min_exposure_ms']:.6f} ms ({limits['min_exposure_s'] * 1e6:.2f} µs)")
        print(f"  Max exposure: {limits['max_exposure_s']:.2f} s")
    
    print("\n" + "=" * 70)
    print("All tests completed!")
    print("=" * 70)


if __name__ == '__main__':
    test_stm32_controller()
