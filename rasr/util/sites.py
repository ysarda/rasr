"""
Radar site management - loads from YAML configuration
"""

import yaml
from pathlib import Path


def load_radar_sites(config_path="radar_sites.yaml"):
    """Load radar sites from YAML configuration."""
    path = Path(config_path)
    if not path.exists():
        # Fallback to hardcoded list if config doesn't exist
        return _get_default_sites()

    with open(path, 'r') as f:
        config = yaml.safe_load(f)

    return config.get('active_sites', [])


def _get_default_sites():
    """Default radar sites list (fallback)."""
    return [
        "KATX", "KABR", "KENX", "KABX", "KAMA", "PAHG", "PGUA", "KFFC",
        "KBBX", "PABC", "KBLX", "KBGM", "PACG", "KBMX", "KBIS", "KFCX",
        "KCBX", "KBOX", "KBRO", "KBUF", "KCXX", "RKSG", "KFDX", "KCBW",
        "KICX", "KGRK", "KCLX", "KRLX", "KCYS", "KLOT", "KILN", "KCLE",
        "KCAE", "KGWX", "KCRP", "KFTG", "KDMX", "KDTX", "KDDC", "KDOX",
        "KDLH", "KDYX", "KEYX", "KEPZ", "KLRX", "KBHX", "KVWX", "PAPD",
        "KFSX", "KSRX", "KFDR", "KHPX", "KPOE", "KEOX", "KFWS", "KAPX",
        "KGGW", "KGLD", "KMVX", "KGJX", "KGRR", "KTFX", "KGRB", "KGSP",
        "KUEX", "KHDX", "KHGX", "KHTX", "KIND", "KJKL", "KDGX", "KJAX",
        "RODN", "PHKM", "KEAX", "KBYX", "PAKC", "KMRX", "RKJK", "KARX",
        "KLCH", "KLGX", "KESX", "KDFX", "KILX", "KLZK", "KVTX", "KLVX",
        "KLBB", "KMQT", "KMXX", "KMAX", "KMLB", "KNQA", "KAMX", "PAIH",
        "KMAF", "KMKX", "KMPX", "KMBX", "KMSX", "KMOB", "PHMO", "KTYX",
        "KVAX", "KMHX", "KOHX", "KLIX", "KOKX", "PAEC", "KLNX", "KIWX",
        "KEVX", "KTLX", "KOAX", "KPAH", "KPDT", "KDIX", "KIWA", "KPBZ",
        "KSFX", "KGYX", "KRTX", "KPUX", "KDVN", "KRAX", "KUDX", "KRGX",
        "KRIW", "KJGX", "KDAX", "KMTX", "KSJT", "KEWX", "KNKX", "KMUX",
        "KHNX", "TJUA", "KSOX", "KSHV", "KFSD", "PHKI", "PHWA", "KOTX",
        "KSGF", "KLSX", "KCCX", "KLWX", "KTLH", "KTBW", "KTWX", "KEMX",
        "KINX", "KVNX", "KVBX", "KAKQ", "KICT", "KLTX", "KYUX"
    ]


# Keep backward compatibility
radar_sites = [load_radar_sites()]
