import type { Project } from "@/lib/api/projects";
import { getOfferDisplayName, getOfferProfile, getPackageScopeLabel, getReportScopeLabel } from "@/lib/billing-product";
import { resolveStakeholderProductPath } from "@/lib/stakeholder-product";

export type ProjectCommercialInsight = {
  stageLabel: string;
  stageTone: "neutral" | "info" | "warning" | "success";
  offerLabel: string;
  scopeLabel: string;
  reportLabel: string;
  summary: string;
  nextStep: string;
  actionLabel: string;
  actionHref: string;
  hasRun: boolean;
  needsDecision: boolean;
  hasServiceFollowup: boolean;
};

function toneFromDecision(stage: ProjectCommercialInsight["stageLabel"]): ProjectCommercialInsight["stageTone"] {
  if (stage.includes("Follow-up")) return "warning";
  if (stage.includes("Vertiefung")) return "info";
  if (stage.includes("Kein Check")) return "neutral";
  return "success";
}

export function getProjectCommercialInsight(project: Project): ProjectCommercialInsight {
  const result = project.role_results ?? {};
  const access = result.billing_access;
  const offerId = access?.offer_id;
  const packageScope = access?.package_scope;
  const reportScope = access?.report_scope ?? access?.package_scope;
  const decision = result.machbarkeit_stufe;
  const hasRun = Boolean(access || typeof result.score === "number");
  const profile = getOfferProfile(offerId, packageScope);
  const stakeholderPath = resolveStakeholderProductPath({
    kundentyp: project.role_inputs?.kundentyp,
    stakeholder_context: project.role_inputs?.stakeholder_context,
  });
  const stakeholderLabel =
    stakeholderPath === "vnb" ? "VNB" : stakeholderPath === "invest" ? "Invest" : "Projektierer";
  const offerLabel = hasRun ? getOfferDisplayName(offerId) : "Noch kein Analysepaket";
  const scopeLabel = hasRun ? getPackageScopeLabel(packageScope) : "Noch kein Scope";
  const reportLabel = hasRun ? getReportScopeLabel(reportScope) : "Noch keine Reporttiefe";

  if (!hasRun) {
    return {
      stageLabel: "Kein Check vorhanden",
      stageTone: "neutral",
      offerLabel,
      scopeLabel,
      reportLabel,
      summary: `${stakeholderLabel}-Projekt ohne gespeicherten Analyse-Run. Paket- und Rollenpfad sind noch nicht belastbar eingeordnet.`,
      nextStep:
        stakeholderPath === "invest"
          ? "Ersten Check starten und danach Kostenbandbreite, Datenbasis und Due-Diligence-Faehigkeit bewerten."
          : stakeholderPath === "vnb"
            ? "Ersten Check starten und danach Anfragepruefung, Auflagen und Datenbasis strukturiert verdichten."
            : "Ersten Check starten und danach Varianten, VNB-Vorbereitung und investorentaugliche Aufbereitung priorisieren.",
      actionLabel: "Projekt analysieren",
      actionHref: `/projects/${project.id}`,
      hasRun: false,
      needsDecision: true,
      hasServiceFollowup: false,
    };
  }

  if (access?.ops_followup_required) {
    return {
      stageLabel: "Service-Follow-up sichtbar",
      stageTone: "warning",
      offerLabel,
      scopeLabel,
      reportLabel,
      summary: `${stakeholderLabel}-Projekt mit sichtbarem Service-Nachlauf. ${profile.deliverable}`,
      nextStep:
        stakeholderPath === "invest"
          ? "Bearbeitungsstand im Tarifbereich pruefen und DD-/Risikofragen im betreuten Nachlauf konsolidieren."
          : stakeholderPath === "vnb"
            ? "Bearbeitungsstand im Tarifbereich pruefen und technische Nachreichungen/Auflagen bewusst begleiten."
            : "Bearbeitungsstand im Tarifbereich pruefen und Projekt-/Variantenlogik im Service-Nachlauf sauber halten.",
      actionLabel: "Service-Status ansehen",
      actionHref: "/settings",
      hasRun: true,
      needsDecision: false,
      hasServiceFollowup: true,
    };
  }

  if (packageScope === "basic") {
    const critical = decision === "orange" || decision === "rot";
    return {
      stageLabel: critical ? "Basis-Run mit Vertiefungsbedarf" : "Basis-Run vorhanden",
      stageTone: critical ? "warning" : "info",
      offerLabel,
      scopeLabel,
      reportLabel,
      summary: critical
        ? `${stakeholderLabel}-Projekt mit Basis-Run, aber klarem Vertiefungsbedarf statt weiterem Screening.`
        : `${stakeholderLabel}-Projekt im Basis-Scope und fuer die erste Vorqualifizierung ausreichend beschrieben.`,
      nextStep: critical
        ? stakeholderPath === "invest"
          ? "Premium oder Professional fuer belastbarere DD-, Risiko- und Kostenband-Sicht pruefen."
          : stakeholderPath === "vnb"
            ? "Premium oder Professional fuer vertiefte Vorpruefung, Auflagenbild und Prozesssicht pruefen."
            : "Premium oder Professional fuer Variantenvergleich, Kosten-/Trassensicht und VNB-Vorbereitung pruefen."
        : stakeholderPath === "invest"
          ? "Bei Portfolio-, Vergleichs- oder Kapitalbindungsdruck die Vertiefung auf Premium oder Pro sauber bewerten."
          : stakeholderPath === "vnb"
            ? "Bei tieferem Daten-, Audit- oder Auflagenbedarf die Vertiefung auf Premium oder Professional bewerten."
            : "Bei Hybrid-, Speicher-, Trassen- oder Freigabedruck den Wechsel auf Premium oder Pro sauber bewerten.",
      actionLabel: critical ? "Upgrade abstimmen" : "Pakete vergleichen",
      actionHref: critical ? "/contact?intent=upgrade" : "/settings",
      hasRun: true,
      needsDecision: true,
      hasServiceFollowup: false,
    };
  }

  if (offerId === "pro_lizenz") {
    const critical = decision === "orange" || decision === "rot";
    return {
      stageLabel: critical ? "Pro-Run mit Einzelfall-Risiko" : "Pro-Pfad aktiv",
      stageTone: critical ? "warning" : "success",
      offerLabel,
      scopeLabel,
      reportLabel,
      summary: critical
        ? `${stakeholderLabel}-Projekt im Pro-Pfad mit Einzelfallbild, das moeglicherweise nicht im reinen Self-Serve endet.`
        : `${stakeholderLabel}-Projekt passt in den laufenden Pro-Pfad und bleibt fachlich im wiederkehrenden Premium-Scope.`,
      nextStep: critical
        ? stakeholderPath === "invest"
          ? "Nur bei echter DD-/Strukturierungseskalation gezielt Professional fuer dieses Einzelprojekt abstimmen."
          : stakeholderPath === "vnb"
            ? "Nur bei echter Prozess- oder Integrationseskalation gezielt Professional fuer dieses Einzelprojekt abstimmen."
            : "Nur wenn echte strategische Begleitung noetig wird, den Wechsel zu Professional fuer dieses Einzelprojekt abstimmen."
        : stakeholderPath === "invest"
          ? "Im Pro-Pfad bleiben und nur bei echter Strukturierungseskalation Professional fuer dieses Einzelprojekt anfragen."
          : stakeholderPath === "vnb"
            ? "Im Pro-Pfad bleiben und nur bei echter Prozesseskalation oder Pilotbedarf Professional anfragen."
            : "Im Pro-Pfad bleiben und nur bei strategischer Eskalation gezielt Professional fuer dieses Einzelprojekt anfragen.",
      actionLabel: critical ? "Professional pruefen" : "Pro abstimmen",
      actionHref: critical ? "/contact?intent=professional" : "/contact?intent=pro",
      hasRun: true,
      needsDecision: critical,
      hasServiceFollowup: false,
    };
  }

  if (packageScope === "premium") {
    const critical = decision === "orange" || decision === "rot";
    return {
      stageLabel: critical ? "Premium-Run mit Strategiefall" : "Premium-Vertiefung vorhanden",
      stageTone: critical ? "warning" : "success",
      offerLabel,
      scopeLabel,
      reportLabel,
      summary: critical
        ? `${stakeholderLabel}-Projekt wurde vertieft geprueft, benoetigt fachlich aber eher strategische Begleitung als einen weiteren Standard-Run.`
        : `${stakeholderLabel}-Projekt liegt im vertieften Self-Serve-Scope und ist sauber fuer ein anspruchsvolleres Einzelvorhaben aufbereitet.`,
      nextStep: critical
        ? stakeholderPath === "invest"
          ? "Professional anfragen, wenn Strukturierung, Investorenkommunikation oder betreute DD-Nacharbeit benoetigt werden."
          : stakeholderPath === "vnb"
            ? "Professional anfragen, wenn Anschlussstrategie, Prozessbild oder betreute Nacharbeit benoetigt werden."
            : "Professional anfragen, wenn Anschlussstrategie, Visualisierung oder betreute Nacharbeit benoetigt werden."
        : stakeholderPath === "invest"
          ? "Bei mehreren aehnlichen Folgeprojekten eher Pro pruefen als weitere Einzelbuchungen fuer DD-Previews zu stapeln."
          : stakeholderPath === "vnb"
            ? "Bei mehreren aehnlichen Folgeprojekten eher Pro oder Pilot pruefen als weitere Einzelbuchungen zu stapeln."
            : "Bei mehreren aehnlichen Folgeprojekten eher Pro pruefen als weitere Einzelbuchungen zu stapeln.",
      actionLabel: critical ? "Professional anfragen" : "Pro vergleichen",
      actionHref: critical ? "/contact?intent=professional" : "/contact?intent=pro",
      hasRun: true,
      needsDecision: true,
      hasServiceFollowup: false,
    };
  }

  const stageLabel = profile.badge === "Servicepfad" ? "Servicepfad aktiv" : "Analysepfad aktiv";
  return {
    stageLabel,
    stageTone: toneFromDecision(stageLabel),
    offerLabel,
    scopeLabel,
    reportLabel,
    summary: profile.deliverable,
    nextStep: profile.nextStep,
    actionLabel: "Naechsten Schritt ansehen",
    actionHref: "/settings",
    hasRun: true,
    needsDecision: false,
    hasServiceFollowup: false,
  };
}

export function summarizeProjectPortfolio(projects: Project[]) {
  const insights = projects.map((project) => getProjectCommercialInsight(project));
  return {
    unchecked: insights.filter((item) => !item.hasRun).length,
    basis: insights.filter((item) => item.scopeLabel === "Basis-Scope").length,
    needsDecision: insights.filter((item) => item.needsDecision).length,
    serviceFollowups: insights.filter((item) => item.hasServiceFollowup).length,
  };
}
