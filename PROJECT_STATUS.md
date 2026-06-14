[33mcommit 002ebfabcd16ad63764ea09243117daf955000f3[m[33m ([m[1;36mHEAD[m[33m -> [m[1;32mmain[m[33m)[m
Author: Andre <andre@gridcheck.local>
Date:   Thu Jun 11 13:53:59 2026 +0200

    feat: engine v2.0 - physikalisch korrekt, N-1 hybrid, anlagentyp, cos-phi, kosten

[1mdiff --git a/backend/engine/berechnung.py b/backend/engine/berechnung.py[m
[1mindex e67e17d..06138d4 100644[m
[1m--- a/backend/engine/berechnung.py[m
[1m+++ b/backend/engine/berechnung.py[m
[36m@@ -1509,6 +1509,80 @@[m [mdef bewerte_stakeholder_konflikt(eingabe, projektprofil, speicher, umwelt, koste[m
     }[m
 [m
 [m
[32m+[m[32mdef baue_eingabe_quellen([m
[32m+[m[32m    *,[m
[32m+[m[32m    spannungsebene,[m
[32m+[m[32m    u_kv,[m
[32m+[m[32m    p_mw,[m
[32m+[m[32m    leitungstyp,[m
[32m+[m[32m    anschlussart,[m
[32m+[m[32m    entfernung_km,[m
[32m+[m[32m    cable_info,[m
[32m+[m[32m    cos_phi,[m
[32m+[m[32m    cos_phi_info,[m
[32m+[m[32m    sk_user,[m
[32m+[m[32m    sk_mva,[m
[32m+[m[32m    rx_ratio,[m
[32m+[m[32m    rx_user,[m
[32m+[m[32m    trafo_s_mva,[m
[32m+[m[32m    trafo_s_user,[m
[32m+[m[32m    trafo_uk,[m
[32m+[m[32m    trafo_uk_user,[m
[32m+[m[32m):[m
[32m+[m[32m    """Provenienz je Eingabefeld: 'nutzer' | 'standardwert' | 'modell'.[m
[32m+[m
[32m+[m[32m    Rein dokumentierend/additiv. Beeinflusst weder Berechnung noch Revisionshash.[m
[32m+[m[32m    """[m
[32m+[m[32m    def eintrag(feld, label, wert, einheit, quelle, begruendung):[m
[32m+[m[32m        return {[m
[32m+[m[32m            'feld': feld,[m
[32m+[m[32m            'label': label,[m
[32m+[m[32m            'wert': wert,[m
[32m+[m[32m            'einheit': einheit,[m
[32m+[m[32m            'quelle': quelle,[m
[32m+[m[32m            'begruendung': begruendung,[m
[32m+[m[32m        }[m
[32m+[m
[32m+[m[32m    cos_phi_user = cos_phi_info.get('quelle') == 'nutzer'[m
[32m+[m[32m    entfernung_modelliert = bool(cable_info.get('heuristisch'))[m
[32m+[m
[32m+[m[32m    return [[m
[32m+[m[32m        eintrag('nennspannung', 'Nennspannung', round(float(u_kv), 3), 'kV', 'nutzer',[m
[32m+[m[32m                'Pflichteingabe aus dem Anschlussprofil.'),[m
[32m+[m[32m        eintrag('leistung_mw', 'Anschlussleistung', round(float(p_mw), 4), 'MW', 'nutzer',[m
[32m+[m[32m                'Pflichteingabe aus dem Projektprofil.'),[m
[32m+[m[32m        eintrag('leitungstyp', 'Leitungstyp', leitungstyp, None, 'nutzer',[m
[32m+[m[32m                'Pflichteingabe; bestimmt Strombelastbarkeit und R/X-Belag.'),[m
[32m+[m[32m        eintrag('anschlussart', 'Anschlussart', anschlussart, None, 'nutzer',[m
[32m+[m[32m                'Pflichteingabe (Einspeisung/Entnahme/Speicher).'),[m
[32m+[m[32m        eintrag('entfernung_km', 'Leitungslaenge', round(float(entfernung_km), 3), 'km',[m
[32m+[m[32m                'modell' if entfernung_modelliert else 'nutzer',[m
[32m+[m[32m                cable_info.get('annahme') or 'Aus Eingabe uebernommen.'),[m
[32m+[m[32m        eintrag('cos_phi', 'Leistungsfaktor cos phi', round(float(cos_phi), 4), None,[m
[32m+[m[32m                'nutzer' if cos_phi_user else 'standardwert',[m
[32m+[m[32m                cos_phi_info.get('annahme') or f"Quelle: {cos_phi_info.get('quelle', 'unbekannt')}."),[m
[32m+[m[32m        eintrag('sk_mva', 'Netzkurzschlussleistung Sk', round(float(sk_mva), 2), 'MVA',[m
[32m+[m[32m                'nutzer' if sk_user is not None else 'standardwert',[m
[32m+[m[32m                'Eingabe verwendet.' if sk_user is not None[m
[32m+[m[32m                else ([m
[32m+[m[32m                    f"Konservativer Standardwert fuer {spannungsebene} "[m
[32m+[m[32m                    f"({SK_DEFAULT[spannungsebene]} MVA); keine verifizierten Netzbetreiberdaten."[m
[32m+[m[32m                )),[m
[32m+[m[32m        eintrag('rx_ratio', 'R/X-Verhaeltnis vorgelagertes Netz', round(float(rx_ratio), 3), None,[m
[32m+[m[32m                'nutzer' if rx_user else 'standardwert',[m
[32m+[m[32m                'Eingabe verwendet.' if rx_user[m
[32m+[m[32m                else f"Typischer Standardwert fuer {spannungsebene}."),[m
[32m+[m[32m        eintrag('trafo_s_mva', 'Transformator-Bemessungsleistung', round(float(trafo_s_mva), 3), 'MVA',[m
[32m+[m[32m                'nutzer' if trafo_s_user else 'standardwert',[m
[32m+[m[32m                'Eingabe verwendet.' if trafo_s_user[m
[32m+[m[32m                else f"Standard-Transformator fuer {spannungsebene}."),[m
[32m+[m[32m        eintrag('trafo_uk_prozent', 'Transformator-Kurzschlussspannung uk', round(float(trafo_uk), 2), '%',[m
[32m+[m[32m                'nutzer' if trafo_uk_user else 'standardwert',[m
[32m+[m[32m                'Eingabe verwendet.' if trafo_uk_user[m
[32m+[m[32m                else f"Typischer Standardwert fuer {spannungsebene}."),[m
[32m+[m[32m    ][m
[32m+[m
[32m+[m
 def erzeuge_transparenzblock(eingabe, dq, speicher, umwelt, stakeholder, n1):[m
     assumptions = [[m
         'Vorpruefung auf Basis des eingegebenen Projekt- und Anschlussprofils; keine verbindliche Netzanschlusszusage.',[m
[36m@@ -1664,6 +1738,29 @@[m [mdef berechne_netzanschluss(eingabe, dry_run=False, revision_context=None):[m
         0,[m
     )[m
 [m
[32m+[m[32m    # Eingabe-Quellen-Markierung (additiv, ohne Einfluss auf Berechnung oder Revisionshash):[m
[32m+[m[32m    # macht je Feld transparent, ob der Wert vom Nutzer stammt, ein konservativer[m
[32m+[m[32m    # Standardwert oder ein Modell-/Heuristik-Wert ist (Regel: Datenquellen/Annahmen getrennt halten).[m
[32m+[m[32m    eingabe_quellen = baue_eingabe_quellen([m
[32m+[m[32m        spannungsebene=spannungsebene,[m
[32m+[m[32m        u_kv=u_kv,[m
[32m+[m[32m        p_mw=p_mw,[m
[32m+[m[32m        leitungstyp=leitungstyp,[m
[32m+[m[32m        anschlussart=anschlussart,[m
[32m+[m[32m        entfernung_km=entfernung_km,[m
[32m+[m[32m        cable_info=cable_info,[m
[32m+[m[32m        cos_phi=cos_phi,[m
[32m+[m[32m        cos_phi_info=cos_phi_info,[m
[32m+[m[32m        sk_user=sk_user,[m
[32m+[m[32m        sk_mva=sk_mva,[m
[32m+[m[32m        rx_ratio=rx_ratio,[m
[32m+[m[32m        rx_user=eingabe.get('rx_ratio') is not None,[m
[32m+[m[32m        trafo_s_mva=trafo_s_mva,[m
[32m+[m[32m        trafo_s_user=eingabe.get('trafo_s_mva') is not None,[m
[32m+[m[32m        trafo_uk=trafo_uk,[m
[32m+[m[32m        trafo_uk_user=(eingabe.get('trafo_uk_prozent') is not None) or (eingabe.get('uk_prozent') is not None),[m
[32m+[m[32m    )[m
[32m+[m
     r_q, x_q = berechne_quellenimpedanz(u_kv, sk_mva, rx_ratio)[m
     r_t, x_t = berechne_trafoimpedanz(u_kv, trafo_s_mva, trafo_uk)[m
     r_l, x_l = berechne_leitungsimpedanz(leitungstyp, entfernung_km, parallele_systeme, temperatur_c)[m
[36m@@ -1723,6 +1820,7 @@[m [mdef berechne_netzanschluss(eingabe, dry_run=False, revision_context=None):[m
     transparenz = erzeuge_transparenzblock([m
         eingabe, datenqualitaet, speicher_bewertung, route_environment, stakeholder_bewertung, n1[m
     )[m
[32m+[m[32m    transparenz['eingabe_quellen'] = eingabe_quellen[m
     erweiterte_scores = erzeuge_erweiterte_scores([m
         speicher_bewertung, route_environment, stakeholder_bewertung[m
     )[m
