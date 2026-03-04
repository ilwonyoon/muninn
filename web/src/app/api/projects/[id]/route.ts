import { NextRequest, NextResponse } from "next/server";
import { getProjectOrNull, updateProject, deleteProject } from "@/lib/api";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const project = await getProjectOrNull(id);
  if (!project) {
    return NextResponse.json(
      { error: `Project '${id}' not found`, code: "NOT_FOUND" },
      { status: 404 }
    );
  }
  return NextResponse.json(project);
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON body", code: "BAD_REQUEST" },
      { status: 400 }
    );
  }

  const data: Partial<{
    name: string;
    status: string;
    summary: string | null;
    github_repo: string | null;
    category: string;
  }> = {};

  if ("name" in body) data.name = (body.name as string | undefined) ?? undefined;
  if ("status" in body) data.status = (body.status as string | undefined) ?? undefined;
  if ("summary" in body) data.summary = (body.summary as string | null) ?? null;
  if ("github_repo" in body) data.github_repo = (body.github_repo as string | null) ?? null;
  if ("category" in body) data.category = (body.category as string | undefined) ?? undefined;

  if (Object.keys(data).length === 0) {
    return NextResponse.json(
      {
        error: "No valid fields provided. Allowed: name, status, summary, github_repo, category",
        code: "BAD_REQUEST",
      },
      { status: 400 }
    );
  }

  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const updated = await updateProject(id, data as any);
    return NextResponse.json(updated);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    if (message.includes("not found")) {
      return NextResponse.json(
        { error: `Project '${id}' not found`, code: "NOT_FOUND" },
        { status: 404 }
      );
    }
    return NextResponse.json(
      { error: message, code: "BAD_REQUEST" },
      { status: 400 }
    );
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  try {
    const result = await deleteProject(id);
    if (!result.deleted) {
      return NextResponse.json(
        { error: `Project '${id}' not found`, code: "NOT_FOUND" },
        { status: 404 }
      );
    }
    return NextResponse.json({ deleted: true });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    if (message.includes("not found")) {
      return NextResponse.json(
        { error: `Project '${id}' not found`, code: "NOT_FOUND" },
        { status: 404 }
      );
    }
    throw err;
  }
}
