import * as React from "react";
import {
  Controller,
  type ControllerRenderProps,
  type ControllerFieldState,
  type FieldPath,
  type FieldValues,
  type UseFormReturn,
  FormProvider,
  useFormContext,
} from "react-hook-form";
import { cn } from "../../lib/utils";
import { AlertCircle } from "lucide-react";
import {
  FormFieldContext,
  FormItemContext,
  useFormField,
} from "../../hooks/useFormField";

type FormProps<TFieldValues extends FieldValues = FieldValues> =
  React.FormHTMLAttributes<HTMLFormElement> & {
    form: UseFormReturn<TFieldValues>;
  };

// eslint-disable-next-line
const Form = React.forwardRef<HTMLFormElement, FormProps<any>>(
  ({ form, className, children, ...props }, ref) => (
    <FormProvider {...form}>
      <form ref={ref} className={cn("space-y-6", className)} {...props}>
        {children}
      </form>
    </FormProvider>
  ),
);

Form.displayName = "Form";

type FormFieldProps<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
> = {
  name: TName;
  render: (props: {
    field: ControllerRenderProps<TFieldValues, TName>;
    fieldState: ControllerFieldState;
    form: UseFormReturn<TFieldValues>;
  }) => React.ReactElement;
};

const FormField = <
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>,
>({
  name,
  render,
}: FormFieldProps<TFieldValues, TName>) => {
  const form = useFormContext<TFieldValues>();

  return (
    <FormFieldContext.Provider value={{ name }}>
      <Controller
        name={name}
        control={form.control}
        render={({ field, fieldState }) =>
          render({
            field,
            fieldState,
            form,
          })
        }
      />
    </FormFieldContext.Provider>
  );
};

const FormItem = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => {
  const id = React.useId();

  return (
    <FormItemContext.Provider value={{ id }}>
      <div ref={ref} className={cn("space-y-2", className)} {...props} />
    </FormItemContext.Provider>
  );
});

FormItem.displayName = "FormItem";

const FormLabel = React.forwardRef<
  React.ComponentRef<"label">,
  React.LabelHTMLAttributes<HTMLLabelElement>
>(({ className, ...props }, ref) => {
  const { formItemId } = useFormField();

  return (
    <label
      ref={ref}
      htmlFor={formItemId}
      className={cn("block text-sm font-semibold text-sand-900", className)}
      {...props}
    />
  );
});

FormLabel.displayName = "FormLabel";

const FormControl = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ ...props }, ref) => {
  const { formItemId, formDescriptionId, formMessageId } = useFormField();

  return (
    <div
      ref={ref}
      data-testid={formItemId}
      aria-describedby={
        formDescriptionId && formMessageId
          ? `${formDescriptionId} ${formMessageId}`
          : formMessageId
      }
      {...props}
    />
  );
});

FormControl.displayName = "FormControl";

const FormDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => {
  const { formDescriptionId } = useFormField();

  return (
    <p
      ref={ref}
      id={formDescriptionId}
      className={cn("text-xs text-sand-400", className)}
      {...props}
    />
  );
});

FormDescription.displayName = "FormDescription";

const FormMessage = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement> & {
    error?: string;
  }
>(({ className, error, ...props }, ref) => {
  const { formMessageId } = useFormField();

  if (!error) {
    return null;
  }

  return (
    <p
      ref={ref}
      id={formMessageId}
      className={cn(
        "flex items-center gap-1.5 text-xs font-medium text-rose-600",
        className,
      )}
      {...props}
    >
      <AlertCircle className="h-3 w-3 shrink-0" />
      {error}
    </p>
  );
});

FormMessage.displayName = "FormMessage";

export {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
};
