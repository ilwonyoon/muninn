"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, CheckCircle, XCircle } from "lucide-react";
import Link from "next/link";

export default function SettingsPage() {
  const [apiStatus, setApiStatus] = useState<"checking" | "ok" | "error">(
    "checking"
  );

  useEffect(() => {
    fetch("/api/stats")
      .then((res) => {
        setApiStatus(res.ok ? "ok" : "error");
      })
      .catch(() => setApiStatus("error"));
  }, []);

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <div className="flex items-center gap-3">
        <Link href="/" className="text-muted hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <h1 className="text-lg font-semibold text-foreground">Settings</h1>
      </div>

      <div className="mt-6 space-y-6">
        {/* Connection status */}
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-medium text-foreground">
            API Connection
          </h2>
          <div className="mt-2 flex items-center gap-2 text-xs">
            {apiStatus === "checking" && (
              <span className="text-muted">Checking...</span>
            )}
            {apiStatus === "ok" && (
              <>
                <CheckCircle className="h-3.5 w-3.5 text-status-active" />
                <span className="text-status-active">Connected</span>
              </>
            )}
            {apiStatus === "error" && (
              <>
                <XCircle className="h-3.5 w-3.5 text-red-400" />
                <span className="text-red-400">Not connected</span>
              </>
            )}
          </div>
          <p className="mt-2 text-[10px] text-muted">
            API endpoint: <code className="font-mono">/api</code> (proxied to
            localhost:8000)
          </p>
        </div>

        {/* About */}
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-medium text-foreground">About</h2>
          <p className="mt-2 text-xs text-muted">
            Muninn is a cross-tool MCP memory server for solo builders.
          </p>
          <p className="mt-1 text-[10px] text-muted">
            Dashboard v0.1.0
          </p>
        </div>
      </div>
    </div>
  );
}
