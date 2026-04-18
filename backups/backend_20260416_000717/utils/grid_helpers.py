import numpy as np

def calculate_line_loading(power_flow, max_capacity):
    return (abs(power_flow) / max_capacity) * 100

def calculate_voltage_deviation(voltage, nominal=1.0):
    return ((voltage - nominal) / nominal) * 100

def check_thermal_limits(loading_percent, warning=80, critical=100):
    if loading_percent >= critical:
        return 'critical'
    elif loading_percent >= warning:
        return 'warning'
    return 'normal'
