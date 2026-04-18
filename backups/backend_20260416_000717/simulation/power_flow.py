import pandapower as pp
import numpy as np

def run_power_flow(net):
    try:
        pp.runpp(net, algorithm='nr', max_iteration=100)
        return {
            'success': True,
            'bus_results': net.res_bus.to_dict(),
            'line_results': net.res_line.to_dict()
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def create_sample_network():
    net = pp.create_empty_network()
    bus1 = pp.create_bus(net, vn_kv=110, name='HV Bus')
    bus2 = pp.create_bus(net, vn_kv=20, name='MV Bus')
    bus3 = pp.create_bus(net, vn_kv=20, name='MV Bus 2')
    pp.create_ext_grid(net, bus=bus1, vm_pu=1.02)
    pp.create_transformer(net, hv_bus=bus1, lv_bus=bus2, std_type='25 MVA 110/20 kV')
    pp.create_line(net, from_bus=bus2, to_bus=bus3, length_km=5, std_type='NAYY 4x50 SE')
    pp.create_load(net, bus=bus3, p_mw=2.0, q_mvar=0.5, name='Last 1')
    pp.create_sgen(net, bus=bus3, p_mw=0.5, name='Solar 1')
    return net

def get_results_summary(net):
    return {
        'n_buses': len(net.bus),
        'n_lines': len(net.line),
        'min_voltage': net.res_bus.vm_pu.min(),
        'max_loading': net.res_line.loading_percent.max()
    }
