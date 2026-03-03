import { NextResponse } from "next/server";
import { ensureInit, getDashboardStats } from "@/lib/db";

export async function GET() {
  try {
    await ensureInit();
    const stats = await getDashboardStats();
    return NextResponse.json(stats);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
