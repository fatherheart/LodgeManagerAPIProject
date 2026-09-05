import { createFileRoute } from "@tanstack/react-router";
import { Link } from "@tanstack/react-router";
import { LoginForm } from "../../components/auth/login-form";

export const Route = createFileRoute("/(auth)/login")({
  component: LoginPage,
});

function LoginPage() {
  return (
    <div className="min-h-screen w-full flex bg-charcoal-50">
      <div className="hidden lg:flex lg:w-1/2 relative bg-charcoal-900 overflow-hidden">
        <img
          src="/imgs/building.webp"
          alt="Modern Architecture"
          className="absolute inset-0 w-full h-full object-cover opacity-60 mix-blend-luminosity"
        />
        <div className="absolute inset-0 bg-linear-to-t from-charcoal-950 via-charcoal-900/40 to-transparent" />

        <div className="relative z-10 flex flex-col justify-end p-16 w-full">
          <div className="h-1 bg-terracotta-400 w-12 mb-8" />
          <h2 className="font-serif text-5xl font-semibold text-white leading-tight mb-6">
            Elevating the standard of <br /> property management.
          </h2>
          <p className="text-charcoal-200 text-lg max-w-md font-sans">
            A structurally refined approach to managing luxury real estate
            portfolios, resident experiences, and financial clarity.
          </p>
        </div>
      </div>

      <div className="w-full lg:w-1/2 flex flex-col items-center justify-center p-8 sm:p-12 lg:p-24 bg-white relative">
        <div className="w-full max-w-sm">
          {" "}
          <div className="lg:hidden h-1 bg-terracotta-400 w-8 mb-8" />
          <div className="mb-10 text-left">
            <h1 className="font-serif text-3xl font-bold text-charcoal-900 mb-3 tracking-tight">
              LodgeOps
            </h1>
            <p className="text-charcoal-500 font-sans">
              Sign in to your administrative dashboard
            </p>
          </div>
          <div className="space-y-6">
            <LoginForm />
          </div>
          <div className="mt-8 text-center sm:text-left text-sm font-sans pt-8 border-t border-charcoal-100">
            <span className="text-charcoal-500">Already have an account?</span>
            <Link
              to="/register"
              className="ml-1 text-terracotta-500 font-medium hover:text-terracotta-600 transition-colors"
            >
              Log In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
