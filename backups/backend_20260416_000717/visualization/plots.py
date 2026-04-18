import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

def plot_voltage_profile(net):
    if net.res_bus.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f'Bus {i}' for i in net.res_bus.index],
        y=net.res_bus.vm_pu.values,
        marker_color=['green' if 0.95 <= v <= 1.05 else 'red' for v in net.res_bus.vm_pu.values]
    ))
    fig.add_hline(y=1.05, line_dash='dash', line_color='red')
    fig.add_hline(y=0.95, line_dash='dash', line_color='red')
    fig.update_layout(title='Spannungsprofil', xaxis_title='Bus', yaxis_title='Spannung (p.u.)')
    return fig

def plot_loading(net):
    if net.res_line.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f'Leitung {i}' for i in net.res_line.index],
        y=net.res_line.loading_percent.values,
        marker_color=['green' if l < 80 else 'orange' if l < 100 else 'red' for l in net.res_line.loading_percent.values]
    ))
    fig.add_hline(y=100, line_dash='dash', line_color='red')
    fig.update_layout(title='Leitungsauslastung', xaxis_title='Leitung', yaxis_title='Auslastung (%)')
    return fig
