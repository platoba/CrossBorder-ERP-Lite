"""SKU management service for cross-border e-commerce.

Handles SKU generation, cross-platform mapping, collision detection,
prefix-based categorization, and barcode (EAN-13 / UPC-A) validation.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class SKUMapping:
    """Maps an internal SKU to a platform-specific SKU."""
    internal_sku: str
    platform: str
    platform_sku: str
    marketplace: str = ""
    asin: str = ""
    fnsku: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SKUInfo:
    """Parsed SKU breakdown."""
    raw: str
    prefix: str
    category_code: str
    sequence: str
    variant: str
    is_valid: bool
    format_name: str


class BarcodeValidator:
    """EAN-13 and UPC-A barcode validation."""

    @staticmethod
    def validate_ean13(code: str) -> bool:
        """Validate an EAN-13 barcode (13 digits, valid check digit)."""
        if not re.match(r"^\d{13}$", code):
            return False
        digits = [int(d) for d in code]
        total = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
        check = (10 - (total % 10)) % 10
        return check == digits[12]

    @staticmethod
    def validate_upc(code: str) -> bool:
        """Validate a UPC-A barcode (12 digits, valid check digit)."""
        if not re.match(r"^\d{12}$", code):
            return False
        digits = [int(d) for d in code]
        total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(digits[:11]))
        check = (10 - (total % 10)) % 10
        return check == digits[11]

    @staticmethod
    def generate_ean13_check(first12: str) -> str:
        """Generate EAN-13 check digit for first 12 digits."""
        if not re.match(r"^\d{12}$", first12):
            raise ValueError("Need exactly 12 digits")
        digits = [int(d) for d in first12]
        total = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
        check = (10 - (total % 10)) % 10
        return first12 + str(check)

    @staticmethod
    def generate_upc_check(first11: str) -> str:
        """Generate UPC-A check digit for first 11 digits."""
        if not re.match(r"^\d{11}$", first11):
            raise ValueError("Need exactly 11 digits")
        digits = [int(d) for d in first11]
        total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(digits))
        check = (10 - (total % 10)) % 10
        return first11 + str(check)


# ── SKU Format Definitions ──────────────────────────────

# Category prefixes for SKU generation
CATEGORY_PREFIXES = {
    "electronics": "EL",
    "clothing": "CL",
    "home": "HM",
    "beauty": "BT",
    "toys": "TY",
    "sports": "SP",
    "automotive": "AT",
    "garden": "GD",
    "pet": "PT",
    "food": "FD",
    "jewelry": "JW",
    "office": "OF",
    "tools": "TL",
    "baby": "BB",
    "health": "HE",
    "shoes": "SH",
    "bags": "BG",
    "watches": "WT",
    "accessories": "AC",
    "outdoor": "OD",
}

# Platform SKU format patterns
PLATFORM_FORMATS = {
    "amazon": r"^[A-Z0-9\-]{1,40}$",
    "shopify": r"^[A-Za-z0-9\-_]{1,255}$",
    "ebay": r"^[A-Za-z0-9\-_]{1,50}$",
    "aliexpress": r"^[A-Za-z0-9\-_]{1,200}$",
    "tiktok": r"^[A-Za-z0-9\-_]{1,50}$",
    "walmart": r"^[A-Za-z0-9\-]{1,50}$",
}


class SKUManager:
    """SKU generation, validation, and cross-platform mapping."""

    def __init__(self, brand_prefix: str = "CB"):
        self.brand_prefix = brand_prefix.upper()
        self._mappings: dict[str, list[SKUMapping]] = {}  # internal_sku → mappings
        self._reverse: dict[str, str] = {}  # "platform:platform_sku" → internal_sku
        self._counter: int = int(time.time() * 1000) % 100000
        self.barcode = BarcodeValidator()

    # ── SKU Generation ──────────────────────────────────

    def generate(
        self,
        category: str = "",
        variant: str = "",
        sequence: Optional[int] = None,
    ) -> str:
        """Generate a new unique SKU.

        Format: {BRAND}-{CATEGORY}-{SEQ}-{VARIANT}
        Example: CB-EL-00142-BLK
        """
        cat_code = CATEGORY_PREFIXES.get(category.lower(), "GN")

        if sequence is None:
            self._counter += 1
            seq = self._counter
        else:
            seq = sequence

        sku = f"{self.brand_prefix}-{cat_code}-{seq:05d}"
        if variant:
            sku += f"-{variant.upper()[:6]}"
        return sku

    def generate_batch(
        self,
        count: int,
        category: str = "",
        variant_list: Optional[list[str]] = None,
    ) -> list[str]:
        """Generate multiple SKUs at once."""
        skus = []
        for i in range(count):
            var = variant_list[i] if variant_list and i < len(variant_list) else ""
            skus.append(self.generate(category=category, variant=var))
        return skus

    # ── SKU Parsing ─────────────────────────────────────

    def parse(self, sku: str) -> SKUInfo:
        """Parse a SKU string and extract components."""
        # Try our format: PREFIX-CAT-SEQ-VAR
        pattern = r"^([A-Z]{2,4})-([A-Z]{2})-(\d{3,6})(?:-([A-Z0-9]{1,6}))?$"
        m = re.match(pattern, sku.upper())
        if m:
            return SKUInfo(
                raw=sku,
                prefix=m.group(1),
                category_code=m.group(2),
                sequence=m.group(3),
                variant=m.group(4) or "",
                is_valid=True,
                format_name="crossborder-erp",
            )

        # Amazon-style ASIN-like
        if re.match(r"^B0[A-Z0-9]{8}$", sku.upper()):
            return SKUInfo(
                raw=sku, prefix="", category_code="", sequence=sku,
                variant="", is_valid=True, format_name="amazon-asin",
            )

        # Generic alphanumeric
        if re.match(r"^[A-Za-z0-9\-_]+$", sku) and len(sku) <= 100:
            return SKUInfo(
                raw=sku, prefix="", category_code="", sequence=sku,
                variant="", is_valid=True, format_name="generic",
            )

        return SKUInfo(
            raw=sku, prefix="", category_code="", sequence="",
            variant="", is_valid=False, format_name="unknown",
        )

    def validate_for_platform(self, sku: str, platform: str) -> bool:
        """Check if a SKU meets a platform's format requirements."""
        pattern = PLATFORM_FORMATS.get(platform.lower())
        if not pattern:
            return True  # Unknown platform, allow anything
        return bool(re.match(pattern, sku))

    # ── Cross-Platform Mapping ──────────────────────────

    def add_mapping(
        self,
        internal_sku: str,
        platform: str,
        platform_sku: str,
        marketplace: str = "",
        asin: str = "",
        fnsku: str = "",
    ) -> SKUMapping:
        """Map an internal SKU to a platform-specific SKU."""
        key = f"{platform.lower()}:{platform_sku}"
        if key in self._reverse:
            existing = self._reverse[key]
            if existing != internal_sku:
                raise ValueError(
                    f"Platform SKU '{platform_sku}' on {platform} already mapped to '{existing}'"
                )

        mapping = SKUMapping(
            internal_sku=internal_sku,
            platform=platform.lower(),
            platform_sku=platform_sku,
            marketplace=marketplace,
            asin=asin,
            fnsku=fnsku,
        )

        if internal_sku not in self._mappings:
            self._mappings[internal_sku] = []
        self._mappings[internal_sku].append(mapping)
        self._reverse[key] = internal_sku
        return mapping

    def get_mappings(self, internal_sku: str) -> list[SKUMapping]:
        """Get all platform mappings for an internal SKU."""
        return self._mappings.get(internal_sku, [])

    def resolve(self, platform_sku: str, platform: str) -> Optional[str]:
        """Resolve a platform SKU back to the internal SKU."""
        key = f"{platform.lower()}:{platform_sku}"
        return self._reverse.get(key)

    def get_platform_sku(self, internal_sku: str, platform: str) -> Optional[str]:
        """Get the platform-specific SKU for an internal SKU."""
        for m in self._mappings.get(internal_sku, []):
            if m.platform == platform.lower():
                return m.platform_sku
        return None

    # ── Collision Detection ─────────────────────────────

    def check_collisions(self, skus: list[str]) -> list[tuple[str, str]]:
        """Find SKU pairs that are too similar (edit distance ≤ 2)."""
        collisions = []
        normalized = [(s, s.upper().replace("-", "").replace("_", "")) for s in skus]
        for i in range(len(normalized)):
            for j in range(i + 1, len(normalized)):
                if self._edit_distance(normalized[i][1], normalized[j][1]) <= 2:
                    collisions.append((skus[i], skus[j]))
        return collisions

    def find_duplicates(self, skus: list[str]) -> dict[str, list[int]]:
        """Find exact duplicate SKUs and their positions."""
        seen: dict[str, list[int]] = {}
        for i, sku in enumerate(skus):
            key = sku.strip().upper()
            if key not in seen:
                seen[key] = []
            seen[key].append(i)
        return {k: v for k, v in seen.items() if len(v) > 1}

    # ── SKU Hash (for dedup across systems) ─────────────

    @staticmethod
    def sku_hash(sku: str) -> str:
        """Generate a deterministic short hash for a SKU (useful for dedup)."""
        return hashlib.sha256(sku.strip().upper().encode()).hexdigest()[:12]

    # ── Export ──────────────────────────────────────────

    def export_mappings(self) -> list[dict]:
        """Export all mappings as dicts."""
        result = []
        for mappings in self._mappings.values():
            for m in mappings:
                result.append({
                    "internal_sku": m.internal_sku,
                    "platform": m.platform,
                    "platform_sku": m.platform_sku,
                    "marketplace": m.marketplace,
                    "asin": m.asin,
                    "fnsku": m.fnsku,
                    "created_at": m.created_at.isoformat(),
                })
        return result

    def import_mappings(self, data: list[dict]) -> int:
        """Import mappings from dicts, returns count imported."""
        count = 0
        for d in data:
            try:
                self.add_mapping(
                    internal_sku=d["internal_sku"],
                    platform=d["platform"],
                    platform_sku=d["platform_sku"],
                    marketplace=d.get("marketplace", ""),
                    asin=d.get("asin", ""),
                    fnsku=d.get("fnsku", ""),
                )
                count += 1
            except (ValueError, KeyError):
                continue
        return count

    # ── Stats ───────────────────────────────────────────

    def stats(self) -> dict:
        """Return mapping statistics."""
        platform_counts: dict[str, int] = {}
        for mappings in self._mappings.values():
            for m in mappings:
                platform_counts[m.platform] = platform_counts.get(m.platform, 0) + 1

        return {
            "total_internal_skus": len(self._mappings),
            "total_mappings": sum(len(v) for v in self._mappings.values()),
            "platforms": platform_counts,
        }

    # ── Private ─────────────────────────────────────────

    @staticmethod
    def _edit_distance(a: str, b: str) -> int:
        """Levenshtein edit distance."""
        if len(a) < len(b):
            return SKUManager._edit_distance(b, a)
        if len(b) == 0:
            return len(a)
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a):
            curr = [i + 1]
            for j, cb in enumerate(b):
                cost = 0 if ca == cb else 1
                curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
            prev = curr
        return prev[len(b)]
