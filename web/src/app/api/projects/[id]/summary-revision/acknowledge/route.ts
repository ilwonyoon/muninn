import { NextRequest, NextResponse } from "next/server";
import { getProjectOrNull, acknowledgeSummaryRevision } from "@/lib/api";

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: projectId } = await params;

  const project = await getProjectOrNull(projectId);
  if (!project) {
    return NextResponse.json(
      { error: `Project '${projectId}' not found`, code: "NOT_FOUND" },
      { status: 404 }
    );
  }

  await acknowledgeSummaryRevision(projectId);
  return NextResponse.json({ ok: true });
}
