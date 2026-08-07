"use client";

import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

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
  host: z.string().min(3, "Host is required."),
  description: z.string().max(240),
  tags: z.string(),
});

type AddServerValues = z.infer<typeof addServerSchema>;

export function AddServerDialog() {
  const [open, setOpen] = useState(false);
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
      host: "",
      description: "",
      tags: "",
    },
  });

  const onSubmit = (values: AddServerValues) => {
    toast.success(`${values.name} added`, {
      description: "Inventory record created for the current session.",
    });
    setOpen(false);
    reset();
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button />}>
        <Plus /> Add server
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Add server</DialogTitle>
          <DialogDescription>
            Add a local or cloud host to the infrastructure inventory.
          </DialogDescription>
        </DialogHeader>
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
            <div className="space-y-1.5">
              <Label htmlFor="server-provider">Provider</Label>
              <Input id="server-provider" {...register("provider")} />
              {errors.provider && (
                <p className="text-xs text-destructive">
                  {errors.provider.message}
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="server-host">Host</Label>
              <Input
                id="server-host"
                placeholder="server.internal"
                {...register("host")}
              />
              {errors.host && (
                <p className="text-xs text-destructive">{errors.host.message}</p>
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
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              Add server
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
