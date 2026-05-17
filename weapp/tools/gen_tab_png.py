"""Write 81x81 RGBA PNGs for tabBar (custom tab still requires paths in app.json)."""
import binascii
import struct
import zlib


def chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", binascii.crc32(tag + data) & 0xFFFFFFFF)


def png_rgba(w: int, h: int, rgba: bytes) -> bytes:
    rows = b"".join(b"\x00" + rgba[y * w * 4 : (y + 1) * w * 4] for y in range(h))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(rows, 9))
        + chunk(b"IEND", b"")
    )


def solid(w: int, h: int, r: int, g: int, b: int) -> bytes:
    px = bytes([r, g, b, 255]) * (w * h)
    return png_rgba(w, h, px)


def main():
    w = h = 81
    base = solid(w, h, 0xE4, 0xDB, 0xD2)
    active = solid(w, h, 0xB8, 0x5C, 0x50)
    out = __import__("pathlib").Path(__file__).resolve().parent.parent / "images"
    out.mkdir(parents=True, exist_ok=True)
    for name in (
        "tab_home",
        "tab_note",
        "tab_card",
        "tab_me",
    ):
        (out / f"{name}.png").write_bytes(base)
        (out / f"{name}_active.png").write_bytes(active)
    print("written to", out)


if __name__ == "__main__":
    main()
