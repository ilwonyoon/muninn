import { NextRequest, NextResponse } from "next/server";
import { getProjectOrNull, listMemories } from "@/lib/api";

export async function GET(
  request: NextRequest,
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

  const searchParams = request.nextUrl.searchParams;

  const rawMaxChars = searchParams.get("max_chars");
  let maxChars: number | undefined;
  if (rawMaxChars !== null) {
    const parsed = parseInt(rawMaxChars, 10);
    if (!isNaN(parsed)) {
      maxChars = Math.min(500000, Math.max(100, parsed));
    }
  }

  const rawTags = searchParams.get("tags");
  const tags = rawTags ? rawTags.split(",").map((t) => t.trim()).filter(Boolean) : undefined;

  const result = await listMemories(projectId, { maxChars, tags });
  return NextResponse.json(result);
}
