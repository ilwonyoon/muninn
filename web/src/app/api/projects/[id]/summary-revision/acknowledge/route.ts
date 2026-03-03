import { NextRequest, NextResponse } from "next/server";
import { ensureInit, getProject, clearSummaryRevision } from "@/lib/db";

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  await ensureInit();
  const { id: projectId } = await params;

  const project = await getProject(projectId);
  if (!project) {
    return NextResponse.json(
      { error: `Project '${projectId}' not found`, code: "NOT_FOUND" },
      { status: 404 }
    );
  }

  await clearSummaryRevision(projectId);
  return NextResponse.json({ ok: true });
}
