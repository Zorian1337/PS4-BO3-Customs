#!/usr/bin/env python3
"""Compare SCE loader metadata from two FSELF/OELF files without executing them."""
from pathlib import Path
import json
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / ".github/scripts"))
from verify_sprx import Elf


def module(path):
    data = Path(path).read_bytes()
    form = "ELF/OELF"
    if data[:4] == bytes.fromhex("4f153d1d"):
        form = "FSELF"
        count = struct.unpack_from("<H", data, 24)[0]
        embedded = 32 + count * 32
        header = bytearray(data[embedded:embedded + 64])
        phoff = struct.unpack_from("<Q", header, 32)[0]
        phnum = struct.unpack_from("<H", header, 56)[0]
        phend = phoff + phnum * 56
        headers = data[embedded:embedded + phend]
        ph = [struct.unpack_from("<IIQQQQQQ", headers, phoff + i * 56) for i in range(phnum)]
        size = max([phend] + [p[2] + p[5] for p in ph])
        if size > 32 * 1024 * 1024:
            raise ValueError("Unexpected module image size")
        image = bytearray(size)
        image[:phend] = headers
        for i in range(count):
            flags, offset, filesz, memsz = struct.unpack_from("<QQQQ", data, 32 + i * 32)
            if flags & 0xF0000:
                continue
            index = (flags >> 20) & 0xFFFF
            if index >= len(ph) or flags & 0xA or offset + filesz > len(data):
                raise ValueError("Unsupported FSELF segment")
            p = ph[index]
            if filesz != memsz or filesz != p[5]:
                raise ValueError("Unexpected segment size")
            image[p[2]:p[2] + filesz] = data[offset:offset + filesz]
        # Section headers are not retained in a FSELF payload. Only loader
        # metadata is inspected here; do not synthesize a source symbol table.
        struct.pack_into("<Q", image, 40, 0)
        struct.pack_into("<HH", image, 60, 0, 0)
        data = bytes(image)
    elf = Elf(data)
    dynamic = elf.segment(2)
    tags = {}
    for offset in range(dynamic[2], dynamic[2] + dynamic[5], 16):
        tag, value = struct.unpack_from("<QQ", data, offset)
        tags.setdefault(tag, []).append(value)
    dynlib = elf.segment(0x61000000)
    strings = elf.slice(dynlib[2] + tags[0x61000035][0], tags[0x61000037][0])
    libraries = {v >> 48: Elf.string(strings, v & 0xFFFFFFFF) for v in tags[0x61000015]}
    imports = []
    exports = []
    at = dynlib[2] + tags[0x61000039][0]
    for offset in range(at, at + tags[0x6100003F][0], 24):
        name, info, other, section, value, size = struct.unpack("<IBBHQQ", elf.slice(offset, 24))
        if name:
            (exports if section else imports).append(Elf.string(strings, name))
    params = elf.segment(0x61000002)
    return {
        "path": str(path), "container": form, "sce_type": hex(elf.type),
        "module_parameters": list(struct.unpack("<QQQ", elf.slice(params[2], 24))),
        "libraries": libraries, "library_import_tags": tags.get(0x61000015),
        "imports": sorted(imports), "exports": sorted(exports),
        "init": tags.get(12), "fini": tags.get(13),
        "load_segments": [{"flags": p[1], "alignment": p[7], "file_size": p[5], "memory_size": p[6]}
                          for p in elf.ph if p[0] in (1, 0x61000010)],
    }


if __name__ == "__main__":
    before, after = [module(p) for p in sys.argv[1:3]]
    print(json.dumps({"before": before, "after": after,
        "new_imports": sorted(set(after["imports"]) - set(before["imports"])),
        "removed_imports": sorted(set(before["imports"]) - set(after["imports"])),
        "same_exports": before["exports"] == after["exports"],
        "same_module_parameters": before["module_parameters"] == after["module_parameters"]}, indent=2))
