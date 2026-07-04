// [ENTREVISTA] Route Handler de Next.js: corre en el servidor de Vercel, no en el browser.
// Al llamar desde el frontend a /api/predict (mismo origen), no hay preflight CORS.
// Vercel llama a Lambda servidor-a-servidor donde CORS no aplica.

import { NextRequest, NextResponse } from "next/server";

const LAMBDA_URL =
  process.env.LAMBDA_API_URL ??
  "https://5yoo5ugs44.execute-api.us-east-1.amazonaws.com";

export async function POST(req: NextRequest) {
  const body = await req.json();

  const upstream = await fetch(`${LAMBDA_URL}/predict`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(body),
  });

  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}
