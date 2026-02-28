"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Info, Save } from "lucide-react";
import Link from "next/link";
import { getInstructions, updateInstructions } from "@/lib/api";

type SaveStatus = "idle" | "saving" | "success" | "error";

export default function InstructionsPage() {
  const [content, setContent] = useState("");
  const [filePath, setFilePath] = useState("");
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    getInstructions()
      .then((data) => {
        setContent(data.content);
        setFilePath(data.path);
      })
      .catch((err: unknown) => {
        setFetchError(err instanceof Error ? err.message : "Failed to load instructions");
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaveStatus("saving");
    setSaveError(null);
    try {
      await updateInstructions(content);
      setSaveStatus("success");
      setTimeout(() => setSaveStatus("idle"), 3000);
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "Failed to save");
      setSaveStatus("error");
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/" className="text-muted hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <h1 className="text-lg font-semibold text-foreground">Instructions</h1>
      </div>

      {/* Info banner */}
      <div className="mt-4 flex items-start gap-2 rounded-lg border border-border bg-card px-4 py-3">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted" />
        <div className="text-xs text-muted">
          <span className="font-medium text-foreground">Server restart required</span> — changes
          take effect after restarting the Muninn MCP server.
          {filePath && (
            <span className="ml-1">
              File: <code className="font-mono text-foreground">{filePath}</code>
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="mt-5">
        {loading && (
          <div className="text-center text-xs text-muted">Loading...</div>
        )}

        {fetchError && (
          <div className="rounded-lg border border-red-900/50 bg-red-950/20 px-4 py-3 text-xs text-red-400">
            {fetchError}
          </div>
        )}

        {!loading && !fetchError && (
          <>
            <textarea
              value={content}
              onChange={(e) => {
                setContent(e.target.value);
                if (saveStatus === "success" || saveStatus === "error") {
                  setSaveStatus("idle");
                  setSaveError(null);
                }
              }}
              className="h-[calc(100vh-280px)] min-h-64 w-full resize-none rounded-lg border border-border bg-card px-4 py-3 font-mono text-sm text-foreground outline-none placeholder:text-muted focus:border-border-hover"
              placeholder="Write your MCP server instructions here..."
              spellCheck={false}
            />

            {/* Footer bar */}
            <div className="mt-3 flex items-center justify-between">
              {/* Save feedback */}
              <div className="text-xs">
                {saveStatus === "success" && (
                  <span className="text-status-active">Saved successfully</span>
                )}
                {saveStatus === "error" && saveError && (
                  <span className="text-red-400">{saveError}</span>
                )}
              </div>

              {/* Save button */}
              <button
                type="button"
                onClick={handleSave}
                disabled={saveStatus === "saving"}
                className="flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
              >
                <Save className="h-3.5 w-3.5" />
                {saveStatus === "saving" ? "Saving..." : "Save"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
