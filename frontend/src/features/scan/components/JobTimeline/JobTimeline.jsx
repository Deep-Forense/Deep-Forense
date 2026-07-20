import { FiCheckCircle, FiClock, FiXCircle } from "react-icons/fi";
import { JOB_STEP_LABELS } from "@/features/scan/domain/scanPresentation";

const formatTimestamp = (timestamp) =>
  timestamp
    ? new Intl.DateTimeFormat("es-EC", { dateStyle: "medium", timeStyle: "short" }).format(new Date(timestamp))
    : null;

function buildSteps(events) {
  const hasFailed = events.some((event) => event.type === "JOB_FAILED");
  const terminalType = hasFailed ? "JOB_FAILED" : "JOB_COMPLETED";
  const stepTypes = ["JOB_CREATED", "JOB_PROCESSING", terminalType];

  return stepTypes.map((type) => {
    const event = events.find((item) => item.type === type);
    return {
      type,
      label: JOB_STEP_LABELS[type],
      done: Boolean(event),
      timestamp: event?.timestamp ?? null,
      isFailure: type === "JOB_FAILED",
    };
  });
}

export default function JobTimeline({ events = [] }) {
  const steps = buildSteps(events);

  return (
    <ol className="space-y-0">
      {steps.map((step, index) => {
        const isLast = index === steps.length - 1;
        const toneClasses = !step.done
          ? "border-border-soft bg-slate-100 text-text-soft"
          : step.isFailure
          ? "border-red-200 bg-red-50 text-red-600"
          : "border-emerald-200 bg-emerald-50 text-emerald-600";
        const Icon = !step.done ? FiClock : step.isFailure ? FiXCircle : FiCheckCircle;

        return (
          <li key={step.type} className="flex gap-3">
            <div className="flex flex-col items-center">
              <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border ${toneClasses}`}>
                <Icon />
              </span>
              {!isLast && <span className={`w-px flex-1 ${step.done ? "bg-emerald-200" : "bg-border-soft"}`} />}
            </div>
            <div className={isLast ? "pb-0" : "pb-6"}>
              <p className={`pt-1.5 text-sm font-bold ${step.done ? "text-secondary" : "text-text-soft"}`}>
                {step.label}
              </p>
              <p className="text-[11px] text-text-soft">{step.done ? formatTimestamp(step.timestamp) : "Pendiente"}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
