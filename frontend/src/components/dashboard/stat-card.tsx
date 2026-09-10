import { cn } from "../../lib/utils";

interface StatCardProps {
  title: string;
  value: string;
  trend?: string;
  trendUp?: boolean;
  className?: string;
}

export function StatCard({
  title,
  value,
  trend,
  trendUp,
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        "bg-white rounded-2xl border border-sand-200 p-6 flex flex-col gap-2 shadow-xs",
        className,
      )}
    >
      <p className="text-sm font-semibold text-sand-500 uppercase tracking-widest">
        {title}
      </p>
      <div className="flex items-end justify-between mt-2">
        <h3 className="text-3xl font-serif font-bold text-sand-900 tracking-tight">
          {value}
        </h3>
        {trend && (
          <span
            className={cn(
              "text-sm font-bold",
              trendUp ? "text-emerald-600" : "text-rose-600",
            )}
          >
            {trend}
          </span>
        )}
      </div>
    </div>
  );
}
