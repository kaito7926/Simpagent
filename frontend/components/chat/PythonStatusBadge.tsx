import { StatusBadge } from "@/components/account-access/StatusBadge";
import { pythonStatusLabel, pythonToneForStatus, type PythonExecutionStatus } from "@/lib/chat/tool-copy";

type PythonStatusBadgeProps = {
  status: PythonExecutionStatus;
};

export function PythonStatusBadge({ status }: PythonStatusBadgeProps) {
  return (
    <StatusBadge tone={pythonToneForStatus(status)}>
      {pythonStatusLabel(status)}
    </StatusBadge>
  );
}
