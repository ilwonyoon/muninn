import { NextRequest, NextResponse } from "next/server";
import { getMemory, updateMemory, deleteMemory } from "@/lib/api";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  try {
    const memory = await getMemory(id);
    return NextResponse.json(memory);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    if (message.includes("not found")) {
      return NextResponse.json({ error: `Memory '${id}' not found`, code: "NOT_FOUND" }, { status: 404 });
    }
    throw err;
  }
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
    return NextResponse.json({ error: "Invalid JSON body", code: "BAD_REQUEST" }, { status: 400 });
  }
  const content = body.content as string | undefined;
  const tags = body.tags as string[] | undefined;
  if (content === undefined && tags === undefined) {
    return NextResponse.json({ error: "At least one of 'content' or 'tags' is required", code: "BAD_REQUEST" }, { status: 400 });
  }
  try {
    const updated = await updateMemory(id, { content, tags });
    return NextResponse.json(updated);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    if (message.includes("not found")) {
      return NextResponse.json({ error: message, code: "NOT_FOUND" }, { status: 404 });
    }
    return NextResponse.json({ error: message, code: "BAD_REQUEST" }, { status: 400 });
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  try {
    const result = await deleteMemory(id);
    if (!result.deleted) {
      return NextResponse.json({ error: `Memory '${id}' not found`, code: "NOT_FOUND" }, { status: 404 });
    }
    return NextResponse.json({ deleted: true });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    if (message.includes("not found")) {
      return NextResponse.json({ error: `Memory '${id}' not found`, code: "NOT_FOUND" }, { status: 404 });
    }
    throw err;
  }
}
