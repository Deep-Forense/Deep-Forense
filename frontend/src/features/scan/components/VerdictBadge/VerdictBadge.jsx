import { FiAlertTriangle, FiCheckCircle, FiXCircle } from "react-icons/fi";
import { Badge } from "@/components/atoms/Badge";
import { VERDICT_PRESENTATION } from "@/features/scan/domain/scanPresentation";

const icons = { APPROVED: FiCheckCircle, SUSPICIOUS: FiAlertTriangle, REJECTED: FiXCircle, INCONCLUSIVE: FiAlertTriangle };

export default function VerdictBadge({ verdict }) {
  const presentation = VERDICT_PRESENTATION[verdict] || VERDICT_PRESENTATION.SUSPICIOUS;
  const Icon = icons[verdict] || FiAlertTriangle;
  return <Badge variant={presentation.variant}><Icon /> {presentation.label}</Badge>;
}
