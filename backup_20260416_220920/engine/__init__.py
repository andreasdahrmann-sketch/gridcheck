from .berechnung import berechne_netzanschluss
from .berechnung import berechne_netzanschluss as run_analysis
from .berechnung import berechne_netzanschluss as run_check
from .ki_modul import ki_bewertung
from .revision import speichere_revision
from .pdf_report import erstelle_pdf

def berechne_netzcheck(anlagentyp, leistung_kw, plz):
    leistung_mw = leistung_kw / 1000.0

    if leistung_mw <= 0.1:
        nennspannung = 0.4
        leitungstyp = "NAYY150"
    elif leistung_mw <= 5.0:
        nennspannung = 20.0
        leitungstyp = "NA2XS2Y150"
    else:
        nennspannung = 110.0
        leitungstyp = "AL240"

    eingabe = {
        "anlagentyp":        anlagentyp,
        "p_kw":              leistung_kw,
        "plz":               plz,
        "leistung_mw":       leistung_mw,
        "nennspannung":      nennspannung,
        "leitungstyp":       leitungstyp,
        "entfernung_km":     1.0,
        "anschlussart":      "Einspeisung",
        "cos_phi":           0.95,
        "parallele_systeme": 1,
    }
    return berechne_netzanschluss(eingabe)

__all__ = [
    'run_analysis', 'run_check', 'berechne_netzanschluss',
    'ki_bewertung', 'speichere_revision', 'erstelle_pdf', 'berechne_netzcheck'
]
