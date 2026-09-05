import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { LandlordSignUpForm } from "../../components/auth/landlord-signup-form";
import { TenantSignUpForm } from "../../components/auth/tenant-signup-form";

export const Route = createFileRoute("/(auth)/register")({
  component: RegisterPage,
});

function RegisterPage() {
  const [activeTab, setActiveTab] = useState<"landlord" | "tenant">("landlord");

  return (
    <div className="min-h-screen w-full flex bg-sand-50">
      <div className="hidden lg:flex lg:w-1/2 relative bg-sand-900 overflow-hidden">
        <img
          src="/imgs/building.webp"
          alt="Modern Architecture"
          className="absolute inset-0 w-full h-full object-cover opacity-60 mix-blend-luminosity"
        />
        <div className="absolute inset-0 bg-linear-to-t from-sand-950 via-sand-900/40 to-transparent" />

        <div className="relative z-10 flex flex-col justify-end p-16 w-full">
          <div className="h-1 bg-oxford-400 w-12 mb-8" />
          <h2 className="font-serif text-5xl font-semibold text-white leading-tight mb-6">
            Welcome to the future <br /> of property living.
          </h2>
          <p className="text-sand-200 text-lg max-w-md font-sans">
            Join a community that elevates property management and resident
            experiences to new heights of refinement.
          </p>
        </div>
      </div>

      <div className="w-full lg:w-1/2 flex flex-col items-center justify-center p-8 sm:p-12 lg:p-16 bg-white relative">
        <div className="w-full max-w-md py-8">
          <div className="lg:hidden h-1 bg-oxford-400 w-8 mb-8" />
          <div className="mb-8 text-left">
            <h1 className="font-serif text-3xl font-bold text-sand-900 mb-3 tracking-tight">
              LodgeOps
            </h1>
            <p className="text-sand-500 font-sans">Create a new account</p>
          </div>

          <div className="mb-6 flex space-x-1 rounded-lg bg-sand-50 p-1">
            <button
              onClick={() => setActiveTab("landlord")}
              className={`flex-1 rounded-md py-2 text-sm font-medium transition-all ${
                activeTab === "landlord"
                  ? "bg-white text-sand-900 shadow-sm"
                  : "text-sand-500 hover:text-sand-900"
              }`}
            >
              Landlord
            </button>
            <button
              onClick={() => setActiveTab("tenant")}
              className={`flex-1 rounded-md py-2 text-sm font-medium transition-all ${
                activeTab === "tenant"
                  ? "bg-white text-sand-900 shadow-sm"
                  : "text-sand-500 hover:text-sand-900"
              }`}
            >
              Tenant
            </button>
          </div>

          <div className="space-y-6">
            {activeTab === "landlord" ? (
              <LandlordSignUpForm />
            ) : (
              <TenantSignUpForm />
            )}
          </div>

          <div className="mt-8 text-center sm:text-left text-sm font-sans pt-8 border-t border-sand-100">
            <span className="text-sand-500">Already have an account? </span>
            <Link
              to="/login"
              className="text-oxford-500 font-medium hover:text-oxford-600 transition-colors"
            >
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
