import { NextRequest, NextResponse } from "next/server";
import { ensureInit, getInstructions, putInstructions } from "@/lib/db";

export async function GET() {
  await ensureInit();
  const instructions = await getInstructions();
  return NextResponse.json({ instructions, path: "turso:instructions" });
}

export async function PUT(request: NextRequest) {
  await ensureInit();
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body", code: "BAD_REQUEST" }, { status: 400 });
  }
  if (
    typeof body !== "object" ||
    body === null ||
    typeof (body as Record<string, unknown>).instructions !== "string"
  ) {
    return NextResponse.json({ error: "'instructions' field (string) is required", code: "BAD_REQUEST" }, { status: 400 });
  }
  const { instructions } = body as { instructions: string };
  await putInstructions(instructions);
  return NextResponse.json({ ok: true });
}
