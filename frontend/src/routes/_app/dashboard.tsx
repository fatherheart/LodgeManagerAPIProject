import { createFileRoute } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import { Button } from "../../components/ui/button";
import { StatCard } from "../../components/dashboard/stat-card";
import { RoomCard } from "../../components/dashboard/room-card";
import { MOCK_ROOMS } from "./rooms";

export const Route = createFileRoute("/_app/dashboard")({
  component: DashboardPage,
});

function DashboardPage() {
  const actionNeededRooms = MOCK_ROOMS.filter(
    (r) => r.status === "warning" || r.status === "overdue",
  );

  return (
    <div className="space-y-10 max-w-7xl mx-auto pb-10">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-6">
        <div>
          <h1 className="text-3xl sm:text-4xl font-serif font-bold text-sand-900 tracking-tight mb-2">
            Property Overview
          </h1>
          <p className="text-sand-500 font-medium">
            Real-time metrics and lease health for your UNIZIK lodge.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            onClick={() => console.log("Add room")}
            className="gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Room
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Revenue"
          value="₦4.2m"
          trend="+12%"
          trendUp={true}
        />
        <StatCard title="Occupancy" value="85%" />
        <StatCard
          title="Pending Payments"
          value="₦450k"
          trend="2 Overdue"
          trendUp={false}
        />
        <StatCard title="Vacant Rooms" value="3" />
      </div>

      <div className="space-y-6 pt-6">
        <div className="flex items-center justify-between border-b border-sand-200 pb-4">
          <h2 className="text-xl font-serif font-bold text-sand-900">
            Action Needed
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
          {actionNeededRooms.map((room) => (
            <RoomCard
              key={room.id}
              number={room.number}
              tenantName={room.tenantName}
              status={room.status}
              leaseProgress={room.leaseProgress}
              daysLeft={room.daysLeft}
            />
          ))}
          {actionNeededRooms.length === 0 && (
            <div className="col-span-full py-8 text-center text-sand-500 bg-sand-50 border border-sand-100 rounded-2xl">
              All leases are up to date. No immediate action required.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
