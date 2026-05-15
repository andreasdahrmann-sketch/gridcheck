export { projectDeveloperReportProfile } from "./project-developer.profile";
export { gridOperatorReportProfile } from "./grid-operator.profile";
export { investorReportProfile } from "./investor.profile";

import type { StakeholderType } from "../types/gridcheck-report-data";
import type { ReportProfile } from "../types/report-profile";
import { gridOperatorReportProfile } from "./grid-operator.profile";
import { investorReportProfile } from "./investor.profile";
import { projectDeveloperReportProfile } from "./project-developer.profile";

const byStakeholder: Record<StakeholderType, ReportProfile> = {
  project_developer: projectDeveloperReportProfile,
  grid_operator: gridOperatorReportProfile,
  investor: investorReportProfile,
};

export function getReportProfile(stakeholder: StakeholderType): ReportProfile {
  return byStakeholder[stakeholder];
}
