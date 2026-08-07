"use client";

import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Check, Copy, Loader2, Plus } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { useCreateRegistration } from "@/hooks/use-infrastructure";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

const addServerSchema = z.object({
  name: z.string().min(3, "Use at least 3 characters."),
  type: z.enum(["local", "cloud"]),
  provider: z.string().min(2, "Provider is required."),
  description: z.string().max(240),
  tags: z.string(),
});

type AddServerValues = z.infer<typeof addServerSchema>;

export function AddServerDialog() {
  const [open, setOpen] = useState(false);
  const [registrationToken, setRegistrationToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const createRegistration = useCreateRegistration();
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<AddServerValues>({
    resolver: zodResolver(addServerSchema),
    defaultValues: {
      name: "",
      type: "local",
      provider: "On-premise",
      description: "",
      tags: "",
    },
  });

  const close = () => {
    setOpen(false);
    setRegistrationToken(null);
    setCopied(false);
    createRegistration.reset();
    reset();
  };

  const onSubmit = async (values: AddServerValues) => {
    try {
      const result = await createRegistration.mutateAsync({
        name: values.name,
        type: values.type,
        provider: values.provider,
        description: values.description || undefined,
        tags: values.tags
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean),
      });
      setRegistrationToken(result.registration_token);
      toast.success(`${values.name} registration created`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Registration failed.");
    }
  };

  const copyToken = async () => {
    if (!registrationToken) return;
    await navigator.clipboard.writeText(registrationToken);
    setCopied(true);
    toast.success("Registration token copied");
  };

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? setOpen(true) : close())}>
      <DialogTrigger render={<Button />}>
        <Plus /> Add server
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {registrationToken ? "Agent registration created" : "Add server"}
          </DialogTitle>
          <DialogDescription>
            {registrationToken
              ? "Copy this token now. It is not stored in plaintext and cannot be shown again."
              : "Create a local or cloud inventory record and its first Agent token."}
          </DialogDescription>
        </DialogHeader>

        {registrationToken ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Input
                value={registrationToken}
                readOnly
                className="font-mono text-xs"
                aria-label="Registration token"
              />
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={copyToken}
                aria-label="Copy registration token"
              >
                {copied ? <Check /> : <Copy />}
              </Button>
            </div>
            <DialogFooter>
              <Button type="button" onClick={close}>
                Done
              </Button>
            </DialogFooter>
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="server-name">Name</Label>
                <Input
                  id="server-name"
                  placeholder="lab-server-01"
                  {...register("name")}
                />
                {errors.name && (
                  <p className="text-xs text-destructive">{errors.name.message}</p>
                )}
              </div>
              <div className="space-y-1.5">
                <Label>Type</Label>
                <Controller
                  control={control}
                  name="type"
                  render={({ field }) => (
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="local">Local</SelectItem>
                        <SelectItem value="cloud">Cloud</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="server-provider">Provider</Label>
                <Input id="server-provider" {...register("provider")} />
                {errors.provider && (
                  <p className="text-xs text-destructive">
                    {errors.provider.message}
                  </p>
                )}
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="server-description">Description</Label>
              <Textarea
                id="server-description"
                rows={3}
                placeholder="Primary purpose and ownership notes"
                {...register("description")}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="server-tags">Tags</Label>
              <Input
                id="server-tags"
                placeholder="inference, shared, cuda-12"
                {...register("tags")}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={close}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="animate-spin" />}
                Create registration
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
