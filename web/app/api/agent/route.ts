import { NextRequest, NextResponse } from "next/server";

const LAMBDA_URL =
  process.env.LAMBDA_API_URL ??
  "https://5yoo5ugs44.execute-api.us-east-1.amazonaws.com";

export async function POST(req: NextRequest) {
  const body = await req.json();

  const upstream = await fetch(`${LAMBDA_URL}/agent`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(body),
  });

  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}
