import math
from typing import List, Tuple, Optional
from models import (
    GridCheckInput, GridCheckOutput, MetricResult, N1Result,
    CostEstimate, Recommendation, ScenarioResult, SubScores,
    PlausibilityWarning, ShortCircuitResult, ProfileSpecificOutput,
    VoltageLevel, GridTopology, ConfidenceLevel, ProjectType, UserProfile
)
from constants import (
    VOLTAGE_LEVELS, REFERENCE_VALUES, CABLE_DATABASE, DEFAULT_CABLE,
    TRAFO_DEFAULTS, COST_REFERENCE, THRESHOLDS, PLAUSIBILITY,
    URBAN_PLZ_PREFIXES, ALPHA_AL, ALPHA_CU, TEMP_REF, SCORE_WEIGHTS
)
from units import kw_to_w, kv_to_v, mva_to_va, va_to_mva, w_to_kw, km_to_m


def get_urban_factor(plz):
    return 1.3 if plz[:2] in URBAN_PLZ_PREFIXES else 1.0


def get_confidence(inp):
    g = inp.grid
    count = sum([
        g.sk_mva is not None, g.sk_mva_min is not None,
        g.cable_type is not None, g.cable_length_km is not None,
        g.trafo_s_mva is not None, g.trafo_uk_percent is not None,
        g.rx_ratio is not None,
    ])
    if count >= 5: return ConfidenceLevel.B
    if count >= 3: return ConfidenceLevel.C
    return ConfidenceLevel.D


def count_default_fields(inp):
    g = inp.grid
    fields = [g.sk_mva, g.sk_mva_min, g.cable_type, g.cable_length_km,
              g.trafo_s_mva, g.trafo_uk_percent, g.rx_ratio]
    manual = sum(1 for f in fields if f is not None)
    return manual, len(fields)


def check_plausibility(inp):
    warnings = []
    vl = inp.grid.voltage_level.value
    p_kw = inp.plant.p_max_kw
    plaus = PLAUSIBILITY.get(vl, {})
    if plaus:
        if p_kw < plaus["p_min_kw"]:
            lower = {"MS_10": "NS", "MS_20": "NS", "MS_30": "NS", "HS": "MS_20", "HoeS": "HS"}.get(vl)
            msg = f"Leistung {p_kw} kW niedrig fuer {vl}."
            if lower: msg += f" {lower}-Anschluss pruefen."
            warnings.append(PlausibilityWarning(field="p_max_kw", message=msg, severity="warnung"))
        if p_kw > plaus["p_max_kw"]:
            higher = {"NS": "MS_20", "MS_10": "MS_20", "MS_20": "HS", "MS_30": "HS", "HS": "HoeS"}.get(vl)
            msg = f"Leistung {p_kw} kW ueberschreitet Bereich fuer {vl}."
            if higher: msg += f" Hoehere Ebene ({higher}) pruefen."
            warnings.append(PlausibilityWarning(field="p_max_kw", message=msg, severity="fehler"))
    if inp.plant.connection_type.value == "einphasig" and p_kw > 4.6:
        warnings.append(PlausibilityWarning(field="connection_type",
            message=f"Einphasig bei {p_kw} kW: Schieflastgrenze 4.6 kVA pruefen.", severity="warnung"))
    if inp.plant.cos_phi == 1.0 and inp.plant.q_regulation.value in ["Q(U)", "Q(P)"]:
        warnings.append(PlausibilityWarning(field="cos_phi",
            message="cos(phi)=1.0 bei aktiver Q-Regelung widerspruechlich.", severity="warnung"))
    return warnings


def assess_data_quality(inp, confidence):
    manual, total = count_default_fields(inp)
    ratio = manual / total if total > 0 else 0
    if ratio >= 0.7: return 90, "Gute Datenbasis - Ergebnis belastbar."
    if ratio >= 0.4: return 60, "Mittlere Datenbasis - Orientierung."
    return 30, "WARNUNG: Ueber 60% Referenzwerte. Ergebnis nur als grobe Indikation."


def resolve_grid_params(inp):
    g = inp.grid
    vl = g.voltage_level.value
    uf = get_urban_factor(inp.project.plz)
    ref = REFERENCE_VALUES[vl]
    tdef = TRAFO_DEFAULTS[vl]
    sk = g.sk_mva or ref["sk_mva"] * uf
    sk_min = g.sk_mva_min or sk * 0.6
    ts = g.trafo_s_mva or tdef["s_mva"]
    tuk = g.trafo_uk_percent or tdef["uk_percent"]
    dist = g.cable_length_km or ref["dist_km"] / uf
    ck = g.cable_type if g.cable_type and g.cable_type in CABLE_DATABASE else DEFAULT_CABLE[vl]
    cable = CABLE_DATABASE[ck]
    alpha = ALPHA_AL if cable["material"] == "Al" else ALPHA_CU
    r_cor = cable["r_ohm_km"] * (1 + alpha * (g.cable_temp_c - TEMP_REF))
    if g.rx_ratio: rx = g.rx_ratio
    elif vl == "NS": rx = 1.5
    elif vl.startswith("MS"): rx = 0.5
    else: rx = 0.1
    return {
        "sk_mva": sk, "sk_mva_min": sk_min,
        "u_nom_kv": VOLTAGE_LEVELS[vl]["u_nom_kv"],
        "u_nom_v": kv_to_v(VOLTAGE_LEVELS[vl]["u_nom_kv"]),
        "trafo_s_mva": ts, "trafo_s_va": mva_to_va(ts),
        "trafo_uk": tuk / 100.0, "trafo_count": g.trafo_count,
        "dist_km": dist, "dist_m": km_to_m(dist),
        "cable_key": ck, "r_ohm_km": r_cor, "x_ohm_km": cable["x_ohm_km"],
        "i_max_a": cable["i_max_a"],
        "delta_u_warn": VOLTAGE_LEVELS[vl]["delta_u_warn"],
        "delta_u_crit": VOLTAGE_LEVELS[vl]["delta_u_crit"],
        "tar": VOLTAGE_LEVELS[vl]["tar"], "vl": vl, "rx_source": rx,
    }


def calc_plant_pqs(inp):
    pl = inp.plant
    p = kw_to_w(pl.p_max_kw) * pl.gleichzeitigkeitsfaktor
    phi = math.acos(pl.cos_phi)
    q = p * math.tan(phi)
    s = p / pl.cos_phi
    pf = kw_to_w(pl.p_feed_in_kw or pl.p_max_kw * 0.95)
    pc = kw_to_w(pl.p_consumption_kw or pl.p_max_kw * 0.05)
    return {"p_w": p, "q_var": q, "s_va": s,
            "p_feed_w": pf, "q_feed_var": pf * math.tan(phi), "s_feed_va": pf / pl.cos_phi,
            "p_cons_w": pc, "cos_phi": pl.cos_phi, "phi_rad": phi}


def calc_existing_pqs(inp):
    g = inp.grid
    pl = kw_to_w(g.existing_load_kw)
    pf = kw_to_w(g.existing_feed_in_kw)
    phi = math.acos(g.existing_cos_phi)
    return {"p_load_w": pl, "q_load_var": pl * math.tan(phi),
            "p_feed_w": pf, "q_feed_var": pf * math.tan(phi)}


def calc_impedances(d):
    u = d["u_nom_v"]
    rx = d["rx_source"]
    z_q = (u ** 2) / mva_to_va(d["sk_mva"])
    x_q = z_q / math.sqrt(1 + rx ** 2)
    r_q = rx * x_q
    z_q_max = (u ** 2) / mva_to_va(d["sk_mva_min"])
    x_q_max = z_q_max / math.sqrt(1 + rx ** 2)
    r_q_max = rx * x_q_max
    z_t = d["trafo_uk"] * (u ** 2) / d["trafo_s_va"]
    x_t = z_t / math.sqrt(1 + 0.01)
    r_t = 0.1 * x_t
    if d["trafo_count"] > 1:
        r_t /= d["trafo_count"]
        x_t /= d["trafo_count"]
    r_l = d["r_ohm_km"] * d["dist_km"]
    x_l = d["x_ohm_km"] * d["dist_km"]
    r_tot = r_q + r_t + r_l
    x_tot = x_q + x_t + x_l
    z_tot = math.sqrt(r_tot**2 + x_tot**2)
    z_tot_max = math.sqrt((r_q_max+r_t+r_l)**2 + (x_q_max+x_t+x_l)**2)
    return {"r_q": r_q, "x_q": x_q, "r_t": r_t, "x_t": x_t,
            "r_l": r_l, "x_l": x_l, "r_total": r_tot, "x_total": x_tot,
            "z_total": z_tot, "z_total_max": z_tot_max}


def calc_delta_u(p, q, r, x, u_nom):
    return (p * r + q * x) / (u_nom ** 2)


def calc_betriebsstrom(s_va, u_nom):
    return s_va / (math.sqrt(3) * u_nom)


def calc_short_circuit(plant, imp, d):
    u = d["u_nom_v"]
    c_max = 1.1
    c_min = 0.95 if d["vl"] == "NS" else 1.0
    ik_max = (c_max * u) / (math.sqrt(3) * imp["z_total"]) if imp["z_total"] > 0 else 0
    ik_min = (c_min * u) / (math.sqrt(3) * imp["z_total_max"]) if imp["z_total_max"] > 0 else 0
    ib = calc_betriebsstrom(plant["s_va"], u)
    ik_ib = ik_min / ib if ib > 0 else 9999
    sk_sn = mva_to_va(d["sk_mva"]) / plant["s_va"] if plant["s_va"] > 0 else 9999
    if ik_ib < 3: status, det = "kritisch", "Schutzausloesung nicht gesichert!"
    elif ik_ib < 6: status, det = "warnung", "Schutzausloesung grenzwertig."
    else: status, det = "ok", "Schutzausloesung plausibel."
    detail = f"Ik_max={ik_max:.0f}A, Ik_min={ik_min:.0f}A, Ik/Ib={ik_ib:.1f} - {det}"
    return ShortCircuitResult(ik_max_a=round(ik_max), ik_min_a=round(ik_min),
        sk_sn_ratio=round(sk_sn, 1), ik_ib_ratio=round(ik_ib, 1), status=status, detail=detail)


def calc_netzrueckwirkung(plant, d):
    s = plant["s_va"]
    sk = mva_to_va(d["sk_mva"])
    anteil = s / sk if sk > 0 else 1.0
    sk_sn = sk / s if s > 0 else 9999
    if anteil >= THRESHOLDS["netzrueckwirkung_kritisch"]: nrs = "kritisch"
    elif anteil >= THRESHOLDS["netzrueckwirkung_pruefung"]: nrs = "pruefung"
    elif anteil >= THRESHOLDS["netzrueckwirkung_hinweis"]: nrs = "hinweis"
    else: nrs = "ok"
    ms = "kritisch" if nrs == "kritisch" else ("warnung" if nrs in ["pruefung","hinweis"] else "ok")
    det = f"S/Sk={anteil*100:.2f}% (Sk/Sn={sk_sn:.1f})"
    metric = MetricResult(name="Netzrueckwirkung", value=round(anteil*100,2),
        unit="%", limit=THRESHOLDS["netzrueckwirkung_pruefung"]*100, status=ms, detail=det)
    return anteil, nrs, metric


def calc_scenarios(plant, existing, imp, d):
    u = d["u_nom_v"]
    ts = d["trafo_s_va"] * d["trafo_count"]
    r = imp["r_l"] + imp["r_t"]
    x = imp["x_l"] + imp["x_t"]
    results = []
    configs = [
        ("Max Einspeisung", plant["p_feed_w"] - existing["p_load_w"]*0.2,
         plant["q_feed_var"] - existing["q_load_var"]*0.2),
        ("Max Bezug", -(plant["p_cons_w"]+existing["p_load_w"]),
         -(plant["q_var"]*0.05+existing["q_load_var"])),
        ("Mischfall", plant["p_feed_w"]-existing["p_load_w"],
         plant["q_feed_var"]-existing["q_load_var"]),
    ]
    for name, pn, qn in configs:
        du = calc_delta_u(pn, qn, r, x, u)
        sn = math.sqrt(pn**2 + qn**2)
        ausl = sn / ts if ts > 0 else 999
        st = "ok"
        if abs(du) > d["delta_u_crit"] or ausl > 1.0: st = "kritisch"
        elif abs(du) > d["delta_u_warn"] or ausl > 0.8: st = "warnung"
        results.append(ScenarioResult(name=name, delta_u_percent=round(du*100,2),
            auslastung_percent=round(ausl*100,1), status=st))
    p1, q1 = configs[0][1], configs[0][2]
    du1 = calc_delta_u(p1, q1, r, x, u)
    s1 = math.sqrt(p1**2 + q1**2)
    tn1 = d["trafo_s_va"]*(d["trafo_count"]-1) if d["trafo_count"]>1 else ts
    an1 = s1/tn1 if tn1>0 else 999
    stn1 = "ok"
    if abs(du1) > d["delta_u_crit"] or an1 > 1.0: stn1 = "kritisch"
    elif abs(du1) > d["delta_u_warn"] or an1 > 0.8: stn1 = "warnung"
    results.append(ScenarioResult(name="N-1 Reserve", delta_u_percent=round(du1*100,2),
        auslastung_percent=round(an1*100,1), status=stn1))
    return results


def calc_n1(inp, scenarios, imp, d):
    reasons = []
    passed = True
    topo = inp.grid.grid_topology
    if topo == GridTopology.STICHLEITUNG:
        reasons.append("Stichleitung: keine Redundanz."); passed = False
    elif topo == GridTopology.RADIAL:
        reasons.append("Radial: eingeschraenkte Redundanz.")
    elif topo == GridTopology.UNBEKANNT:
        reasons.append("Topologie unbekannt: konservativ nicht N-1."); passed = False
    elif topo == GridTopology.RING:
        reasons.append("Ring: N-1 plausibel.")
    elif topo == GridTopology.VERMASCHT:
        reasons.append("Vermascht: gute N-1 Voraussetzungen.")
    for s in scenarios:
        if s.status == "kritisch":
            reasons.append(f"{s.name}: kritisch (du={s.delta_u_percent}%, ausl={s.auslastung_percent}%)")
            passed = False
    note = "Vereinfachter Pre-Screen. Keine echte Ausfallsimulation."
    return N1Result(passed=passed, reasons=reasons, topology_note=note)


def calc_costs(inp, d):
    vl = d["vl"]
    ref = COST_REFERENCE[vl]
    c = inp.costs
    ic = c is not None and any([c.tiefbau_eur_m, c.kabel_eur_m, c.trafostation_eur, c.schaltanlage_eur]) if c else False
    if ic:
        tr = ((c.tiefbau_eur_m or 0) + (c.kabel_eur_m or 0)) * d["dist_m"]
        st = (c.trafostation_eur or 0) + (c.schaltanlage_eur or 0)
        pl = c.planung_eur or (tr + st) * 0.1
        cf = ConfidenceLevel.B
    else:
        tr = ref["trasse_eur_km"] * d["dist_km"]
        st = ref["station_eur"]
        pl = (tr + st) * 0.1
        cf = ConfidenceLevel.D
    return CostEstimate(trasse_eur=round(tr), station_eur=round(st),
        planung_eur=round(pl), total_eur=round(tr+st+pl), is_custom=ic, confidence=cf)


def calc_sub_scores(metrics, n1, sc, dq_score, scenarios, inp):
    cap = 100
    volt = 100
    scs = 100
    sec = 100
    for m in metrics:
        if m.name == "Trafoauslastung":
            if m.status == "kritisch": cap -= 40
            elif m.status == "warnung": cap -= 20
        if m.name == "Leitungsauslastung":
            if m.status == "kritisch": cap -= 40
            elif m.status == "warnung": cap -= 20
        if m.name == "Spannungsaenderung":
            if m.status == "kritisch": volt -= 50
            elif m.status == "warnung": volt -= 25
    if sc.status == "kritisch": scs -= 50
    elif sc.status == "warnung": scs -= 25
    if sc.sk_sn_ratio < THRESHOLDS["sk_sn_red"]: scs -= 30
    elif sc.sk_sn_ratio < THRESHOLDS["sk_sn_yellow"]: scs -= 15
    if not n1.passed: sec -= 40
    for s in scenarios:
        if s.status == "kritisch": sec -= 15
        elif s.status == "warnung": sec -= 5
    if inp.plant.storage_kwh and inp.plant.storage_kwh > 0: cap = min(100, cap+5)
    if inp.plant.q_regulation.value in ["Q(U)", "Q(P)"]: volt = min(100, volt+5)
    return SubScores(capacity=max(0,min(100,cap)), voltage=max(0,min(100,volt)),
        short_circuit=max(0,min(100,scs)), security=max(0,min(100,sec)),
        data_quality=max(0,min(100,dq_score)))


def calc_weighted_score(sub):
    w = SCORE_WEIGHTS
    raw = (sub.capacity*w["capacity"] + sub.voltage*w["voltage"] +
           sub.short_circuit*w["short_circuit"] + sub.security*w["security"] +
           sub.data_quality*w["data_quality"])
    return max(0, min(100, round(raw)))


def check_hard_override(metrics, sc):
    reasons = []
    for m in metrics:
        if m.name == "Trafoauslastung" and m.value > 100:
            reasons.append(f"Trafo ueberlastet ({m.value}%)")
        if m.name == "Leitungsauslastung" and m.value > 100:
            reasons.append(f"Leitung ueberlastet ({m.value}%)")
        if m.name == "Spannungsaenderung" and abs(m.value) > 5:
            reasons.append(f"Spannung {m.value}% > 5%")
    if sc.ik_ib_ratio < 3:
        reasons.append(f"Ik/Ib={sc.ik_ib_ratio} < 3")
    if reasons: return True, "; ".join(reasons)
    return False, None


def build_profile_output(inp, metrics, costs, n1, score, sc):
    p = inp.project.user_profile
    sec = {}
    if p == UserProfile.PROJEKTIERER:
        steps = []
        if score >= 70: steps.append("NAP einreichen")
        elif score >= 40: steps.append("Vorabstimmung VNB"); steps.append("NVP beauftragen")
        else: steps.append("Standortalternative pruefen")
        sec["naechste_schritte"] = steps
        sec["kosten"] = {"gesamt": costs.total_eur, "confidence": costs.confidence.value}
    elif p == UserProfile.NETZBETREIBER:
        sec["metriken"] = [{"name": m.name, "wert": m.value, "limit": m.limit, "status": m.status} for m in metrics]
        sec["n1"] = {"bestanden": n1.passed, "gruende": n1.reasons}
        sec["kurzschluss"] = {"ik_max": sc.ik_max_a, "ik_min": sc.ik_min_a, "sk_sn": sc.sk_sn_ratio}
    elif p == UserProfile.INVESTOR:
        risiko = "gering" if score >= 70 else ("mittel" if score >= 40 else "hoch")
        sec["risiko"] = {"stufe": risiko, "score": score, "kosten": costs.total_eur}
    elif p == UserProfile.PARKBETREIBER:
        sec["netzdienlichkeit"] = {"speicher": inp.plant.storage_kwh or 0,
            "q_regelung": inp.plant.q_regulation.value}
    return ProfileSpecificOutput(profile=p.value, sections=sec)


def build_recommendations(metrics, n1, nr_status, sc, inp, d):
    recs = []
    for m in metrics:
        if m.status == "kritisch":
            recs.append(Recommendation(category="kritisch", text=f"{m.name}: {m.detail}"))
        elif m.status == "warnung":
            recs.append(Recommendation(category="warnung", text=f"{m.name}: {m.detail}"))
    if not n1.passed:
        recs.append(Recommendation(category="kritisch", text="N-1 nicht erfuellt: Redundanz pruefen."))
    if nr_status in ["pruefung", "kritisch"]:
        recs.append(Recommendation(category="warnung", text="Netzrueckwirkungsstudie empfohlen."))
    if sc.status == "kritisch":
        recs.append(Recommendation(category="kritisch", text=f"Kurzschluss: {sc.detail}"))
    if inp.plant.q_regulation.value == "keine":
        recs.append(Recommendation(category="info", text="Blindleistungsregelung empfohlen (Q(U) oder cos(phi)(P))."))
    if not inp.plant.has_frt:
        recs.append(Recommendation(category="info", text="FRT-Faehigkeit sicherstellen."))
    if not inp.plant.has_remote_control:
        recs.append(Recommendation(category="info", text="Fernwirktechnik gem. TAR vorsehen."))
    if not recs:
        recs.append(Recommendation(category="ok", text="Keine kritischen Befunde. Anschluss erscheint realisierbar."))
    return recs


def run_analysis(inp):
    confidence = get_confidence(inp)
    plaus = check_plausibility(inp)
    dq_score, dq_note = assess_data_quality(inp, confidence)
    d = resolve_grid_params(inp)
    plant = calc_plant_pqs(inp)
    existing = calc_existing_pqs(inp)
    imp = calc_impedances(d)
    u = d["u_nom_v"]
    r_net = imp["r_l"] + imp["r_t"]
    x_net = imp["x_l"] + imp["x_t"]
    du = calc_delta_u(plant["p_feed_w"], plant["q_feed_var"], r_net, x_net, u)
    ib = calc_betriebsstrom(plant["s_va"], u)
    trafo_total = d["trafo_s_va"] * d["trafo_count"]
    trafo_ausl = plant["s_va"] / trafo_total if trafo_total > 0 else 999
    leit_ausl = ib / d["i_max_a"] if d["i_max_a"] > 0 else 999
    metrics = []
    du_st = "ok"
    if abs(du) > d["delta_u_crit"]: du_st = "kritisch"
    elif abs(du) > d["delta_u_warn"]: du_st = "warnung"
    metrics.append(MetricResult(name="Spannungsaenderung", value=round(du*100,2),
        unit="%", limit=d["delta_u_crit"]*100, status=du_st,
        detail=f"Delta_u = {du*100:.2f}% (Grenze {d['delta_u_crit']*100}%)"))
    ta_st = "ok"
    if trafo_ausl > 1.0: ta_st = "kritisch"
    elif trafo_ausl > 0.8: ta_st = "warnung"
    metrics.append(MetricResult(name="Trafoauslastung", value=round(trafo_ausl*100,1),
        unit="%", limit=100, status=ta_st,
        detail=f"S_Anlage/S_Trafo = {trafo_ausl*100:.1f}%"))
    la_st = "ok"
    if leit_ausl > 1.0: la_st = "kritisch"
    elif leit_ausl > 0.8: la_st = "warnung"
    metrics.append(MetricResult(name="Leitungsauslastung", value=round(leit_ausl*100,1),
        unit="%", limit=100, status=la_st,
        detail=f"Ib/Imax = {leit_ausl*100:.1f}%"))
    sc = calc_short_circuit(plant, imp, d)
    nr_anteil, nr_status, nr_metric = calc_netzrueckwirkung(plant, d)
    metrics.append(nr_metric)
    scenarios = calc_scenarios(plant, existing, imp, d)
    n1 = calc_n1(inp, scenarios, imp, d)
    costs = calc_costs(inp, d)
    sub = calc_sub_scores(metrics, n1, sc, dq_score, scenarios, inp)
    score = calc_weighted_score(sub)
    ho, ho_reason = check_hard_override(metrics, sc)
    if ho:
        status = "kritisch"
        status_text = f"Harter Verstoss: {ho_reason}"
    elif score >= 70:
        status = "ok"
        status_text = "Anschluss erscheint realisierbar."
    elif score >= 40:
        status = "bedingt"
        status_text = "Anschluss moeglich, Einschraenkungen beachten."
    else:
        status = "kritisch"
        status_text = "Anschluss kritisch, Massnahmen erforderlich."
    recs = build_recommendations(metrics, n1, nr_status, sc, inp, d)
    prof = build_profile_output(inp, metrics, costs, n1, score, sc)
    return GridCheckOutput(
        confidence=confidence, score=score, sub_scores=sub,
        status=status, status_text=status_text,
        hard_override=ho, hard_override_reason=ho_reason,
        plausibility_warnings=plaus, data_quality_note=dq_note,
        metrics=metrics, short_circuit=sc, scenarios=scenarios,
        n1=n1, costs=costs, recommendations=recs,
        netzrueckwirkung_anteil=round(nr_anteil,4),
        netzrueckwirkung_status=nr_status,
        q_max_kvar=round(plant["q_var"]/1000, 1),
        s_max_kva=round(plant["s_va"]/1000, 1),
        applicable_tar=d["tar"],
        profile_output=prof,
        input_snapshot=inp.dict(),
    )

def berechne_netzcheck(
    typ: str,
    leistung_kw: float,
    plz: str,
    spannung_kv=None,
    skv_mva=None,
    bestehende_einspeisung_kw=0,
    leitungstyp="NAYY 150",
    leitungslaenge_km=1.0,
):
    """Adapter fuer api/routes.py -> run_analysis()"""
    from models import (
        GridCheckInput, ProjectMeta, PlantInput, GridInput,
        ProjectType, VoltageLevel, ConnectionType, QRegulation,
        GridTopology, UserProfile
    )

    # Spannungsebene ableiten
    if spannung_kv is None:
        if leistung_kw <= 135: spannung_kv = 0.4
        elif leistung_kw <= 5000: spannung_kv = 20.0
        elif leistung_kw <= 120000: spannung_kv = 110.0
        else: spannung_kv = 380.0

    vl_map = {0.4: "NS", 10.0: "MS_10", 20.0: "MS_20", 30.0: "MS_30", 110.0: "HS", 380.0: "HoeS"}
    vl_str = vl_map.get(spannung_kv, "NS")
    try: vl = VoltageLevel(vl_str)
    except: vl = VoltageLevel.NS

    try: pt = ProjectType(typ)
    except: pt = ProjectType.PV

    inp = GridCheckInput(
        project=ProjectMeta(name="API-Check", plz=plz, user_profile=UserProfile.PROJEKTIERER, project_type=pt),
        plant=PlantInput(
            p_max_kw=leistung_kw,
            cos_phi=0.9,
            connection_type=ConnectionType.DREIPHASIG,
            q_regulation=QRegulation.COSPHI_P,
            gleichzeitigkeitsfaktor=1.0,
        ),
        grid=GridInput(
            voltage_level=vl,
            sk_mva=skv_mva,
            existing_feed_in_kw=bestehende_einspeisung_kw,
            cable_type=leitungstyp if leitungstyp in CABLE_DATABASE else None,
            cable_length_km=leitungslaenge_km,
            grid_topology=GridTopology.UNBEKANNT,
        ),
    )

    out = run_analysis(inp)

    # Mapping auf altes routes.py Format
    du_metric = next((m for m in out.metrics if m.name == "Spannungsaenderung"), None)
    ta_metric = next((m for m in out.metrics if m.name == "Trafoauslastung"), None)
    la_metric = next((m for m in out.metrics if m.name == "Leitungsauslastung"), None)

    return {
        "score": out.score,
        "spannungsband_ok": du_metric.status == "ok" if du_metric else None,
        "thermische_auslastung_ok": (
            (ta_metric.status == "ok" if ta_metric else True) and
            (la_metric.status == "ok" if la_metric else True)
        ),
        "kurzschluss_ok": out.short_circuit.status == "ok",
        "n1_ok": out.n1.passed,
        "netzebene": vl_str,
        "empfehlung": "; ".join(r.text for r in out.recommendations),
        "details": {
            "status": out.status,
            "status_text": out.status_text,
            "confidence": out.confidence.value,
            "data_quality_note": out.data_quality_note,
            "sub_scores": out.sub_scores.dict(),
            "metrics": [m.dict() for m in out.metrics],
            "short_circuit": out.short_circuit.dict(),
            "scenarios": [s.dict() for s in out.scenarios],
            "n1": out.n1.dict(),
            "costs": out.costs.dict(),
            "netzrueckwirkung_anteil": out.netzrueckwirkung_anteil,
            "netzrueckwirkung_status": out.netzrueckwirkung_status,
            "plausibility_warnings": [w.dict() for w in out.plausibility_warnings],
            "hard_override": out.hard_override,
            "hard_override_reason": out.hard_override_reason,
            "applicable_tar": out.applicable_tar,
        }
    }
