import test from "node:test";
import assert from "node:assert/strict";

import { createDeviceProofProvider, type DeviceProofKeyStore } from "@/lib/device-proof";

void test("device proof provider reuses a persisted non-extractable key pair", async () => {
  let stored: CryptoKeyPair | null = null;
  let saves = 0;
  let savedPrivateKeyExtractable: boolean | null = null;
  const keyStore: DeviceProofKeyStore = {
    async load() {
      return stored;
    },
    async save(pair) {
      saves += 1;
      savedPrivateKeyExtractable = pair.privateKey.extractable;
      stored = pair;
    },
  };

  const firstProvider = createDeviceProofProvider(keyStore);
  const firstThumbprint = await firstProvider.thumbprint();

  const secondProvider = createDeviceProofProvider(keyStore);
  const secondThumbprint = await secondProvider.thumbprint();

  assert.equal(firstThumbprint, secondThumbprint);
  assert.equal(saves, 1);
  assert.equal(savedPrivateKeyExtractable, false);
});
