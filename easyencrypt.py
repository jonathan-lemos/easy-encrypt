import hashlib
from typing import Iterable, Union

from aes256gcmcipher import Aes256GcmCipher
from argon2kdf import Argon2Kdf
from cipher import Cipher
from kdf import Kdf
import json
from bufferedreader import BufferedReader


def sha256hash(b: bytes):
    m = hashlib.sha256()
    m.update(b)
    return m.digest()


def encrypt(password: str, kdf: Kdf, cipher: Cipher, input: Union[bytes, Iterable[bytes], str]):
    key = kdf.derive(password, cipher.key_length())

    head_kdf = kdf.serialize()
    head_cipher = cipher.serialize()
    header = {
        "kdf": head_kdf,
        "cipher": head_cipher
    }
    header_bytes = bytes(json.dumps(header), "utf-8")

    yield b'EZ'
    yield len(header_bytes).to_bytes(4, "big")
    yield header_bytes
    yield from cipher.encrypt(key, input)


def decrypt(password: str, input: Union[bytes, Iterable[bytes], str]) -> Iterable[bytes]:
    with BufferedReader(input) as br:
        if br.read(2) != b'EZ':
            raise ValueError("The data is not valid easyencrypted data (magic header missing)")

        len_bytes = br.read(4)
        if len(len_bytes) != 4:
            raise ValueError("The data is not valid easyencrypted data (header length field missing)")

        header_len = int.from_bytes(len_bytes, "big")
        if header_len < 0:
            raise ValueError("The data is not valid easyencrypted data (header length is negative)")

        header_bytes = br.read(header_len)
        if len(header_bytes) != header_len:
            raise ValueError("The data is not valid easyencrypted data (reached EOF while reading header)")

        header_str = str(header_bytes, "utf-8")
        header = json.loads(header_str)
        header_kdf = header["kdf"]
        header_cipher = header["cipher"]

        kdf = {
            "argon2id": Argon2Kdf.deserialize,
            "argon2d": Argon2Kdf.deserialize,
            "argon2i": Argon2Kdf.deserialize,
        }[header_kdf["algorithm"]](header_kdf)

        cipher = {
            "aes-256-gcm": Aes256GcmCipher.deserialize
        }[header_cipher["algorithm"]](header_cipher)

        key = kdf.derive(password, cipher.key_length())

        return cipher.decrypt(key, br.chunks())

