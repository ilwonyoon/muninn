import { NextRequest, NextResponse } from "next/server";
import { getProjectOrNull, getSummaryRevision } from "@/lib/api";

export async function GET(
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

  const revisions = await getSummaryRevision(projectId);
  return NextResponse.json(revisions);
}
