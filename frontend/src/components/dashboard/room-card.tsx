import { cn } from "../../lib/utils";

export type RoomStatus = "safe" | "warning" | "overdue" | "vacant";

interface RoomCardProps {
  number: string;
  tenantName: string | null;
  status: RoomStatus;
  leaseProgress: number; // 0-100
  daysLeft: number | null;
  onClick?: () => void;
}

const statusStyles: Record<
  RoomStatus,
  { badge: string; progress: string; label: string }
> = {
  safe: {
    badge: "bg-emerald-50 text-emerald-700 border-emerald-200",
    progress: "bg-emerald-500",
    label: "Safe",
  },
  warning: {
    badge: "bg-amber-50 text-amber-700 border-amber-200",
    progress: "bg-amber-500",
    label: "Expiring",
  },
  overdue: {
    badge: "bg-rose-50 text-rose-700 border-rose-200",
    progress: "bg-rose-600",
    label: "Overdue",
  },
  vacant: {
    badge: "bg-sand-50 text-sand-600 border-sand-200",
    progress: "bg-sand-200",
    label: "Vacant",
  },
};

export function RoomCard({
  number,
  tenantName,
  status,
  leaseProgress,
  daysLeft,
  onClick,
}: RoomCardProps) {
  const styles = statusStyles[status];

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-2xl border border-sand-200 p-6 flex flex-col gap-4 shadow-xs hover:shadow-md hover:border-sand-300 transition-all duration-200 cursor-pointer group"
    >
      <div className="flex justify-between items-center">
        <h3 className="text-2xl font-serif font-bold text-sand-900 group-hover:text-oxford-500 transition-colors">
          {number}
        </h3>
        <span
          className={cn(
            "px-2.5 py-1 text-[10px] font-extrabold rounded-md border uppercase tracking-wider",
            styles.badge,
          )}
        >
          {styles.label}
        </span>
      </div>

      <div className="flex-1 mt-2">
        <p className="text-sm font-semibold text-sand-600">
          {status === "vacant" ? "Available for lease" : tenantName}
        </p>
      </div>

      <div className="space-y-2 mt-4 pt-4 border-t border-sand-100">
        <div className="flex justify-between items-center text-xs font-bold uppercase tracking-wider">
          <span className="text-sand-400">Lease</span>
          <span
            className={
              status === "overdue" ? "text-rose-600" : "text-sand-900"
            }
          >
            {status === "vacant" ? "--" : `${daysLeft} days left`}
          </span>
        </div>
        <div className="w-full bg-sand-100 rounded-full h-1.5 overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              styles.progress,
            )}
            style={{ width: `${Math.min(Math.max(leaseProgress, 0), 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
