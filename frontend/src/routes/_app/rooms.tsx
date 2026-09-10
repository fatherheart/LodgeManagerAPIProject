import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Plus, Search } from "lucide-react";
import { Button } from "../../components/ui/button";
import {
  RoomCard,
  type RoomStatus,
} from "../../components/dashboard/room-card";
import { cn } from "../../lib/utils";

export const Route = createFileRoute("/_app/rooms")({
  component: RoomsPage,
});

// Mock Data
export const MOCK_ROOMS = [
  {
    id: "1",
    number: "101",
    tenantName: "Chinedu Okafor",
    status: "safe" as RoomStatus,
    leaseProgress: 30,
    daysLeft: 245,
  },
  {
    id: "2",
    number: "102",
    tenantName: "Aisha Bello",
    status: "warning" as RoomStatus,
    leaseProgress: 85,
    daysLeft: 20,
  },
  {
    id: "3",
    number: "103",
    tenantName: "Emeka Nwosu",
    status: "overdue" as RoomStatus,
    leaseProgress: 100,
    daysLeft: -5,
  },
  {
    id: "4",
    number: "104",
    tenantName: null,
    status: "vacant" as RoomStatus,
    leaseProgress: 0,
    daysLeft: null,
  },
  {
    id: "5",
    number: "201",
    tenantName: "Fatima Aliyu",
    status: "safe" as RoomStatus,
    leaseProgress: 45,
    daysLeft: 190,
  },
  {
    id: "6",
    number: "202",
    tenantName: "Tunde Bakare",
    status: "safe" as RoomStatus,
    leaseProgress: 10,
    daysLeft: 310,
  },
  {
    id: "7",
    number: "203",
    tenantName: "Ngozi Eze",
    status: "warning" as RoomStatus,
    leaseProgress: 90,
    daysLeft: 12,
  },
  {
    id: "8",
    number: "204",
    tenantName: null,
    status: "vacant" as RoomStatus,
    leaseProgress: 0,
    daysLeft: null,
  },
];

function RoomsPage() {
  const [filter, setFilter] = useState<RoomStatus | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");

  const filteredRooms = MOCK_ROOMS.filter((r) => {
    const matchesFilter = filter === "all" || r.status === filter;
    const matchesSearch =
      r.number.includes(searchQuery) ||
      (r.tenantName &&
        r.tenantName.toLowerCase().includes(searchQuery.toLowerCase()));

    return matchesFilter && matchesSearch;
  });

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-10">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-6 px-1">
        <div>
          <h1 className="text-3xl sm:text-4xl font-serif font-bold text-sand-900 tracking-tight mb-2">
            Rooms & Tenants
          </h1>
          <p className="text-sand-500 font-medium">
            Manage your property units and view lease statuses.
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

      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-sand-200 pb-4 px-1">
          <div className="flex items-center gap-2 overflow-x-auto scrollbar-none pb-1">
            {(["all", "safe", "warning", "overdue", "vacant"] as const).map(
              (status) => (
                <button
                  key={status}
                  onClick={() => setFilter(status)}
                  className={cn(
                    "px-4 py-2 rounded-lg text-sm font-semibold capitalize transition-all duration-200 whitespace-nowrap",
                    filter === status
                      ? "bg-oxford-600 text-white shadow-xs"
                      : "text-sand-500 hover:text-sand-900 hover:bg-sand-100",
                  )}
                >
                  {status}
                </button>
              ),
            )}
          </div>

          {/* Search Box */}
          <div className="relative shrink-0 w-full md:w-64">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-sand-400" />
            </div>
            <input
              type="text"
              placeholder="Search by room or tenant..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="block w-full pl-10 pr-3 py-2 border border-sand-200 rounded-lg bg-white placeholder-sand-400 focus:outline-none focus:ring-1 focus:ring-sand-900 focus:border-sand-900 sm:text-sm"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredRooms.length > 0 ? (
            filteredRooms.map((room) => (
              <RoomCard
                key={room.id}
                number={room.number}
                tenantName={room.tenantName}
                status={room.status}
                leaseProgress={room.leaseProgress}
                daysLeft={room.daysLeft}
              />
            ))
          ) : (
            <div className="col-span-full py-12 text-center text-sand-500 bg-sand-50 border border-sand-100 rounded-2xl">
              No rooms found matching your search or filter.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
