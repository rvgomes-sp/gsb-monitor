const encoder = new TextEncoder();
export const SESSION_COOKIE = "gsb_session";

function toBase64Url(bytes: Uint8Array) {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function fromBase64Url(value: string) {
  const base64 = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
  const binary = atob(padded);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

async function hmac(value: string, secret: string) {
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return new Uint8Array(await crypto.subtle.sign("HMAC", key, encoder.encode(value)));
}

export async function sha256(value: string) {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(value));
  return toBase64Url(new Uint8Array(digest));
}

export async function createSessionToken(email: string, secret: string) {
  const payload = toBase64Url(
    encoder.encode(JSON.stringify({
      email: email.toLowerCase(),
      exp: Date.now() + 12 * 60 * 60 * 1000,
    })),
  );
  const signature = toBase64Url(await hmac(payload, secret));
  return `${payload}.${signature}`;
}

export async function verifySessionToken(token: string, secret: string) {
  const [payload, signature] = token.split(".");
  if (!payload || !signature) return null;
  const expected = await hmac(payload, secret);
  const received = fromBase64Url(signature);
  if (expected.length !== received.length) return null;
  let difference = 0;
  for (let index = 0; index < expected.length; index += 1) {
    difference |= expected[index] ^ received[index];
  }
  if (difference !== 0) return null;
  try {
    const decoded = JSON.parse(new TextDecoder().decode(fromBase64Url(payload))) as {
      email?: string;
      exp?: number;
    };
    if (!decoded.email || !decoded.exp || decoded.exp < Date.now()) return null;
    return { email: decoded.email, exp: decoded.exp };
  } catch {
    return null;
  }
}

export type PortalProfile = {
  email: string;
  name: string;
  role: string;
  initials: string;
};

const portalProfiles: Record<string, Omit<PortalProfile, "email">> = {
  "rodrigo.vazquez@vazquezefonseca.com.br": {
    name: "Rodrigo Vazquez",
    role: "Diretor do Projeto",
    initials: "RV",
  },
  "ana.fonseca@vazquezefonseca.com.br": {
    name: "Ana Fonseca",
    role: "Diretora Institucional",
    initials: "AF",
  },
};

export function portalProfile(email: string): PortalProfile {
  const normalized = email.trim().toLowerCase();
  const known = portalProfiles[normalized];
  if (known) return { email: normalized, ...known };

  const localPart = normalized.split("@")[0] || "Usuário";
  const words = localPart
    .split(/[._-]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1));
  const name = words.join(" ") || normalized;
  const initials = words
    .slice(0, 2)
    .map((word) => word.charAt(0))
    .join("")
    .toUpperCase() || "US";

  return {
    email: normalized,
    name,
    role: "Usuário autenticado",
    initials,
  };
}

export function configuredAccounts() {
  try {
    const stored = process.env.PORTAL_ACCOUNTS ?? "";
    if (!stored) return {};
    const decoded = stored.startsWith("{")
      ? stored
      : new TextDecoder().decode(fromBase64Url(stored));
    return JSON.parse(decoded) as Record<string, string>;
  } catch {
    return {};
  }
}
