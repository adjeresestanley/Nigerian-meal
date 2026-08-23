"""Normalize static image filenames and matching template image references."""

from pathlib import Path
import re
from urllib.parse import quote, unquote


ROOT = Path(__file__).resolve().parent
IMAGE_DIR = ROOT / "static" / "images"
TEMPLATES_DIR = ROOT / "templates"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif"}
IMG_SRC_PATTERN = re.compile(
    r"(<img\b[^>]*\bsrc\s*=\s*)([\"'])(.*?)(\2)",
    re.IGNORECASE | re.DOTALL,
)


def normalized_name(filename: str) -> str:
    """Return a lowercase filename with spaces replaced by hyphens."""
    return filename.lower().replace(" ", "-")


def build_rename_map() -> dict[str, str]:
    """Build and validate old-to-new names before changing any files."""
    files = [
        path
        for path in IMAGE_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    rename_map = {path.name: normalized_name(path.name) for path in files}
    destinations = list(rename_map.values())

    if len(destinations) != len(set(destinations)):
        raise RuntimeError("Image filenames collide after normalization.")

    existing_names = {path.name for path in files}
    for old_name, new_name in rename_map.items():
        if new_name != old_name and new_name in existing_names:
            raise RuntimeError(
                f"Cannot rename {old_name!r}: destination {new_name!r} already exists."
            )

    return rename_map


def update_template_references(rename_map: dict[str, str]) -> int:
    """Update literal image filenames inside template img src attributes."""
    replacements = {
        variant.lower(): new_name
        for old_name, new_name in rename_map.items()
        for variant in {old_name, quote(old_name), unquote(old_name)}
        if variant != new_name
    }
    if not replacements:
        return 0

    pattern = re.compile(
        "|".join(re.escape(name) for name in sorted(replacements, key=len, reverse=True)),
        re.IGNORECASE,
    )
    changed_files = 0

    for template_path in TEMPLATES_DIR.rglob("*"):
        if not template_path.is_file():
            continue
        text = template_path.read_text(encoding="utf-8")

        def replace_src(match: re.Match[str]) -> str:
            prefix, quote_mark, src, closing_quote = match.groups()
            updated_src = pattern.sub(
                lambda filename: replacements[filename.group(0).lower()], src
            )
            if "recipe.image_url" in updated_src and "|lower" not in updated_src:
                updated_src = updated_src.replace(
                    "recipe.image_url",
                    "recipe.image_url|lower|replace(' ', '-')",
                )
            return prefix + quote_mark + updated_src + closing_quote

        updated_text = IMG_SRC_PATTERN.sub(replace_src, text)
        if updated_text != text:
            template_path.write_text(updated_text, encoding="utf-8")
            changed_files += 1

    return changed_files


def rename_images(rename_map: dict[str, str]) -> None:
    """Rename through temporary names so swaps cannot overwrite files."""
    temporary_names = {}
    for old_name, new_name in rename_map.items():
        if old_name == new_name:
            continue
        source = IMAGE_DIR / old_name
        temporary = IMAGE_DIR / f".__normalize_tmp__{old_name}"
        source.rename(temporary)
        temporary_names[temporary] = IMAGE_DIR / new_name

    for temporary, destination in temporary_names.items():
        temporary.rename(destination)


def main() -> None:
    rename_map = build_rename_map()
    changed_names = {
        old_name: new_name
        for old_name, new_name in rename_map.items()
        if old_name != new_name
    }

    if changed_names:
        print("Renaming images:")
        for old_name, new_name in changed_names.items():
            print(f"  {old_name} -> {new_name}")
        rename_images(rename_map)
    else:
        print("All image filenames are already normalized.")

    changed_templates = update_template_references(rename_map)
    print(f"Updated {changed_templates} template file(s).")


if __name__ == "__main__":
    main()
