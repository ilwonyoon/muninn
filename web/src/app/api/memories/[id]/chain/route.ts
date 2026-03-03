import { NextRequest, NextResponse } from "next/server";
import { ensureInit, getSupersedChain } from "@/lib/db";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  await ensureInit();
  const { id } = await params;
  const chain = await getSupersedChain(id);
  if (chain.length === 0) {
    return NextResponse.json({ error: `Memory '${id}' not found or has no chain`, code: "NOT_FOUND" }, { status: 404 });
  }
  return NextResponse.json(chain);
}
