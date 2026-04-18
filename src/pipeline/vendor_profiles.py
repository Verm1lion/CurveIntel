"""
CurveIntel — Vendor CSV Profilleri ve Otomatik Tespit.

Desteklenen cihazlar:
  - ZwickRoell testXpert II/III (ASCII/CSV/TRA)
  - Instron Bluehill Universal/3 (CSV)
  - Shimadzu Trapezium X/Lite (CSV)
  - Tinius Olsen Horizon (CSV)
  - MTS TestSuite Elite/Essential (TXT/CSV)
  - DEVOTRANS CKS-III (CSV, Turkce)
  - Hegewald & Peschke LabMaster (CSV, Almanca)
  - NIST Numisheet (CSV)
  - Generic fallback

Kaynak: Opus deep research (prompt2/4.7_opus_ciktisi2.md)
  - zs2decode (ZwickRoell), snpl (Shimadzu), bluer (Instron)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class VendorProfile:
    """Cihaz/yazilim CSV export profili."""
    name: str
    fingerprint_regex: str
    column_map: dict[str, str]
    default_encoding: str = "utf-8"
    default_decimal: str = "."
    default_separator: str = ","
    time_column: str | None = None
    notes: str = ""


# ══════════════════════════════════════════════
# Vendor Profilleri
# ══════════════════════════════════════════════

ZWICKROELL = VendorProfile(
    name="ZwickRoell testXpert",
    fingerprint_regex=(
        r"(?i)(?:testXpert|Zwick[ /\-]?Roell|ZwickRoell|TXpert|"
        r"Standardkraft|Standardweg|Pr.fmaschine|Probenbezeichnung)"
    ),
    column_map={
        # Force
        "Standardkraft": "force", "Standard force": "force",
        "Kraft": "force", "Prufkraft": "force", "F": "force",
        # Displacement
        "Standardweg": "displacement", "Standard travel": "displacement",
        "Traverse": "displacement", "Traversenweg": "displacement",
        "Weg": "displacement", "Extension": "displacement",
        "Crosshead": "displacement",
        # Stress
        "Spannung": "stress", "Zugspannung": "stress",
        "Stress": "stress", "Tensile stress": "stress",
        # Strain
        "Dehnung": "strain", "Tensile strain": "strain",
        "Strain": "strain",
        # Extensometer
        "Extensometer-Dehnung": "extensometer",
        "Extensometer strain": "extensometer",
        # Time
        "Zeit": "time", "Prufzeit": "time",
        "Time": "time", "Test time": "time",
    },
    default_encoding="windows-1252",
    default_decimal=",",
    default_separator=";",
    time_column="Zeit",
    notes="DE locale: ; ayirici, , ondalik. EN locale: , ayirici, . ondalik",
)

INSTRON = VendorProfile(
    name="Instron Bluehill",
    fingerprint_regex=(
        r"(?i)(?:Bluehill|Instron|Specimen_RawData_\d+|"
        r"\.is_(?:tens|comp|flex|peel|tear)|"
        r"Tensile\s+strain\s*\(Extension\)|Specimen\s+label)"
    ),
    column_map={
        # Force
        "Load": "force", "Load (N)": "force", "Load (kN)": "force",
        "Force": "force", "Kraft": "force", "Charge": "force",
        "Carga": "force", "Yuk": "force",
        # Displacement
        "Extension": "displacement", "Extension (mm)": "displacement",
        "Compressive extension": "displacement",
        "Crosshead": "displacement", "Weg": "displacement",
        "Allongement": "displacement", "Uzama": "displacement",
        # Stress
        "Tensile stress": "stress", "Tensile stress (MPa)": "stress",
        "Compressive stress": "stress", "Flexure stress": "stress",
        "Stress": "stress", "Zugspannung": "stress",
        "Contrainte": "stress", "Gerilme": "stress",
        # Strain
        "Tensile strain": "strain",
        "Tensile strain (Extension)": "strain",
        "Tensile strain (Strain 1)": "strain",
        "Strain": "strain", "Dehnung": "strain",
        "Birim uzama": "strain",
        # Time
        "Time": "time", "Time (s)": "time",
        "Zeit": "time", "Temps": "time", "Zaman": "time",
    },
    default_encoding="utf-8",
    default_decimal=".",
    default_separator=",",
    time_column="Time",
    notes="UTF-16 BOM olabilir! Encoding sniff gerekli.",
)

SHIMADZU = VendorProfile(
    name="Shimadzu Trapezium",
    fingerprint_regex=(
        r"(?is)(?:TRAPEZIUM(?:\s*(?:X|LITE\s*X|X-V|2|3))?|"
        r"Shimadzu|Autograph|AG(?:S)?[- ]?(?:X2?|V2?|IS|I)|AGX[- ]?V2?|"
        r"\u8a66\u9a13\u529b|\u30b9\u30c8\u30ed\u30fc\u30af|\u540d\u524d\s*[,\t]|\u8a66\u9a13\u6761\u4ef6)"
    ),
    column_map={
        # Force (JP + EN)
        "\u8a66\u9a13\u529b": "force", "\u529b": "force", "\u8377\u91cd": "force",
        "Force": "force", "Test Force": "force", "Load": "force",
        # Displacement
        "\u30b9\u30c8\u30ed\u30fc\u30af": "displacement", "\u5909\u4f4d": "displacement",
        "\u3064\u304b\u307f\u5177\u9593\u5909\u4f4d": "displacement",
        "\u4f38\u3073": "displacement", "\u4f38\u3073\u8a08\u5909\u4f4d": "displacement",
        "Stroke": "displacement", "Displacement": "displacement",
        "Crosshead": "displacement", "Extension": "displacement",
        "Elongation": "displacement", "Extensometer": "displacement",
        "Grip Separation": "displacement",
        # Stress
        "\u5fdc\u529b": "stress", "\u771f\u5fdc\u529b": "stress",
        "Stress": "stress", "True Stress": "stress",
        # Strain
        "\u6b6a": "strain", "\u3072\u305a\u307f": "strain",
        "\u771f\u3072\u305a\u307f": "strain",
        "Strain": "strain", "True Strain": "strain",
        # Time
        "\u6642\u9593": "time", "\u7d4c\u904e\u6642\u9593": "time",
        "Time": "time", "Elapsed Time": "time",
    },
    default_encoding="shift_jis",
    default_decimal=".",
    default_separator=",",
    time_column="\u6642\u9593",
    notes="Shift-JIS encoding (JP). Western: ASCII/CP1252.",
)

TINIUS_OLSEN = VendorProfile(
    name="Tinius Olsen Horizon",
    fingerprint_regex=r"(?i)(?:Tinius\s*Olsen|Horizon|QMat|Test\s*Navigator)",
    column_map={
        "Load": "force", "Force": "force", "Load (N)": "force",
        "Extension": "displacement", "Stroke": "displacement",
        "Travel": "displacement",
        "Stress": "stress", "Stress (MPa)": "stress",
        "Strain": "strain", "Strain (%)": "strain",
        "Time": "time", "Time (s)": "time",
    },
    default_encoding="windows-1252",
    default_decimal=".",
    default_separator=",",
    time_column="Time",
)

MTS = VendorProfile(
    name="MTS TestSuite",
    fingerprint_regex=(
        r"(?i)(?:\b(?:Axial\s+(?:Force|Displacement|Strain)|_Load|_Time)\b|"
        r"MTS\s*TestSuite)"
    ),
    column_map={
        "Time": "time", "_Time": "time",
        "Axial Force": "force", "Load": "force", "_Load": "force",
        "Axial Displacement": "displacement",
        "Crosshead": "displacement",
        "Axial Strain": "strain",
        "Axial Stress": "stress",
    },
    default_encoding="utf-8",
    default_decimal=".",
    default_separator="\t",
    time_column="Time",
)

DEVOTRANS = VendorProfile(
    name="DEVOTRANS CKS-III",
    fingerprint_regex=(
        r"(?i)(?:DEVOTRANS|\bDVT\b|\bCKS(?:-?III)?\b|"
        r"Kuvvet|Uzama|Gerilme|Numune)"
    ),
    column_map={
        "Kuvvet": "force", "Kuvvet (N)": "force", "Force": "force",
        "Uzama": "displacement", "Uzama (mm)": "displacement",
        "Ekstansometrik Uzama": "extensometer",
        "Gerilme": "stress", "Gerilme (MPa)": "stress",
        "Gerilme (N/mm2)": "stress",
        "Birim Uzama": "strain", "% Uzama": "strain",
        "Zaman": "time", "Zaman (s)": "time",
    },
    default_encoding="windows-1254",
    default_decimal=",",
    default_separator=";",
    time_column="Zaman",
    notes="Turkce locale: ; ayirici, , ondalik.",
)

HEGEWALD = VendorProfile(
    name="Hegewald & Peschke LabMaster",
    fingerprint_regex=(
        r"(?i)(?:LabMaster|Hegewald(?:[ -]Peschke)?|Inspekt|\bH&P\b|"
        r"Zugversuch|Druckversuch)"
    ),
    column_map={
        "Kraft": "force", "Kraft [N]": "force", "Force": "force",
        "Weg": "displacement", "Standardweg": "displacement",
        "Traversenweg": "displacement", "Weg [mm]": "displacement",
        "Dehnung": "strain", "Dehnung [%]": "strain",
        "Spannung": "stress", "Spannung [MPa]": "stress",
        "Spannung [N/mm2]": "stress",
        "Zeit": "time", "Zeit [s]": "time",
    },
    default_encoding="windows-1252",
    default_decimal=",",
    default_separator=";",
    time_column="Zeit",
)

NIST_NUMISHEET = VendorProfile(
    name="NIST Numisheet",
    fingerprint_regex=r"(?i)(?:Numisheet|NIST|Estrain|Estress|Tstrain|Tstress)",
    column_map={
        "Estress": "stress", "Tstress": "stress",
        "Estrain": "strain", "Tstrain": "strain",
        "Time": "time",
    },
    default_encoding="utf-8",
    default_decimal=".",
    default_separator=",",
    time_column="Time",
)


# ══════════════════════════════════════════════
# Vendor Tespit Motoru
# ══════════════════════════════════════════════

# Oncelik sirasi: spesifik → genel
ALL_PROFILES: list[VendorProfile] = [
    ZWICKROELL,
    INSTRON,
    SHIMADZU,
    MTS,
    TINIUS_OLSEN,
    DEVOTRANS,
    HEGEWALD,
    NIST_NUMISHEET,
]

# Encoding fallback zinciri (Opus onerisi)
ENCODING_CHAIN = [
    "utf-8-sig",    # UTF-8 with BOM
    "utf-16",       # Instron Bluehill
    "shift_jis",    # Shimadzu Trapezium
    "windows-1252", # ZwickRoell, Hegewald
    "windows-1254", # DEVOTRANS (Turkce)
    "latin-1",      # Son care
]


def detect_vendor(filepath, max_lines: int = 40) -> VendorProfile | None:
    """
    CSV dosyasindan vendor'u otomatik tespit et.

    2-asamali pipeline (Opus onerisi):
      1. Fingerprint sniff: ilk N satiri regex ile tara
      2. En yuksek skor ile vendor sec

    Args:
        filepath: CSV dosya yolu
        max_lines: Okunacak maksimum satir sayisi

    Returns:
        VendorProfile veya None (tespit edilemezse)
    """
    from pathlib import Path
    filepath = Path(filepath)

    # Dosyayi oku (encoding chain ile)
    raw_text = ""
    used_encoding = "utf-8"

    for enc in ENCODING_CHAIN:
        try:
            with open(filepath, "r", encoding=enc, errors="strict") as f:
                lines = [f.readline() for _ in range(max_lines)]
            raw_text = "\n".join(lines)
            used_encoding = enc
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if not raw_text:
        # Son care: latin-1 her zaman calisir
        with open(filepath, "r", encoding="latin-1") as f:
            lines = [f.readline() for _ in range(max_lines)]
        raw_text = "\n".join(lines)
        used_encoding = "latin-1"

    # Fingerprint match: en cok eslesen vendor
    best_profile = None
    best_score = 0

    for profile in ALL_PROFILES:
        matches = re.findall(profile.fingerprint_regex, raw_text)
        score = len(matches)
        if score > best_score:
            best_score = score
            best_profile = profile

    return best_profile


def detect_encoding(filepath) -> str:
    """
    Dosyanin encoding'ini tespit et.

    BOM kontrolu + chardet fallback.
    """
    from pathlib import Path
    filepath = Path(filepath)

    # BOM kontrolu
    with open(filepath, "rb") as f:
        raw = f.read(4)

    if raw[:3] == b"\xef\xbb\xbf":
        return "utf-8-sig"
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "utf-16"

    # Encoding chain ile deneme
    for enc in ENCODING_CHAIN:
        try:
            with open(filepath, "r", encoding=enc, errors="strict") as f:
                f.read(4096)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue

    return "latin-1"


def detect_decimal_separator(sample_lines: list[str], separator: str = ",") -> str:
    """
    Ondalik ayiriciyi tespit et.

    Mantig: Sayi iceren hucrelerde virgul/nokta sayisini karsilastir.
    """
    dot_count = 0
    comma_count = 0

    for line in sample_lines:
        cells = line.split(separator) if separator != "," else line.split("\t")
        for cell in cells:
            cell = cell.strip().strip('"')
            # Sayi benzeri mi?
            if re.match(r"^-?\d", cell):
                dot_count += cell.count(".")
                comma_count += cell.count(",")

    # Noktalar cogunluktaysa . ondalik, virgul cogunluktaysa , ondalik
    if comma_count > dot_count * 2:
        return ","
    return "."
