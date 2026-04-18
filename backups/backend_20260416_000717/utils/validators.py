def validate_network(net):
    errors = []
    if len(net.bus) == 0:
        errors.append('Keine Busse definiert')
    if len(net.line) == 0 and len(net.trafo) == 0:
        errors.append('Keine Leitungen oder Trafos')
    if len(net.ext_grid) == 0:
        errors.append('Kein externes Netz definiert')
    return {'valid': len(errors) == 0, 'errors': errors}
