import { NextRequest, NextResponse } from "next/server";
import { ensureInit, listProjects, createProject, getProject } from "@/lib/db";

export async function GET(request: NextRequest) {
  await ensureInit();
  const status = request.nextUrl.searchParams.get("status") ?? undefined;
  const projects = await listProjects(status);
  return NextResponse.json(projects);
}

export async function POST(request: NextRequest) {
  await ensureInit();
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON body", code: "BAD_REQUEST" },
      { status: 400 }
    );
  }
  const id = body.id as string | undefined;
  const name = body.name as string | undefined;
  if (!id || !name) {
    return NextResponse.json(
      { error: "'id' and 'name' are required", code: "BAD_REQUEST" },
      { status: 400 }
    );
  }
  const existing = await getProject(id);
  if (existing) {
    return NextResponse.json(
      { error: `Project '${id}' already exists`, code: "CONFLICT" },
      { status: 409 }
    );
  }
  const project = await createProject({
    id,
    name,
    summary: (body.summary as string) ?? undefined,
    github_repo: (body.github_repo as string) ?? undefined,
    category: (body.category as string) ?? "project",
  });
  return NextResponse.json(project, { status: 201 });
}
