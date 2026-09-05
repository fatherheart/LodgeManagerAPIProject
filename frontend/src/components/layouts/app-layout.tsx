import { useState } from "react";
import { Outlet } from "@tanstack/react-router";
import Sidebar from "./sidebar";
import Header from "./header";

export default function AppLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-sand-50 text-sand-900 font-sans">
      <div className="flex h-screen overflow-hidden relative">
        <Sidebar
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
        />

        <div className="flex-1 flex flex-col min-w-0">
          <Header onMenuClick={() => setIsSidebarOpen(true)} />
          <main className="p-4 sm:p-6 md:p-10 flex-1 overflow-y-auto">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
