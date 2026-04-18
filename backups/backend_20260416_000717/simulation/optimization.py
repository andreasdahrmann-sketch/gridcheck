import pandapower as pp
import numpy as np

def optimize_voltage(net, target_vm=1.0):
    results = []
    for idx in net.ext_grid.index:
        original = net.ext_grid.at[idx, 'vm_pu']
        best_vm = original
        best_dev = float('inf')
        for vm in np.arange(0.95, 1.06, 0.01):
            net.ext_grid.at[idx, 'vm_pu'] = vm
            try:
                pp.runpp(net)
                dev = net.res_bus.vm_pu.std()
                if dev < best_dev:
                    best_dev = dev
                    best_vm = vm
            except:
                pass
        net.ext_grid.at[idx, 'vm_pu'] = best_vm
        results.append({'grid': idx, 'optimal_vm': best_vm})
    return results
