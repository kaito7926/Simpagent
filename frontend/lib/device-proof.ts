export type ProofRequest = {
  input: string;
  init?: RequestInit;
};

export type DeviceProofProvider = {
  proofHeader(input: string, init?: RequestInit): Promise<string>;
};

export type DeviceProofKeyStore = {
  load(): Promise<CryptoKeyPair | null>;
  save(pair: CryptoKeyPair): Promise<void>;
};

const DPOP_TYPE = "dpop+jwt";
const DPOP_ALGORITHM = "RS256";
const DPOP_DB_NAME = "simpagent-device-proof";
const DPOP_STORE_NAME = "proof-keys";
const DPOP_KEY_ID = "default-rsa-2048";

type StoredProofKey = {
  id: string;
  pair: CryptoKeyPair;
};

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

async function generateKeyPair(): Promise<CryptoKeyPair> {
  return crypto.subtle.generateKey(
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

function openProofDatabase(): Promise<IDBDatabase | null> {
  const indexedDb = globalThis.indexedDB;
  if (!indexedDb) {
    return Promise.resolve(null);
  }

  return new Promise((resolve, reject) => {
    const request = indexedDb.open(DPOP_DB_NAME, 1);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(DPOP_STORE_NAME)) {
        database.createObjectStore(DPOP_STORE_NAME, { keyPath: "id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Unable to open proof key store"));
  });
}

function indexedDbKeyStore(): DeviceProofKeyStore {
  return {
    async load(): Promise<CryptoKeyPair | null> {
      const database = await openProofDatabase();
      if (!database) {
        return null;
      }
      try {
        return await new Promise<CryptoKeyPair | null>((resolve, reject) => {
          const transaction = database.transaction(DPOP_STORE_NAME, "readonly");
          const request = transaction.objectStore(DPOP_STORE_NAME).get(DPOP_KEY_ID);
          request.onsuccess = () => {
            const stored = request.result as StoredProofKey | undefined;
            resolve(stored?.pair ?? null);
          };
          request.onerror = () => reject(request.error ?? new Error("Unable to read proof key"));
        });
      } finally {
        database.close();
      }
    },
    async save(pair: CryptoKeyPair): Promise<void> {
      const database = await openProofDatabase();
      if (!database) {
        return;
      }
      try {
        await new Promise<void>((resolve, reject) => {
          const transaction = database.transaction(DPOP_STORE_NAME, "readwrite");
          const request = transaction.objectStore(DPOP_STORE_NAME).put({ id: DPOP_KEY_ID, pair });
          request.onsuccess = () => resolve();
          request.onerror = () => reject(request.error ?? new Error("Unable to persist proof key"));
        });
      } finally {
        database.close();
      }
    },
  };
}

export function createDeviceProofProvider(
  keyStore: DeviceProofKeyStore | null = indexedDbKeyStore(),
): DeviceProofProvider & { thumbprint(): Promise<string> } {
  let keyPairPromise: Promise<CryptoKeyPair> | null = null;

  async function keyPair(): Promise<CryptoKeyPair> {
    if (!keyPairPromise) {
      keyPairPromise = (async () => {
        const stored = await keyStore?.load().catch(() => null);
        if (stored) {
          return stored;
        }
        const generated = await generateKeyPair();
        await keyStore?.save(generated).catch(() => undefined);
        return generated;
      })();
    }
    return keyPairPromise;
  }

  async function publicJwk(): Promise<JsonWebKey> {
    const pair = await keyPair();
    return crypto.subtle.exportKey("jwk", pair.publicKey);
  }

  async function thumbprint(): Promise<string> {
    const jwk = await publicJwk();
    if (!jwk.e || !jwk.n || jwk.kty !== "RSA") {
      throw new Error("Unsupported browser proof key");
    }
    const canonical = JSON.stringify({ e: jwk.e, kty: "RSA", n: jwk.n });
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonical));
    return base64Url(digest);
  }

  return {
    thumbprint,
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
}

const defaultDeviceProof = createDeviceProofProvider();

export async function deviceProofThumbprint(): Promise<string> {
  return defaultDeviceProof.thumbprint();
}

export const browserDeviceProof: DeviceProofProvider = {
  proofHeader(input: string, init: RequestInit = {}): Promise<string> {
    return defaultDeviceProof.proofHeader(input, init);
  },
};
