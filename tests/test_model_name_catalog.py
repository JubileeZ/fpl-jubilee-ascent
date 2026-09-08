from pathlib import Path

from models import get_model, list_model_names
from models.selection import load_model_selection

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs" / "model_name.md"
README = ROOT / "README.md"


def test_list_model_names_matches_discovery() -> None:
    names = list_model_names()
    assert names == sorted(names)
    assert names
    for name in names:
        assert get_model(name).name == name


def test_model_name_catalog_lists_every_discovered_model() -> None:
    catalog = CATALOG.read_text(encoding="utf-8")
    missing = [name for name in list_model_names() if f"`{name}`" not in catalog]
    assert missing == [], f"docs/model_name.md missing {missing}"


def test_model_name_catalog_includes_champion() -> None:
    champion = load_model_selection().champion
    catalog = CATALOG.read_text(encoding="utf-8")
    assert f"`{champion}`" in catalog


def test_readme_cli_section_3_follows_availability_overrides() -> None:
    text = README.read_text(encoding="utf-8")
    overrides = text.index("`data/availability_overrides.csv`")
    section3 = text.index("### 3. Generate Transfer Plan")
    assert overrides < section3
