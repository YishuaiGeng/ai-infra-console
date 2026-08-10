import base64
import hashlib
import hmac
import os
import uuid

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ai_infra_api.core.config import Settings


class CredentialEncryption:
    def __init__(self, settings: Settings) -> None:
        configured = settings.credential_encryption_key
        if configured is None:
            raw_key = hashlib.sha256(settings.jwt_secret.get_secret_value().encode()).digest()
        else:
            try:
                raw_key = base64.b64decode(configured.get_secret_value(), validate=True)
            except ValueError as error:
                raise ValueError("credential encryption key must be valid base64") from error
        if len(raw_key) != 32:
            raise ValueError("credential encryption key must decode to 32 bytes")
        self._key = raw_key
        self.key_version = settings.credential_encryption_key_version

    def encrypt(self, account_id: uuid.UUID, credential_id: uuid.UUID, value: str) -> bytes:
        nonce = os.urandom(12)
        ciphertext = AESGCM(self._key).encrypt(
            nonce,
            value.encode(),
            self._aad(account_id, credential_id),
        )
        return nonce + ciphertext

    def decrypt(self, account_id: uuid.UUID, credential_id: uuid.UUID, payload: bytes) -> str:
        if len(payload) < 29:
            raise ValueError("encrypted credential payload is invalid")
        plaintext = AESGCM(self._key).decrypt(
            payload[:12],
            payload[12:],
            self._aad(account_id, credential_id),
        )
        return plaintext.decode()

    def fingerprint(self, value: str) -> str:
        return hmac.new(self._key, value.encode(), hashlib.sha256).hexdigest()

    def _aad(self, account_id: uuid.UUID, credential_id: uuid.UUID) -> bytes:
        return f"{account_id}:{credential_id}:{self.key_version}".encode()


def mask_credential(value: str) -> str:
    if len(value) <= 8:
        return f"{value[:2]}****{value[-2:]}"
    return f"{value[:4]}****{value[-4:]}"
