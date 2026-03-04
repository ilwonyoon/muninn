import { NextRequest, NextResponse } from "next/server";
import { createMemory, getProjectOrNull } from "@/lib/api";

export async function POST(request: NextRequest) {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body", code: "BAD_REQUEST" }, { status: 400 });
  }
  const project_id = body.project_id as string | undefined;
  const content = body.content as string | undefined;
  if (!project_id || !content) {
    return NextResponse.json({ error: "'project_id' and 'content' are required", code: "BAD_REQUEST" }, { status: 400 });
  }
  const project = await getProjectOrNull(project_id);
  if (!project) {
    return NextResponse.json({ error: `Project '${project_id}' not found`, code: "NOT_FOUND" }, { status: 404 });
  }
  try {
    const memory = await createMemory({
      project_id,
      content,
      source: (body.source as string) ?? "manual",
      tags: (body.tags as string[]) ?? undefined,
    });
    return NextResponse.json(memory, { status: 201 });
  } catch (err) {
    return NextResponse.json({ error: String(err), code: "BAD_REQUEST" }, { status: 400 });
  }
}
