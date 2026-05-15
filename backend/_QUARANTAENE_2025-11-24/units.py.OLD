def kw_to_w(kw): return kw * 1_000
def mw_to_w(mw): return mw * 1_000_000
def kv_to_v(kv): return kv * 1_000
def mva_to_va(mva): return mva * 1_000_000
def va_to_mva(va): return va / 1_000_000
def w_to_kw(w): return w / 1_000
def km_to_m(km): return km * 1_000

def validate_positive(value, name):
    if value is None or value <= 0:
        raise ValueError(f"{name} muss positiv sein, ist aber {value}")
    return value

def validate_range(value, min_v, max_v, name):
    if value < min_v or value > max_v:
        raise ValueError(f"{name} = {value} ausserhalb [{min_v}, {max_v}]")
    return value
