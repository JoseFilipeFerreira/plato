import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Dict, Tuple, List, Generator, Set
from urllib.parse import urljoin

import crossplane
import docker
from docker.errors import NotFound
from docker.models.containers import Container
import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

client = docker.from_env()

# ===================================================
#                     LOGGER
# ===================================================

LEVEL_COLORS = {
    'DEBUG':    "\033[36mDEBUG", # Cyan
    'INFO':     "\033[34mINFO",  # Blue
    'WARNING':  "\033[33mWARN",  # Orange
    'ERROR':    "\033[31mERROR", # Red
    'CRITICAL': "\033[41mCRIT",  # Extra Red
}
RESET = "\033[0m"


class LevelColorFormatter(logging.Formatter):
    def format(self, record):
        levelname_color = LEVEL_COLORS.get(record.levelname, "")
        record.levelname = f"{levelname_color}{RESET}"
        return super().format(record)

log_level = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Reduce logger polution
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("docker").setLevel(logging.WARNING)

for handler in logging.getLogger().handlers:
    handler.setFormatter(LevelColorFormatter(handler.formatter._fmt, datefmt="%Y-%m-%d %H:%M:%S"))


logger = logging.getLogger(__name__)

# ===================================================
#                  CONFIGURATION
# ===================================================
ASSETS_PATH   = Path("/www/assets")
SELFHST_ICONS = ASSETS_PATH / Path("selfhst-icons/png")
CUSTOM_ICONS  = ASSETS_PATH / Path("custom")

NGINX_CONFIG_FOLDER = Path("/etc/nginx")
NGINX_CONFIG_PATH = NGINX_CONFIG_FOLDER / "nginx.conf"
SITES_ENABLED_DIR = NGINX_CONFIG_FOLDER / "sites-enabled"

HOSTNAME = os.getenv("HOSTNAME")

AUTOMATIC_ICONS = os.getenv("AUTOMATIC_ICONS", "True").lower() in ("1", "true", "yes")
CATEGORY_ICONS  = os.getenv("CATEGORY_ICONS")

CATEGORY_ICONS_DICT: Dict[str, str] = {}


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

MANIFEST_PATH = ASSETS_PATH / Path("manifest.json")

def write_manifest():
    with MANIFEST_PATH.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)

    logger.debug("Manifest content:\n%s", json.dumps(manifest, indent=4))
    logger.info(f"Manifest generated on {MANIFEST_PATH}")

# ===================================================
#                  CONTAINER UTILS
# ===================================================

def safe_list_containers(all=True) -> Generator[Container, None, None]:
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

_nginx_config = {}
_lock = threading.Lock()
_nginx_cooldown = 5
_latest_nginx_reload = 0

def get_nginx_port_url_map(nginx_conf=NGINX_CONFIG_PATH) -> Dict[int, List[str]]:
    logger.info("Parsing Nginx Config")

    valid_hostname = re.compile(r'^[a-zA-Z0-9.-]+$')

    parsed = crossplane.parse(nginx_conf)
    port_url_map: Dict[int, Set[str]] = {}

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
                    continue  # skip blocks without valid hostnames

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
                                            port_url_map.setdefault(int(internal_port), set()).add(url)

    # Convert sets to sorted lists
    ret = {port: sorted(urls) for port, urls in port_url_map.items()}

    if ret:
        log_url_pairs = ''
        for port in ret:
            log_url_pairs += f"  {port} -> {ret[port]}\n"
        logger.debug(log_url_pairs)
    else:
        logger.warning("Nginx config not found")

    return ret


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

def get_nginx_config() -> Dict[int, List[str]]:
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
        observer.schedule(event_handler, str(NGINX_CONFIG_PATH.parent), recursive=False)
    if SITES_ENABLED_DIR.exists():
        observer.schedule(event_handler, str(SITES_ENABLED_DIR), recursive=True)

    observer.daemon = True
    observer.start()
    return observer

# ===================================================
#                  URL Finder
# ===================================================

COMMON_HTTP_PORTS = {
    80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
    3000, 3001,
    5000, 5050, 5080,
    7000, 7001,
    8000, 8001, 8080, 8081, 8090, 8096, 8181, 8200, 8888, 8989,
    9000, 9090, 9117, 9999
}

COMMON_HTTPS_PORTS = {
    443, 444, 8443, 9443, 10443, 12443, 14443
}

KNOWN_PORTS = {
    "jellyfin": 8096,
    "qbittorrent": 8080,
    "home-assistant": 8123,
    "esphome": 6052
}

def get_local_url(container, name:str ) -> Tuple[str, int]:

    # Find used TCP ports
    unique_ports = set()
    for port_proto, host_mappings in container.attrs['NetworkSettings']['Ports'].items():
        internal_port, proto = port_proto.split('/')
        if proto == "tcp" and host_mappings:
            for mapping in host_mappings:
                unique_ports.add((int(internal_port), int(mapping['HostPort'])))

    logger.debug(f"Ports found: {unique_ports}")

    if len(unique_ports) == 1:
        # Use the only exposed port as UI port
        internal_port, external_port = next(iter(unique_ports))

        protocol = "http"
        if internal_port in COMMON_HTTPS_PORTS:
            protocol = "https"

        return f"{protocol}://{HOSTNAME}:{external_port}", external_port

    elif len(unique_ports) > 1:
        # Check if any of the found ports are common HTTP/HTTPS port
        for internal_port, external_port in unique_ports:


            protocol = None

            if internal_port in COMMON_HTTP_PORTS:
                protocol = "http"
            elif internal_port in COMMON_HTTPS_PORTS:
                protocol = "https"

            if protocol is not None:
                logger.debug(f"Found common {protocol} port {internal_port} -> {external_port}")
                return f"{protocol}://{HOSTNAME}:{external_port}", external_port

        logger.error(f"More than one UI port found for {name}\nDisanbiguation needed with com.plato.ui-port")
        exit(1)


    else:
        # If no port is exposed, search known ports
        image_name = container.image.tags[0] if container.image.tags else ""
        container_name = container.name.lower()

        for service, port in KNOWN_PORTS.items():
            if service in image_name or service in container_name:
                logger.debug(f"Found known port for service {service}: {port}")
                return f"http://{HOSTNAME}:{port}", port

        logger.error(f"No port found for {name}\nPort must be provided with com.plato.ui-port")
        exit(1)

# ===================================================
#                  GENERATE CONFIG
# ===================================================

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


        name        = labels.get("com.plato.name", container_name.title())
        url         = labels.get("com.plato.url")
        endpoint    = labels.get("com.plato.endpoint")
        ui_port     = labels.get("com.plato.ui-port")

        force_https = labels.get("com.plato.force-https", "false").lower() in ("1", "true", "yes")

        logger.debug(f"> Processing container {name}")

        # caddy-docker-proxy support
        caddy_url = labels.get("caddy")
        if caddy_url:
            logger.debug(f"Caddy found: {caddy_url}")
            url = "https://" + caddy_url

        if not url:
            if ui_port:
                url = f"http://{HOSTNAME}:{ui_port}"
            else:
                url, ui_port = get_local_url(container, name)

            if endpoint:
                url = urljoin(url.rstrip('/') + '/', endpoint)

            if nginx_url_pairs:
                external_urls = nginx_url_pairs.get(ui_port)
                if external_urls:
                    url = external_urls[0]
                    logger.debug(f"Found external url: {url}")

        if url and force_https:
            if "https" not in url:
                logger.debug(f"Force HTTPS on {url}")
                url = url.replace("http", "https")

        if not url:
            logger.error(f"Could not create URL for {name}")
            exit(1)

        try:
            importance = float(labels.get("com.plato.importance", 0))
        except (TypeError, ValueError):
            logger.error(f"com.plato.importance must be a float value for {name}")
            exit(1)

        result = {
            k: v
            for k, v in {
                "name"       : name,
                "url"        : url,
                "importance" : importance,
                "subtitle"   : labels.get("com.plato.subtitle"),
                "tag"        : labels.get("com.plato.tag"),
                "tagstyle"   : labels.get("com.plato.tagstyle"),
                "keywords"   : labels.get("com.plato.keywords"),
                "icon"       : labels.get("com.plato.icon")
            }.items()
            if v is not None
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
                logger.debug(f"Found Custom icon: {search_icon}")
            elif os.path.exists(selfhst_icon_path):
                result['logo'] = str(Path(*selfhst_icon_path.parts[2:]))
                logger.debug(f"Found selfh.st icon: {search_icon}.png")
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
    # Validate initial config
    if not HOSTNAME:
        logger.error("HOSTNAME must be provided")
        exit(1)

    if CATEGORY_ICONS:
        CATEGORY_ICONS_DICT = dict(
            (k.strip(), v.strip())
            for k, v in (item.split("=", 1) for item in CATEGORY_ICONS.split(",") if "=" in item)
        )
    else:
        logger.warning("CATEGORY_ICONS not provided. Column order will be random")

    write_manifest()

    start_nginx_watcher()

    generate_homer_config()

    for event in client.events(decode=True, filters={"type": "container"}):
         # Skip exec-related events
        action = event["Action"]
        if action.startswith("exec_"):
            continue

        logger.debug(f"Container event: {event["Action"]} on {event["Actor"]["Attributes"].get("name")}")

        generate_homer_config()
