import json
import random
import string
import time
from itertools import product
from pathlib import Path
import httpx
import logging

from solver.paths import DATA_DIR
from models import get_default_model_name

logger = logging.getLogger(__name__)

DEFAULT_PLANNING_HORIZON = 5

CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_FILE = CACHE_DIR / "http_cache.json"
CACHE_EXPIRATION = 300

def load_settings():
    comp_path = DATA_DIR / "comprehensive_settings.json"
    user_path = DATA_DIR / "user_settings.json"
    
    # Write default configs if they do not exist
    if not comp_path.exists():
        comp_path.write_text(json.dumps({
            "decay_base": 0.9,
            "ft_value": 1.5,
            "vcap_weight": 0.1,
            "bench_weights": {"0": 0.03, "1": 0.21, "2": 0.06, "3": 0.002},
            "itb_value": 0.08,
            "itb_loss_per_transfer": 0.05,
            "ft_use_penalty": 0.2,
            "no_transfer_by_position": [],
            "hit_cost": 4,
            "weekly_hit_limit": 1
        }, indent=2))
        
    if not user_path.exists():
        user_path.write_text(json.dumps({
            "horizon": DEFAULT_PLANNING_HORIZON,
            "decay_base": 0.85,
            "datasource": get_default_model_name(),
            "team_data": "json",
            "team_id": None,
            "banned": [],
            "locked": [],
            "use_wc": [],
            "use_bb": [],
            "use_fh": [],
            "use_tc": [],
            "verbose": True
        }, indent=2))

    with open(comp_path) as f:
        options = json.load(f)
    with open(user_path) as f:
        options = {**options, **json.load(f)}

    return options

def get_random_id(n):
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(n))

def xmin_to_prob(xmin, sub_on=0.5, sub_off=0.3):
    start = min(max((xmin - 25 * sub_on) / (90 * (1 - sub_off) + 65 * sub_off - 25 * sub_on), 0.001), 0.999)
    return start + (1 - start) * sub_on

def get_dict_combinations(my_dict):
    keys = my_dict.keys()
    for key in keys:
        if my_dict[key] is None or len(my_dict[key]) == 0:
            my_dict[key] = [None]
    all_combs = [dict(zip(my_dict.keys(), values, strict=False)) for values in product(*my_dict.values())]
    feasible_combs = []
    for comb in all_combs:
        c_values = [i for i in comb.values() if i is not None]
        if len(c_values) == len(set(c_values)):
            feasible_combs.append({k: [v] for k, v in comb.items() if v is not None})
    return feasible_combs

def load_config_files(config_paths):
    options = {}
    for path_str in config_paths.split(";"):
        path = Path(path_str)
        if path.exists():
            with open(path) as f:
                options = {**options, **json.load(f)}
    return options

def cached_request(url: str) -> dict:
    """Helper mock cache request used by the solver."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache = {}
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
        except Exception:
            pass
            
    current_time = time.time()
    if url in cache:
        cached_data = cache[url]
        if current_time - cached_data["timestamp"] < CACHE_EXPIRATION:
            return cached_data["data"]
            
    # Make external call
    logger.info(f"FPL Solver requesting URL: {url}")
    r = httpx.get(url, timeout=15.0)
    r.raise_for_status()
    data = r.json()
    
    cache[url] = {
        "timestamp": current_time,
        "data": data
    }
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception:
        pass
        
    return data


def load_solver_static(options: dict) -> tuple[dict, list]:
    """Return bootstrap-static and fixtures. Injected options skip live HTTP."""
    bootstrap = options.get("fpl_bootstrap")
    fixtures = options.get("fpl_fixtures")
    if bootstrap is None:
        bootstrap = cached_request("https://fantasy.premierleague.com/api/bootstrap-static/")
    if fixtures is None:
        fixtures = cached_request("https://fantasy.premierleague.com/api/fixtures/")
    return bootstrap, fixtures
