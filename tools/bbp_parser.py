#!/usr/bin/env python3
"""Parser do blueprints-pack.bbp (Warhammer 40k Rogue Trader, Owlcat/Unity).

Formato (confirmado no código do jogo — Kingmaker.Blueprints.JsonSystem.BlueprintsCache
e na reimplementação MIT xADDBx/BpBinReader):

- Header: int32 LE `count`, seguido de `count` registros TOC de 20 bytes:
  GUID (16 bytes, layout .NET/bytes_le) + uint32 LE offset ABSOLUTO no arquivo
  (offset 0 = blueprint nulo).
- Cada entrada é serializada pelo ReflectionBasedSerializer da Owlcat
  (binário dirigido por reflexão, sem nomes de campo no stream):
    [16B TypeId do tipo raiz][corpo do objeto campo-a-campo][Name: string]
    [AssetId: string = guid "N"]
  Strings são no formato .NET BinaryReader (comprimento 7-bit varint + UTF-8).
- A ordem/tipo dos campos vem dos assemblies do jogo. Esse schema é extraído
  uma única vez por tools/bbp_schema_dumper (C#, MetadataLoadContext) para
  `bbp_schema_rt.json(.gz)`, consumido por este parser.

Uso:
    python tools/bbp_parser.py <arquivo.bbp> <guid>              # imprime JSON
    python tools/bbp_parser.py <arquivo.bbp> --dump-names out.json \
        [--types BlueprintArea,BlueprintQuest,...] [--all-types]
    python tools/bbp_parser.py <arquivo.bbp> --info

Notas:
- Referências a assets Unity (UnityObjectRef) são emitidas como
  {"Index": n} sem resolver o `blueprint.assets` (exigiria parsear o bundle
  Unity; o índice é estável e suficiente para correlação).
- LocalizedString é emitida como {"m_Key": chave} — o texto vive nos packs de
  localização do jogo, não no .bbp.
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import struct
import sys
import uuid
from pathlib import Path

DEFAULT_SCHEMA = Path(__file__).resolve().parent / "bbp_schema_rt.json.gz"

# Tipos padrão do --dump-names (prefixo do nome simples do tipo raiz)
DEFAULT_NAME_TYPES = (
    "BlueprintArea",
    "BlueprintQuest",
    "BlueprintQuestObjective",
    "BlueprintItem",
)


class BinaryReader:
    """Réplica mínima do System.IO.BinaryReader (LE, UTF-8)."""

    __slots__ = ("data", "pos")

    def __init__(self, data: bytes, pos: int = 0):
        self.data = data
        self.pos = pos

    def read(self, n: int) -> bytes:
        b = self.data[self.pos : self.pos + n]
        if len(b) != n:
            raise EOFError(f"EOF em 0x{self.pos:x} lendo {n} bytes")
        self.pos += n
        return b

    def i32(self) -> int:
        return struct.unpack_from("<i", self.data, self._adv(4))[0]

    def u32(self) -> int:
        return struct.unpack_from("<I", self.data, self._adv(4))[0]

    def i64(self) -> int:
        return struct.unpack_from("<q", self.data, self._adv(8))[0]

    def u64(self) -> int:
        return struct.unpack_from("<Q", self.data, self._adv(8))[0]

    def f32(self) -> float:
        return struct.unpack_from("<f", self.data, self._adv(4))[0]

    def f64(self) -> float:
        return struct.unpack_from("<d", self.data, self._adv(8))[0]

    def byte(self) -> int:
        return self.data[self._adv(1)]

    def boolean(self) -> bool:
        return self.byte() != 0

    def string(self) -> str:
        # 7-bit encoded length + UTF-8
        length = 0
        shift = 0
        while True:
            b = self.byte()
            length |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
            if shift > 35:
                raise ValueError(f"varint inválido em 0x{self.pos:x}")
        return self.read(length).decode("utf-8")

    def guid_n(self) -> str:
        """GUID .NET (bytes_le) como string formato 'N' (32 hex)."""
        return uuid.UUID(bytes_le=self.read(16)).hex

    def _adv(self, n: int) -> int:
        p = self.pos
        if p + n > len(self.data):
            raise EOFError(f"EOF em 0x{p:x} lendo {n} bytes")
        self.pos += n
        return p


ZERO_GUID = "0" * 32


class BbpFile:
    def __init__(self, bbp_path: str | Path, schema_path: str | Path | None = None):
        self.path = Path(bbp_path)
        self.data = self.path.read_bytes()
        self.schema = self._load_schema(schema_path)
        self.type_ids: dict[str, str] = self.schema["type_ids"]  # typeid N -> fullName
        self.types: dict[str, dict] = self.schema["types"]  # fullName -> {name, fields}
        self.enums: dict[str, dict] = self.schema["enums"]

        (count,) = struct.unpack_from("<I", self.data, 0)
        self.index: dict[str, int] = {}  # guid N -> offset (0 = nulo, omitido)
        pos = 4
        for _ in range(count):
            g = uuid.UUID(bytes_le=self.data[pos : pos + 16]).hex
            (off,) = struct.unpack_from("<I", self.data, pos + 16)
            pos += 20
            if off:
                self.index[g] = off
        # tamanho de cada entrada = próximo offset (entradas são contíguas)
        offsets = sorted(set(self.index.values()))
        nxt = {a: b for a, b in zip(offsets, offsets[1:])}
        last = offsets[-1] if offsets else len(self.data)
        self.entry_end = {off: nxt.get(off, len(self.data) if off == last else off) for off in offsets}

    @staticmethod
    def _load_schema(schema_path) -> dict:
        p = Path(schema_path) if schema_path else DEFAULT_SCHEMA
        if not p.exists() and p.suffix == ".gz" and p.with_suffix("").exists():
            p = p.with_suffix("")
        opener = gzip.open if p.suffix == ".gz" else open
        with opener(p, "rt", encoding="utf-8") as f:
            return json.load(f)

    # ---------- API ----------

    def guids(self):
        return self.index.keys()

    def root_type(self, guid: str) -> str | None:
        """Nome completo do tipo raiz sem decodificar o corpo."""
        off = self.index[self._norm(guid)]
        tid = uuid.UUID(bytes_le=self.data[off : off + 16]).hex
        if tid == ZERO_GUID:
            return None
        return self.type_ids.get(tid)

    def get_blueprint(self, guid: str) -> dict | None:
        """Decodifica uma entrada: {"Data": {...}, "Name": ..., "AssetId": ...}."""
        g = self._norm(guid)
        off = self.index.get(g)
        if off is None:
            raise KeyError(f"guid {g} não está no TOC")
        r = BinaryReader(self.data, off)
        tid = uuid.UUID(bytes_le=r.read(16)).hex
        if tid == ZERO_GUID:
            return None
        schema = self._resolve(tid)
        data = self._read_object_body(r, schema, identified=True, tid=tid)
        name = r.string()
        if self.schema.get("use_string_asset_id", True):
            asset_id = r.string()
        else:
            asset_id = r.guid_n()
        return {"Data": data, "AssetId": asset_id, "Name": name}

    def get_name(self, guid: str) -> str | None:
        """Nome interno via heurística de cauda (rápida), com fallback pra decode."""
        g = self._norm(guid)
        off = self.index[g]
        end = self.entry_end[off]
        entry = self.data[off:end]
        # AssetId no fim: string de 32 hex == guid do TOC
        if len(entry) > 33 and entry[-33] == 0x20 and entry[-32:] == g.encode("ascii"):
            body = entry[:-33]
            candidates = []
            for ln in range(0, min(201, len(body))):
                p = len(body) - 1 - ln
                if p < 0:
                    break
                if body[p] == ln:
                    try:
                        s = body[p + 1 :].decode("utf-8")
                    except UnicodeDecodeError:
                        continue
                    if all(0x20 <= ord(c) < 0x110000 and c != "\x7f" for c in s):
                        candidates.append(s)
            if len(candidates) == 1:
                return candidates[0]
        bp = self.get_blueprint(g)
        return bp["Name"] if bp else None

    # ---------- decodificação dirigida por schema ----------

    def _norm(self, guid: str) -> str:
        return guid.replace("-", "").lower()

    def _resolve(self, tid: str) -> dict:
        full = self.type_ids.get(tid)
        if full is None:
            raise KeyError(f"TypeId {tid} ausente no schema")
        return self.types[full]

    def _read_object_body(self, r: BinaryReader, schema: dict, identified: bool, tid: str = "") -> dict:
        obj: dict = {}
        if identified:
            obj["$type"] = tid + ", " + schema["name"]
        for field in schema["fields"]:
            try:
                obj[field["name"]] = self._read_value(r, field["value"])
            except Exception as e:
                raise RuntimeError(
                    f"falha em {schema['name']}.{field['name']} "
                    f"kind={field['value']['kind']} pos=0x{r.pos:x}: {e}"
                ) from e
        return obj

    def _read_value(self, r: BinaryReader, v: dict):
        kind = v["kind"]
        if kind == "Int32":
            return r.i32()
        if kind == "UInt32":
            return r.u32()
        if kind == "Int64":
            return r.i64()
        if kind == "UInt64":
            return r.u64()
        if kind == "Single":
            return r.f32()
        if kind == "Double":
            return r.f64()
        if kind == "Boolean":
            return r.boolean()
        if kind == "String":
            return r.string()
        if kind == "EnumInt32":
            return self._enum_repr(v["enum"], r.i32())
        if kind == "BlueprintRef":
            g = r.string()
            return ("!bp_" + g) if g else None
        if kind == "UnityObjectRef":
            idx = r.i32()
            return {"Index": idx} if idx >= 0 else None
        if kind == "WeakResourceLink":
            if self.schema.get("serialized_field_name"):
                fn = r.string()
                if fn != "AssetId":
                    raise ValueError("WeakResourceLink sem campo AssetId")
            aid = r.string()
            return {"AssetId": aid} if aid.strip() else None
        if kind == "LocalizedString":
            return {"m_Key": r.string()}
        if kind == "Color":
            return {"r": r.f32(), "g": r.f32(), "b": r.f32(), "a": r.f32()}
        if kind == "Color32":
            packed = r.i32()
            return {
                "r": packed & 255,
                "g": (packed >> 8) & 255,
                "b": (packed >> 16) & 255,
                "a": (packed >> 24) & 255,
            }
        if kind == "Vector2":
            return {"x": r.f32(), "y": r.f32()}
        if kind == "Vector3":
            return {"x": r.f32(), "y": r.f32(), "z": r.f32()}
        if kind == "Vector4":
            return {"x": r.f32(), "y": r.f32(), "z": r.f32(), "w": r.f32()}
        if kind == "Vector2Int":
            return {"x": r.i32(), "y": r.i32()}
        if kind == "Rect":
            return {"x": r.f32(), "y": r.f32(), "width": r.f32(), "height": r.f32()}
        if kind == "Bounds":
            return {
                "center": {"x": r.f32(), "y": r.f32(), "z": r.f32()},
                "size": {"x": r.f32(), "y": r.f32(), "z": r.f32()},
            }
        if kind == "AnimationCurve":
            n = r.i32()
            return {
                "keys": [
                    {
                        "time": r.f32(),
                        "value": r.f32(),
                        "weightedMode": r.byte(),
                        "inTangent": r.f32(),
                        "inWeight": r.f32(),
                        "outTangent": r.f32(),
                        "outWeight": r.f32(),
                    }
                    for _ in range(n)
                ]
            }
        if kind == "Gradient":
            nc = r.i32()
            color_keys = [
                {"time": r.f32(), "r": r.f32(), "g": r.f32(), "b": r.f32()} for _ in range(nc)
            ]
            na = r.i32()
            alpha_keys = [{"time": r.f32(), "alpha": r.f32()} for _ in range(na)]
            return {"colorKeys": color_keys, "alphaKeys": alpha_keys, "mode": r.byte()}
        if kind == "ColorBlock":
            out = {}
            for k in ("normalColor", "pressedColor", "highlightedColor", "disabledColor"):
                out[k] = self._read_value(r, {"kind": "Color"})
            out["colorMultiplier"] = r.f32()
            out["fadeDuration"] = r.f32()
            return out
        if kind in ("Array", "List"):
            n = r.i32()
            elem = v["element"]
            return [self._read_value(r, elem) for _ in range(n)]
        if kind == "Object":
            if v.get("identified") or v.get("force_needs_type"):
                tid = uuid.UUID(bytes_le=r.read(16)).hex
                if tid == ZERO_GUID:
                    return None
                schema = self._resolve(tid)
                return self._read_object_body(r, schema, identified=bool(v.get("identified")), tid=tid)
            return self._read_object_body(r, self.types[v["type"]], identified=False)
        if kind == "BlueprintGuid":
            return "!bp_" + r.guid_n()
        if kind == "BlueprintRefWrath":
            g = r.guid_n()
            return ("!bp_" + g) if g != ZERO_GUID else None
        raise ValueError(f"kind não suportado: {kind}")

    def _enum_repr(self, enum_name: str, value: int):
        e = self.enums.get(enum_name)
        if e is None:
            return value
        values = e["values"]
        if e.get("is_flags"):
            names = [n for n, val in values.items() if val & value]
            return " | ".join(names) if names else value
        for n, val in values.items():
            if val == value:
                return n
        return value


def cmd_dump_names(bbp: BbpFile, out_path: str, prefixes: tuple[str, ...] | None):
    result = {}
    stats = {"total": 0, "filtrados": 0, "decodificados": 0, "falhas": 0, "tipo_desconhecido": 0}
    for g in bbp.guids():
        stats["total"] += 1
        full = bbp.root_type(g)
        if full is None:
            continue
        simple = full.rsplit(".", 1)[-1]
        if prefixes is not None and not any(simple.startswith(p) for p in prefixes):
            continue
        stats["filtrados"] += 1
        try:
            name = bbp.get_name(g)
            stats["decodificados"] += 1
        except Exception:
            stats["falhas"] += 1
            name = None
        result[g] = {"name": name, "type": simple}
    Path(out_path).write_text(
        json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
    )
    print(
        f"{out_path}: {len(result)} entradas "
        f"(TOC total={stats['total']}, filtrados={stats['filtrados']}, "
        f"falhas={stats['falhas']})",
        file=sys.stderr,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("bbp", help="caminho do blueprints-pack.bbp")
    ap.add_argument("guid", nargs="?", help="guid do blueprint (com ou sem hífens)")
    ap.add_argument("--schema", help=f"schema JSON(.gz) (default: {DEFAULT_SCHEMA})")
    ap.add_argument("--dump-names", metavar="SAIDA.json", help="gera mapping guid -> nome/tipo")
    ap.add_argument(
        "--types",
        help="prefixos de tipo (separados por vírgula) pro --dump-names "
        f"(default: {','.join(DEFAULT_NAME_TYPES)})",
    )
    ap.add_argument("--all-types", action="store_true", help="--dump-names sem filtro de tipo")
    ap.add_argument("--info", action="store_true", help="estatísticas do arquivo")
    args = ap.parse_args()

    bbp = BbpFile(args.bbp, args.schema)

    if args.info:
        print(f"entradas no TOC (não nulas): {len(bbp.index)}")
        print(f"tipos no schema: {len(bbp.types)}; type_ids: {len(bbp.type_ids)}")
        return

    if args.dump_names:
        if args.all_types:
            prefixes = None
        elif args.types:
            prefixes = tuple(t.strip() for t in args.types.split(",") if t.strip())
        else:
            prefixes = DEFAULT_NAME_TYPES
        cmd_dump_names(bbp, args.dump_names, prefixes)
        return

    if not args.guid:
        ap.error("informe um guid, --dump-names ou --info")
    bp = bbp.get_blueprint(args.guid)
    json.dump(bp, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
