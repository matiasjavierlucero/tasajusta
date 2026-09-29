import { NextRequest } from "next/server";

export const maxDuration = 60;

const LAMBDA_URL =
  process.env.LAMBDA_API_URL ??
  "https://5yoo5ugs44.execute-api.us-east-1.amazonaws.com";

export async function POST(req: NextRequest) {
  const body = await req.json();

  const upstream = await fetch(`${LAMBDA_URL}/agent/stream`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(body),
  });

  return new Response(upstream.body, {
    status:  upstream.status,
    headers: {
      "Content-Type":      "text/event-stream",
      "Cache-Control":     "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
