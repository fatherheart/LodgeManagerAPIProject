import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { useNavigate } from "@tanstack/react-router";
import { login, registerLandlord, registerTenant } from "../services/auth-service";
import { processErrorMessage } from "../lib/utils";

export const useLogin = () => {
  const navigate = useNavigate();

  return useMutation({
    mutationFn: login,
    onSuccess: (data) => {
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      toast.success("Successfully logged in");
      navigate({ to: "/dashboard" });
    },
    onError: (error) => {
      toast.error(
        processErrorMessage(error, "Failed to login. Please try again."),
      );
    },
  });
};

export const useLandlordSignUp = () => {
  const navigate = useNavigate();

  return useMutation({
    mutationFn: registerLandlord,
    onSuccess: () => {
      toast.success("Account created successfully. Please log in.");
      navigate({ to: "/login" });
    },
    onError: (error) => {
      toast.error(
        processErrorMessage(error, "Failed to create account. Please try again."),
      );
    },
  });
};

export const useTenantSignUp = () => {
  const navigate = useNavigate();

  return useMutation({
    mutationFn: registerTenant,
    onSuccess: () => {
      toast.success("Account created successfully. Please log in.");
      navigate({ to: "/login" });
    },
    onError: (error) => {
      toast.error(
        processErrorMessage(error, "Failed to create account. Please try again."),
      );
    },
  });
};
