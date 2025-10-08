from docker.errors import NotFound
from pathlib import Path
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import crossplane
import docker
import json
import logging
import os
import re
import threading
import time
import yaml

client = docker.from_env()

# ===================================================
#                     LOGGER
# ===================================================

LEVEL_COLORS = {
    'DEBUG':    "\033[36mDEBUG", # Cyan
    'INFO':     "\033[34mINFO", # Blue
    'WARNING':  "\033[33mWARN", # Orange
    'ERROR':    "\033[31mERRO", # Red
    'CRITICAL': "\033[41mCRIT", # Extra Red
}
RESET = "\033[0m"

class LevelColorFormatter(logging.Formatter):
    def format(self, record):
        levelname_color = LEVEL_COLORS.get(record.levelname, "")
        record.levelname = f"{levelname_color}{RESET}"
        return super().format(record)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

for handler in logging.getLogger().handlers:
    handler.setFormatter(LevelColorFormatter(handler.formatter._fmt, datefmt="%Y-%m-%d %H:%M:%S"))

logger = logging.getLogger(__name__)

logger.info("""
      _,--------._
      `:._______,:)
        \\..::ooOo/
    ___  )::ooOo(  ___     ██████╗ ██╗      █████╗ ████████╗ ██████╗
   /,-.`/..::ooOo.',-.\\    ██╔══██╗██║     ██╔══██╗╚══██╔══╝██╔═══██╗
  ((  ,'..::ooOoOOb.  ))   ██████╔╝██║     ███████║   ██║   ██║   ██║
   \\`/ . ..::ooOoOO8'/     ██╔═══╝ ██║     ██╔══██║   ██║   ██║   ██║
    Y . ..::ooOoOO888b.    ██║     ███████╗██║  ██║   ██║   ╚██████╔╝
   (   . ..::ooOoOO888b    ╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝    ╚═════╝
    \\ . ..::ooOoOO888F
     `.. ..::ooOoOOP'
       `._..ooOO8P'
         `------'
""")
# ===================================================
#                  CONFIGURATION
# ===================================================
ASSETS_PATH   = Path("/www/assets")
SELFHST_ICONS = ASSETS_PATH / Path("selfhst-icons/png")
CUSTOM_ICONS  = ASSETS_PATH / Path("custom")

HOSTNAME = os.getenv("HOSTNAME")
if not HOSTNAME:
    logger.error("HOSTNAME must be provided")
    exit(1)

AUTOMATIC_ICONS = os.getenv("AUTOMATIC_ICONS", "True").lower() in ("1", "true", "yes")
CATEGORY_ICONS  = os.getenv("CATEGORY_ICONS")

if CATEGORY_ICONS:
    CATEGORY_ICONS_DICT = dict(
        (k.strip(), v.strip())
        for k, v in (item.split("=", 1) for item in CATEGORY_ICONS.split(",") if "=" in item)
    )
else:
    logger.warning("CATEGORY_ICONS not provided. Column order will be random")
    CATEGORY_ICONS_DICT = {}

NGINX_CONFIG_FOLDER = Path(os.getenv("NGINX_CONFIG_FOLDER", "/etc/nginx"))

NGINX_CONFIG_PATH = NGINX_CONFIG_FOLDER / "nginx.conf"
SITES_ENABLED_DIR = NGINX_CONFIG_FOLDER / "sites-enabled"

# Create base config from env
configuration = {
    'title':    os.getenv("TITLE", "Demo dashboard"),
    'subtitle': os.getenv("SUBTITLE", "Plato"),
    'logo':     os.getenv("LOGO", "logo.png"),
    'columns':  os.getenv("COLUMNS", "auto"),
    'header':   os.getenv("HEADER", True),
    'footer':   os.getenv("FOOTER", False),
    'theme': "default",
    'colors': {
        'light': {
            'highlight-primary':   os.getenv("COLORS_LIGHT_HIGHLIGHT-PRIMARY",'#3367d6'),
            'highlight-secondary': os.getenv("COLORS_LIGHT_HIGHLIGHT-SECONDARY", '#4285f4'),
            'highlight-hover':     os.getenv("COLORS_LIGHT_HIGHLIGHT-HOVER", '#5a95f5'),
            'background':          os.getenv("COLORS_LIGHT_BACKGROUND", '#f5f5f5'),
            'card-background':     os.getenv("COLORS_LIGHT_CARD-BACKGROUND", '#ffffff'),
            'text':                os.getenv("COLORS_LIGHT_TEXT", '#363636'),
            'text-header':         os.getenv("COLORS_LIGHT_TEXT-HEADER", '#ffffff'),
            'text-title':          os.getenv("COLORS_LIGHT_TEXT-TITLE", '#303030'),
            'text-subtitle':       os.getenv("COLORS_LIGHT_TEXT-SUBTITLE", '#424242'),
            'card-shadow':         os.getenv("COLORS_LIGHT_CARD-SHADOW", 'rgba(0, 0, 0, 0.1)'),
            'link':                os.getenv("COLORS_LIGHT_LINK", '#3273dc'),
            'link-hover':          os.getenv("COLORS_LIGHT_LINK-HOVER", '#363636')
        },
        'dark': {
            'highlight-primary':   os.getenv("COLORS_DARK_HIGHLIGHT-PRIMARY", '#3367d6'),
            'highlight-secondary': os.getenv("COLORS_DARK_HIGHLIGHT-SECONDARY", '#4285f4'),
            'highlight-hover':     os.getenv("COLORS_DARK_HIGHLIGHT-HOVER", '#5a95f5'),
            'background':          os.getenv("COLORS_DARK_BACKGROUND", '#131313'),
            'card-background':     os.getenv("COLORS_DARK_CARD-BACKGROUND", '#2b2b2b'),
            'text':                os.getenv("COLORS_DARK_TEXT", '#eaeaea'),
            'text-header':         os.getenv("COLORS_DARK_TEXT-HEADER", '#ffffff'),
            'text-title':          os.getenv("COLORS_DARK_TEXT-TITLE", '#fafafa'),
            'text-subtitle':       os.getenv("COLORS_DARK_TEXT-SUBTITLE", '#f5f5f5'),
            'card-shadow':         os.getenv("COLORS_DARK_CARD-SHADOW", 'rgba(0, 0, 0, 0.4)'),
            'link':                os.getenv("COLORS_DARK_LINK", '#3273dc'),
            'link-hover':          os.getenv("COLORS_DARK_LINK-HOVER", '#ffdd57')
        }
    },
    'services': []
}

# ===================================================
#                  MANIFEST
# ===================================================

manifest = {
    "name":       os.getenv("PWA_NAME", "Plato Dashboard"),
    "short_name": os.getenv("PWA_SHORT_NAME", "Plato"),
    "start_url":"../",
    "display":"standalone",
    "background_color": os.getenv("PWA_BACKGROUND_COLOR", "#ffffff"),
    "lang":"en",
    "scope":"../",
    "description": os.getenv("PWA_DESCRIPTION", "Plato Server Dashboard"),
    "theme_color": os.getenv("PWA_THEME_COLOR", "#3367D6"),
    "icons":[
        {"src":"./icons/pwa-192x192.png","sizes":"192x192","type":"image/png"},
        {"src":"./icons/pwa-512x512.png","sizes":"512x512","type":"image/png"}
    ]
}

manifest_path = ASSETS_PATH / Path("manifest.json")

with manifest_path.open("w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=4)

logger.debug("Manifest content:\n%s", json.dumps(manifest, indent=4))
logger.info(f"Manifest generated on {manifest_path}")

# ===================================================
#                  CONTAINER UTILS
# ===================================================

def safe_list_containers(all=True):
    for c in client.api.containers(all=all):
        cid = c["Id"]
        try:
            yield client.containers.get(cid)
        except NotFound:
            # Container vanished between list and inspect
            continue

# ===================================================
#                  NGINX PARSING
# ===================================================

_nginx_config = None
_lock = threading.Lock()
_nginx_cooldown = 5
_latest_nginx_reload = 0

def get_nginx_port_url_map(nginx_conf=NGINX_CONFIG_PATH):
    logger.info("Parsing Nginx Config")

    valid_hostname = re.compile(r'^[a-zA-Z0-9.-]+$')

    parsed = crossplane.parse(nginx_conf)
    port_url_map = {}

    for config in parsed.get("config", []):
        for directive in config.get("parsed", []):
            if directive.get("directive") == "server":
                server_block = directive
                server_names = []
                scheme = "http"

                for directive in server_block.get("block", []):
                    if directive["directive"] == "listen":
                        args = directive.get("args", [])
                        if any("443" in arg or arg == "ssl" for arg in args):
                            scheme = "https"

                    elif directive["directive"] == "server_name":
                        for name in directive.get("args", []):
                            name = name.strip()
                            if name != "_" and valid_hostname.match(name):
                                server_names.append(name)

                if not server_names:
                    return  # skip blocks without valid hostnames

                # Only process location blocks
                for directive in server_block.get("block", []):
                    if directive.get("directive") == "location":
                        location_path = directive.get("args", ["/"])[0]
                        for subdir in directive.get("block", []):
                            if subdir.get("directive") == "proxy_pass":
                                proxy_target = subdir.get("args", [None])[0]
                                if proxy_target:
                                    match = re.search(r":(\d+)", proxy_target)
                                    if match:
                                        internal_port = match.group(1)
                                        for name in server_names:
                                            url = f"{scheme}://{name}{location_path.rstrip('/')}"
                                            url = url.rstrip("=")
                                            if url == f"{scheme}://{name}":
                                                url = url.rstrip("/")
                                            port_url_map.setdefault(internal_port, set()).add(url)

    # Convert sets to sorted lists
    port_url_map = {port: sorted(urls) for port, urls in port_url_map.items()}

    if port_url_map:
        log_url_pairs = ''
        for port in port_url_map:
            log_url_pairs += f"  {port} -> {port_url_map[port]}\n"
        logger.debug(log_url_pairs)
    else:
        logger.warning("Nginx config not found")

    return port_url_map


def _reload_nginx_config():
    global _nginx_config, _latest_nginx_reload
    now = time.time()
    with _lock:
        _latest_nginx_reload = now
    try:
        new_config = get_nginx_port_url_map()
        with _lock:
            _nginx_config = new_config
    except Exception as e:
        logger.error(f"Failed to reload nginx config: {e}")

def get_nginx_config():
    with _lock:
        return _nginx_config


class NginxConfigWatcher(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path == NGINX_CONFIG_PATH or path.parent == SITES_ENABLED_DIR:
            now = time.time()
            if now - _latest_nginx_reload > _nginx_cooldown:
                logger.info(f"Detected change in Nginx config: {path}")
                _reload_nginx_config()

def start_nginx_watcher():

    _reload_nginx_config()

    event_handler = NginxConfigWatcher()
    observer = Observer()
    if NGINX_CONFIG_PATH.parent.exists():
        observer.schedule(event_handler, NGINX_CONFIG_PATH.parent, recursive=False)
    if SITES_ENABLED_DIR.exists():
        observer.schedule(event_handler, SITES_ENABLED_DIR, recursive=True)

    observer.daemon = True
    observer.start()
    return observer

# ===================================================
#                  GENERATE CONFIG
# ===================================================

def get_ui_port(container, name: str) -> str:
    unique_ports = set()

    for _, host_mappings in container.attrs['NetworkSettings']['Ports'].items():
        if host_mappings:
            for mapping in host_mappings:
                unique_ports.add(mapping['HostPort'])

    if len(unique_ports) == 0:
        logger.error(f"No port found for {name}\nDisanbiguation needed with com.plato.ui-port")
        exit(1)

    if len(unique_ports) > 1:
        logger.error(f"More than one port found for {name}\nDisanbiguation needed with com.plato.ui-port")
        exit(1)

    return next(iter(unique_ports))


def generate_homer_config():
    logger.info("🔧 Generating Homer dashboard configuration...")

    nginx_url_pairs = get_nginx_config()

    categories = {}

    for container in safe_list_containers():

        # skip stopped/paused containers
        if container.status != "running":
            continue

        labels = container.labels

        category = labels.get("com.plato.category")

        if not category:
            continue

        container_name = container.name.lower()

        name     = labels.get("com.plato.name", container_name.title())
        url      = labels.get("com.plato.url")
        ui_port  = labels.get("com.plato.ui-port")

        if not url:
            if not ui_port:
                ui_port = get_ui_port(container, name)

            if ui_port:
                url = [f"http://{HOSTNAME}:{ui_port}"]
            if nginx_url_pairs:
                url = nginx_url_pairs.get(ui_port, url)

        if not url:
            logger.error(f"Could not create URL for {name}")
            exit(1)


        try:
            importance = float(labels.get("com.plato.importance", 0))
        except (TypeError, ValueError):
            logger.error(f"com.plato.importance must be a float value for {name}")
            exit(1)

        result = {
            "name"       : name,
            "url"        : url[0],
            "importance" : importance,
            "subtitle"   : labels.get("com.plato.subtitle"),
            "tag"        : labels.get("com.plato.tag"),
            "tagstyle"   : labels.get("com.plato.tagstyle"),
            "keywords"   : labels.get("com.plato.keywords"),
            "icon"       : labels.get("com.plato.icon")
        }

        custom_logo = labels.get("com.plato.custom-logo")

        if custom_logo:
            result['logo'] = custom_logo

        elif AUTOMATIC_ICONS:
            search_icon = container_name

            selfhst_icon = labels.get("com.plato.selfhst-icon")

            if selfhst_icon:
                search_icon = selfhst_icon

            selfhst_icon_path = SELFHST_ICONS / f"{search_icon.replace("_","-").replace(" ","-")}.png"

            custom_icon_path = CUSTOM_ICONS / f"{search_icon}.png"

            if os.path.exists(custom_icon_path):
                result['logo'] = str(Path(*custom_icon_path.parts[2:]))
                logger.debug(f"Found Custom icon for {name}: {search_icon}")
            elif os.path.exists(selfhst_icon_path):
                result['logo'] = str(Path(*selfhst_icon_path.parts[2:]))
                logger.debug(f"Found selfh.st icon for {name}: {search_icon}.png")
            else:
                logger.warning(f"Icon not found for {name}: {search_icon}.png")
                if selfhst_icon:
                    logger.error("Provided logo is invalid: com.plato.selfhst-icon")
                    exit(1)

        categories.setdefault(category, []).append(result)

    # Sort each column
    for category in categories:
        categories[category].sort(key=lambda x: x["importance"], reverse=True)


    configuration['services'] = sorted(
        [
            {
                "name": category,
                "icon": CATEGORY_ICONS_DICT.get(category),
                "items": items
            }
            for category, items in categories.items()
        ],
        key=lambda x: list(CATEGORY_ICONS_DICT.keys()).index(x["name"])
            if x["name"] in CATEGORY_ICONS_DICT
            else len(CATEGORY_ICONS_DICT)
    )

    logger.debug(yaml.dump(configuration, sort_keys=False, default_flow_style=False))

    with open(ASSETS_PATH / Path("config.yml"), "w") as f:
        yaml.dump(configuration, f, default_flow_style=False, sort_keys=False)

if __name__ == "__main__":

    start_nginx_watcher()

    generate_homer_config()

    for event in client.events(decode=True, filters={"type": "container"}):
         # Skip exec-related events
        action = event["Action"]
        if action.startswith("exec_"):
            continue

        logger.debug("Container event:", event["Action"], "on", event["Actor"]["Attributes"].get("name"))

        generate_homer_config()
