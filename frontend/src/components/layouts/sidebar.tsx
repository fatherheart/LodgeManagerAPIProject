import { Link } from "@tanstack/react-router";
import {
  Home,
  Building,
  Users,
  CreditCard,
  Settings,
  LogOut,
  X,
} from "lucide-react";
import { cn } from "../../lib/utils";

const navItems = [
  { to: "/dashboard", label: "Dashboard", Icon: Home },
  { to: "/rooms", label: "Rooms", Icon: Building },
  { to: "/tenants", label: "Tenants", Icon: Users },
  { to: "/payments", label: "Payments", Icon: CreditCard },
  { to: "/settings", label: "Settings", Icon: Settings },
];

export function Sidebar({
  isOpen,
  onClose,
}: {
  isOpen?: boolean;
  onClose?: () => void;
}) {
  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-charcoal-900/60 lg:hidden backdrop-blur-sm transition-opacity"
          onClick={onClose}
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-72 bg-white border-r border-charcoal-200 p-6 flex flex-col justify-between shrink-0 transition-transform duration-300 ease-in-out lg:static lg:translate-x-0 h-full",
          isOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full",
        )}
      >
        <div>
          <div className="flex items-center justify-between mb-10">
            <h2 className="text-2xl font-serif font-bold text-charcoal-900 tracking-tight">
              LodgeManager
            </h2>
            <button
              onClick={onClose}
              className="lg:hidden p-2 -mr-2 text-charcoal-400 hover:text-charcoal-900 hover:bg-charcoal-50 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <nav className="space-y-1.5">
            {navItems.map(({ to, label, Icon }) => (
              <Link
                key={to}
                to={to}
                className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 inactive text-charcoal-500 hover:bg-charcoal-50 hover:text-charcoal-900"
                activeProps={{ className: "bg-charcoal-900 text-white shadow-xs !text-white" }}
              >
                <Icon className="w-5 h-5" />
                <span>{label}</span>
              </Link>
            ))}
          </nav>
        </div>

        <div>
          <button
            type="button"
            onClick={() => console.log("sign out")}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-charcoal-500 hover:text-rose-600 hover:bg-rose-50 transition-all duration-200"
          >
            <LogOut className="w-5 h-5" />
            Sign out
          </button>
        </div>
      </aside>
    </>
  );
}

export default Sidebar;
