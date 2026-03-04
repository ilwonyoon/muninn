import { NextRequest, NextResponse } from "next/server";
import { getInstructions, updateInstructions } from "@/lib/api";

export async function GET() {
  const { content, path } = await getInstructions();
  return NextResponse.json({ instructions: content, path });
}

export async function PUT(request: NextRequest) {
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
  await updateInstructions(instructions);
  return NextResponse.json({ ok: true });
}
