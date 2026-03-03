import { NextRequest, NextResponse } from "next/server";
import { ensureInit, searchMemories } from "@/lib/db";

export async function GET(request: NextRequest) {
  await ensureInit();
  const sp = request.nextUrl.searchParams;
  const q = sp.get("q") ?? "";
  if (!q.trim()) {
    return NextResponse.json({ error: "'q' query parameter is required", code: "BAD_REQUEST" }, { status: 400 });
  }
  const project = sp.get("project") ?? undefined;
  const tagsParam = sp.get("tags");
  const tags = tagsParam ? tagsParam.split(",").map(t => t.trim()).filter(Boolean) : undefined;
  const limitStr = sp.get("limit");
  const limit = limitStr ? Math.max(1, Math.min(200, parseInt(limitStr, 10) || 50)) : 50;

  const results = await searchMemories(q, project, tags, limit);
  return NextResponse.json({ results, count: results.length });
}
