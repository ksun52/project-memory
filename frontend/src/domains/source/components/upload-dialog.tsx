"use client";

import { useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useDropzone } from "react-dropzone";
import { Upload, X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCreateNoteSource, useUploadDocumentSource } from "../hooks";

const noteSchema = z.object({
  title: z.string().min(1, "Title is required"),
  content: z.string().min(1, "Content is required"),
});

type NoteFormValues = z.infer<typeof noteSchema>;

const docSchema = z.object({
  title: z.string().min(1, "Title is required"),
});

type DocFormValues = z.infer<typeof docSchema>;

interface UploadDialogProps {
  memorySpaceId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSourceCreated?: () => void;
}

export function UploadDialog({
  memorySpaceId,
  open,
  onOpenChange,
  onSourceCreated,
}: UploadDialogProps) {
  const [activeTab, setActiveTab] = useState<string>("note");

  const createNote = useCreateNoteSource();
  const uploadDoc = useUploadDocumentSource();

  const noteForm = useForm<NoteFormValues>({
    resolver: zodResolver(noteSchema),
    defaultValues: { title: "", content: "" },
  });

  const docForm = useForm<DocFormValues>({
    resolver: zodResolver(docSchema),
    defaultValues: { title: "" },
  });

  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setFileError(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxFiles: 1,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
    },
  });

  function handleClose() {
    noteForm.reset();
    docForm.reset();
    setFile(null);
    setFileError(null);
    setActiveTab("note");
    onOpenChange(false);
  }

  function onNoteSubmit(values: NoteFormValues) {
    createNote.mutate(
      {
        memorySpaceId,
        data: { source_type: "note", title: values.title, content: values.content },
      },
      {
        onSuccess: () => {
          onSourceCreated?.();
          handleClose();
        },
      }
    );
  }

  function onDocSubmit(values: DocFormValues) {
    if (!file) {
      setFileError("Please select a file");
      return;
    }

    uploadDoc.mutate(
      {
        memorySpaceId,
        data: { title: values.title, file },
      },
      {
        onSuccess: () => {
          onSourceCreated?.();
          handleClose();
        },
      }
    );
  }

  const isPending = createNote.isPending || uploadDoc.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add Source</DialogTitle>
          <DialogDescription>
            Add a note or upload a document to this memory space.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="w-full">
            <TabsTrigger value="note">Quick Note</TabsTrigger>
            <TabsTrigger value="document">Upload Document</TabsTrigger>
          </TabsList>

          <TabsContent value="note">
            <form onSubmit={noteForm.handleSubmit(onNoteSubmit)} className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="note-title">Title</Label>
                <Input
                  id="note-title"
                  placeholder="e.g. Meeting notes from kickoff"
                  {...noteForm.register("title")}
                />
                {noteForm.formState.errors.title && (
                  <p className="text-sm text-destructive">
                    {noteForm.formState.errors.title.message}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="note-content">Content</Label>
                <Textarea
                  id="note-content"
                  placeholder="Paste or type your notes here..."
                  rows={6}
                  {...noteForm.register("content")}
                />
                {noteForm.formState.errors.content && (
                  <p className="text-sm text-destructive">
                    {noteForm.formState.errors.content.message}
                  </p>
                )}
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={handleClose}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isPending}>
                  {createNote.isPending ? "Creating..." : "Create Note"}
                </Button>
              </DialogFooter>
            </form>
          </TabsContent>

          <TabsContent value="document">
            <form onSubmit={docForm.handleSubmit(onDocSubmit)} className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="doc-title">Title</Label>
                <Input
                  id="doc-title"
                  placeholder="e.g. Project charter v2"
                  {...docForm.register("title")}
                />
                {docForm.formState.errors.title && (
                  <p className="text-sm text-destructive">
                    {docForm.formState.errors.title.message}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label>File</Label>
                <div
                  {...getRootProps()}
                  className={`
                    border-2 border-dashed rounded-lg p-6 text-center cursor-pointer
                    transition-colors
                    ${isDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-muted-foreground/50"}
                  `}
                >
                  <input {...getInputProps()} />
                  {file ? (
                    <div className="flex items-center justify-center gap-2">
                      <span className="text-sm font-medium truncate">{file.name}</span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setFile(null);
                        }}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-2 text-muted-foreground">
                      <Upload className="h-8 w-8" />
                      <p className="text-sm">
                        Drag & drop a file here, or click to browse
                      </p>
                      <p className="text-xs">PDF, DOCX, or TXT</p>
                    </div>
                  )}
                </div>
                {fileError && (
                  <p className="text-sm text-destructive">{fileError}</p>
                )}
              </div>

              <DialogFooter>
                <Button type="button" variant="outline" onClick={handleClose}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isPending}>
                  {uploadDoc.isPending ? "Uploading..." : "Upload Document"}
                </Button>
              </DialogFooter>
            </form>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
