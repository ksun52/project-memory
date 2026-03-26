"use client";

import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { useUpdateRecord } from "../hooks";
import type { MemoryRecord, RecordStatus, RecordImportance } from "../types";

const STATUSES: RecordStatus[] = ["active", "tentative", "outdated", "archived"];
const IMPORTANCES: RecordImportance[] = ["low", "medium", "high"];

const schema = z.object({
  content: z.string().min(1, "Content is required"),
  status: z.enum(["active", "tentative", "outdated", "archived"]),
  importance: z.enum(["low", "medium", "high"]),
});

type FormValues = z.infer<typeof schema>;

interface RecordEditDialogProps {
  record: MemoryRecord | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RecordEditDialog({
  record,
  open,
  onOpenChange,
}: RecordEditDialogProps) {
  const updateMutation = useUpdateRecord();
  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { content: "", status: "active", importance: "medium" },
  });

  useEffect(() => {
    if (record && open) {
      reset({
        content: record.content,
        status: record.status,
        importance: record.importance,
      });
    }
  }, [record, open, reset]);

  function onSubmit(values: FormValues) {
    if (!record) return;
    updateMutation.mutate(
      { id: record.id, data: values },
      {
        onSuccess: () => {
          onOpenChange(false);
        },
      }
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Record</DialogTitle>
          <DialogDescription>
            Update this memory record&apos;s content, status, or importance.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="edit-content">Content</Label>
            <Textarea
              id="edit-content"
              rows={4}
              {...register("content")}
            />
            {errors.content && (
              <p className="text-sm text-destructive">{errors.content.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label>Status</Label>
            <Controller
              control={control}
              name="status"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STATUSES.map((s) => (
                      <SelectItem key={s} value={s}>
                        {s.charAt(0).toUpperCase() + s.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </div>

          <div className="space-y-2">
            <Label>Importance</Label>
            <Controller
              control={control}
              name="importance"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {IMPORTANCES.map((i) => (
                      <SelectItem key={i} value={i}>
                        {i.charAt(0).toUpperCase() + i.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
