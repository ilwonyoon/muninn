import { NextRequest, NextResponse } from "next/server";
import { listTags } from "@/lib/api";

export async function GET(request: NextRequest) {
  const project = request.nextUrl.searchParams.get("project") ?? undefined;
  const tags = await listTags(project);
  return NextResponse.json(tags);
}
