import { NextRequest, NextResponse } from "next/server";
import { ensureInit, getProject, getSummaryRevision } from "@/lib/db";

export async function GET(
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

  const revision = await getSummaryRevision(projectId);
  return NextResponse.json(revision);
}
