import { NextResponse } from "next/server";
import { ensureInit, getDashboardStats } from "@/lib/db";

export async function GET() {
  await ensureInit();
  const stats = await getDashboardStats();
  return NextResponse.json(stats);
}
