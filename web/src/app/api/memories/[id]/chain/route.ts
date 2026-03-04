import { NextRequest, NextResponse } from "next/server";
import { getSupersedeChain } from "@/lib/api";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const chain = await getSupersedeChain(id);
  if (chain.length === 0) {
    return NextResponse.json({ error: `Memory '${id}' not found or has no chain`, code: "NOT_FOUND" }, { status: 404 });
  }
  return NextResponse.json(chain);
}
