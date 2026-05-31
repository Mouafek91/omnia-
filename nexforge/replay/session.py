"""Session record + storage."""
from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass(frozen=True)
class SessionRecord:
    timestamp_us: int
    kind: str
    channel: str
    value: any
    ir_hash: str = ""


@dataclass
class Session:
    name: str
    ir_hash: str
    records: list

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"name": self.name, "ir_hash": self.ir_hash,
                "records": [asdict(r) for r in self.records]}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = [SessionRecord(**r) for r in data["records"]]
        return cls(name=data["name"], ir_hash=data["ir_hash"], records=records)

    def iterate(self):
        for r in sorted(self.records, key=lambda x: x.timestamp_us):
            yield r
