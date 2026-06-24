export type ProofRequest = {
  input: string;
  init?: RequestInit;
};

export type DeviceProofProvider = {
  proofHeader(input: string, init?: RequestInit): Promise<string>;
};

const DPOP_TYPE = "dpop+jwt";
const DPOP_ALGORITHM = "RS256";

let keyPairPromise: Promise<CryptoKeyPair> | null = null;

function base64Url(raw: ArrayBuffer | Uint8Array): string {
  const bytes = raw instanceof Uint8Array ? raw : new Uint8Array(raw);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  const encoded =
    typeof btoa === "function" ? btoa(binary) : Buffer.from(bytes).toString("base64");
  return encoded.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function jsonPart(value: unknown): string {
  return base64Url(new TextEncoder().encode(JSON.stringify(value)));
}

function requestUrl(input: string): string {
  const origin =
    typeof window !== "undefined" && window.location?.origin
      ? window.location.origin
      : "http://localhost";
  return new URL(input, origin).toString();
}

async function keyPair(): Promise<CryptoKeyPair> {
  if (!keyPairPromise) {
    keyPairPromise = crypto.subtle.generateKey(
      {
        name: "RSASSA-PKCS1-v1_5",
        modulusLength: 2048,
        publicExponent: new Uint8Array([1, 0, 1]),
        hash: "SHA-256",
      },
      false,
      ["sign", "verify"],
    );
  }
  return keyPairPromise;
}

async function publicJwk(): Promise<JsonWebKey> {
  const pair = await keyPair();
  return crypto.subtle.exportKey("jwk", pair.publicKey);
}

export async function deviceProofThumbprint(): Promise<string> {
  const jwk = await publicJwk();
  if (!jwk.e || !jwk.n || jwk.kty !== "RSA") {
    throw new Error("Unsupported browser proof key");
  }
  const canonical = JSON.stringify({ e: jwk.e, kty: "RSA", n: jwk.n });
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonical));
  return base64Url(digest);
}

export const browserDeviceProof: DeviceProofProvider = {
  async proofHeader(input: string, init: RequestInit = {}): Promise<string> {
    const pair = await keyPair();
    const jwk = await publicJwk();
    const method = String(init.method ?? "GET").toUpperCase();
    const issuedAt = Math.floor(Date.now() / 1000);
    const header = jsonPart({
      typ: DPOP_TYPE,
      alg: DPOP_ALGORITHM,
      jwk: {
        kty: jwk.kty,
        n: jwk.n,
        e: jwk.e,
      },
    });
    const payload = jsonPart({
      htm: method,
      htu: requestUrl(input),
      iat: issuedAt,
      jti: crypto.randomUUID(),
    });
    const signingInput = `${header}.${payload}`;
    const signature = await crypto.subtle.sign(
      "RSASSA-PKCS1-v1_5",
      pair.privateKey,
      new TextEncoder().encode(signingInput),
    );
    return `${signingInput}.${base64Url(signature)}`;
  },
};
