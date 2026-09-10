import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "../ui/form";
import { Input } from "../ui/input";
import { Button } from "../ui/button";
import { loginSchema, type LoginFormData } from "../../lib/form-schemas";
import { useLogin } from "../../hooks/auth";

export function LoginForm() {
  const { mutate, isPending } = useLogin();

  const form = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const onSubmit = (data: LoginFormData) => {
    mutate(data);
  };

  return (
    <Form form={form} onSubmit={form.handleSubmit(onSubmit)}>
      <div className="space-y-5">
        <FormField
          name="email"
          render={({ field, fieldState }) => (
            <FormItem>
              <FormLabel>Email Address</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  type="email"
                  placeholder="your@email.com"
                  autoComplete="email"
                />
              </FormControl>
              <FormMessage error={fieldState.error?.message} />
            </FormItem>
          )}
        />

        <FormField
          name="password"
          render={({ field, fieldState }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  type="password"
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
              </FormControl>
              <FormMessage error={fieldState.error?.message} />
            </FormItem>
          )}
        />

        <Button
          type="submit"
          className="w-full"
          isLoading={isPending}
          disabled={isPending}
        >
          Log In
        </Button>
      </div>
    </Form>
  );
}
