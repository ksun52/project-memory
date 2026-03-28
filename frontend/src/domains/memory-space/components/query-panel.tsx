"use client";

import { useState, useRef, useEffect } from "react";
import Markdown from "react-markdown";
import { Brain, Send, FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useMemorySpaceQuery } from "../hooks";
import type { Citation } from "../types";

interface QueryPanelProps {
  memorySpaceId: string;
}

interface QAEntry {
  question: string;
  answer: string;
  citations: Citation[];
}

const SUGGESTIONS = [
  "What are the key decisions?",
  "Summarize the recent updates",
  "What are the open risks?",
];

const markdownComponents = {
  h1: ({ children, ...props }: React.ComponentProps<"h1">) => (
    <h1 className="text-xl font-bold mt-4 mb-2" {...props}>{children}</h1>
  ),
  h2: ({ children, ...props }: React.ComponentProps<"h2">) => (
    <h2 className="text-lg font-semibold mt-3 mb-1.5" {...props}>{children}</h2>
  ),
  h3: ({ children, ...props }: React.ComponentProps<"h3">) => (
    <h3 className="text-base font-semibold mt-2 mb-1" {...props}>{children}</h3>
  ),
  p: ({ children, ...props }: React.ComponentProps<"p">) => (
    <p className="mb-2 leading-relaxed" {...props}>{children}</p>
  ),
  ul: ({ children, ...props }: React.ComponentProps<"ul">) => (
    <ul className="list-disc pl-5 mb-2 space-y-0.5" {...props}>{children}</ul>
  ),
  ol: ({ children, ...props }: React.ComponentProps<"ol">) => (
    <ol className="list-decimal pl-5 mb-2 space-y-0.5" {...props}>{children}</ol>
  ),
  li: ({ children, ...props }: React.ComponentProps<"li">) => (
    <li className="leading-relaxed" {...props}>{children}</li>
  ),
  strong: ({ children, ...props }: React.ComponentProps<"strong">) => (
    <strong className="font-semibold" {...props}>{children}</strong>
  ),
};

function CitationList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;

  return (
    <div className="mt-3">
      <p className="text-xs font-medium text-muted-foreground mb-1.5">
        Sources ({citations.length})
      </p>
      <div className="flex flex-col gap-1.5">
        {citations.map((citation, i) => (
          <div
            key={i}
            className="flex items-start gap-2 rounded-md border px-3 py-2 text-xs"
          >
            <FileText className="h-3.5 w-3.5 mt-0.5 shrink-0 text-muted-foreground" />
            <span className="text-muted-foreground line-clamp-2">
              {citation.excerpt}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function QueryPanel({ memorySpaceId }: QueryPanelProps) {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<QAEntry[]>([]);
  const queryMutation = useMemorySpaceQuery();
  const historyEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when history updates
  useEffect(() => {
    historyEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, queryMutation.isPending]);

  function submit(q: string) {
    const trimmed = q.trim();
    if (!trimmed || queryMutation.isPending) return;

    setQuestion("");
    queryMutation.mutate(
      { id: memorySpaceId, data: { question: trimmed } },
      {
        onSuccess: (data) => {
          setHistory((prev) => [
            ...prev,
            { question: trimmed, answer: data.answer, citations: data.citations },
          ]);
        },
      }
    );
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(question);
    }
  }

  const showEmptyState = history.length === 0 && !queryMutation.isPending;

  return (
    <div className="flex flex-col h-[600px]">
      {/* Scrollable Q&A area */}
      <div className="flex-1 overflow-y-auto space-y-6 pb-4">
        {showEmptyState && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Brain className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold">
              Ask a question about this memory space
            </h3>
            <p className="text-sm text-muted-foreground mt-1 max-w-sm">
              Get answers based on the sources and records stored here.
            </p>
            <div className="flex flex-wrap justify-center gap-2 mt-6">
              {SUGGESTIONS.map((s) => (
                <Button
                  key={s}
                  variant="outline"
                  size="sm"
                  onClick={() => submit(s)}
                >
                  {s}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* History entries */}
        {history.map((entry, i) => (
          <div key={i} className="space-y-3">
            {/* User question */}
            <div className="flex justify-end">
              <div className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground max-w-[80%]">
                {entry.question}
              </div>
            </div>
            {/* Answer */}
            <div className="rounded-lg border bg-muted/40 px-4 py-3 text-sm">
              <Markdown components={markdownComponents}>
                {entry.answer}
              </Markdown>
              <CitationList citations={entry.citations} />
            </div>
          </div>
        ))}

        {/* Loading indicator for pending query */}
        {queryMutation.isPending && (
          <div className="space-y-3">
            <div className="flex justify-end">
              <div className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground max-w-[80%]">
                {queryMutation.variables?.data.question}
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground px-4 py-3">
              <Loader2 className="h-4 w-4 animate-spin" />
              Thinking...
            </div>
          </div>
        )}

        <div ref={historyEndRef} />
      </div>

      {/* Input area */}
      <div className="flex items-center gap-2 border-t pt-4">
        <Input
          placeholder="Ask a question..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={queryMutation.isPending}
        />
        <Button
          size="icon"
          onClick={() => submit(question)}
          disabled={!question.trim() || queryMutation.isPending}
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
