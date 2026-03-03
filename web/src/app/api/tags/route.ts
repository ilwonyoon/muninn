import { NextRequest, NextResponse } from "next/server";
import { ensureInit, getAllTags } from "@/lib/db";

export async function GET(request: NextRequest) {
  await ensureInit();
  const project = request.nextUrl.searchParams.get("project") ?? undefined;
  const tags = await getAllTags(project);
  return NextResponse.json(tags);
}
