"use client";

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
import { useCreateRecord } from "../hooks";
import type { RecordType, RecordImportance } from "../types";

const RECORD_TYPES: RecordType[] = [
  "fact", "event", "decision", "issue", "question", "preference", "task", "insight",
];

const IMPORTANCES: RecordImportance[] = ["low", "medium", "high"];

const schema = z.object({
  record_type: z.enum(["fact", "event", "decision", "issue", "question", "preference", "task", "insight"]),
  content: z.string().min(1, "Content is required"),
  importance: z.enum(["low", "medium", "high"]),
});

type FormValues = z.infer<typeof schema>;

interface RecordCreateDialogProps {
  memorySpaceId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RecordCreateDialog({
  memorySpaceId,
  open,
  onOpenChange,
}: RecordCreateDialogProps) {
  const createMutation = useCreateRecord();
  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { record_type: "fact", content: "", importance: "medium" },
  });

  function onSubmit(values: FormValues) {
    createMutation.mutate(
      { memorySpaceId, data: values },
      {
        onSuccess: () => {
          reset();
          onOpenChange(false);
        },
      }
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Record</DialogTitle>
          <DialogDescription>
            Manually add a memory record to this space.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label>Type</Label>
            <Controller
              control={control}
              name="record_type"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {RECORD_TYPES.map((t) => (
                      <SelectItem key={t} value={t}>
                        {t.charAt(0).toUpperCase() + t.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.record_type && (
              <p className="text-sm text-destructive">{errors.record_type.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="record-content">Content</Label>
            <Textarea
              id="record-content"
              placeholder="Enter the memory record content..."
              rows={4}
              {...register("content")}
            />
            {errors.content && (
              <p className="text-sm text-destructive">{errors.content.message}</p>
            )}
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
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Creating..." : "Create Record"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
