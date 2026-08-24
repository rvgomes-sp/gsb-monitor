import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "../../../../lib/auth";

export async function POST() {
  const response = NextResponse.json(
    { status: "OK" },
    { headers: { "Cache-Control": "private, no-store, max-age=0" } },
  );
  response.cookies.set(SESSION_COOKIE, "", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0,
    expires: new Date(0),
  });
  return response;
}

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
