import json
import logging
import os
from pathlib import Path
from typing import Dict, Tuple, List, Generator, Set
from urllib.parse import urljoin

import docker
from docker.errors import NotFound
from docker.models.containers import Container
import yaml

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

HOSTNAME = os.getenv("HOSTNAME")

AUTOMATIC_ICONS = os.getenv("AUTOMATIC_ICONS", "True").lower() in ("1", "true", "yes")
CATEGORY_ICONS  = os.getenv("CATEGORY_ICONS")

CATEGORY_ICONS_DICT: Dict[str, str] = {}

# Load Base theme
THEMES_PATH = Path("/www/themes")
THEME = os.getenv("THEME", "default").lower()
THEME_PATH = THEMES_PATH / Path(f"{THEME}.json")
if not THEME_PATH.exists():
    logger.error(f"Theme {THEME} does not exist")
    exit(1)

with open(THEME_PATH, "r") as f:
    colors = json.load(f)

# Helper to get env or fallback to theme
def get_color(env_var, theme_section, key):
    return os.getenv(env_var, colors.get(theme_section, {}).get(key))


# Create base config from env
configuration = {
    'title':    os.getenv("TITLE", "Demo dashboard"),
    'subtitle': os.getenv("SUBTITLE", "Plato"),
    'logo':     os.getenv("LOGO", "logo.png"),
    'columns':  os.getenv("COLUMNS", "auto"),
    'header':   os.getenv("HEADER", True),
    'footer':   os.getenv("FOOTER", False),
    'theme': "default",
    "colors": {
        "light": {
            "highlight-primary":   get_color("LIGHT_HIGHLIGHT-PRIMARY", "light", "highlight-primary"),
            "highlight-secondary": get_color("LIGHT_HIGHLIGHT-SECONDARY", "light", "highlight-secondary"),
            "highlight-hover":     get_color("LIGHT_HIGHLIGHT-HOVER", "light", "highlight-hover"),
            "background":          get_color("LIGHT_BACKGROUND", "light", "background"),
            "card-background":     get_color("LIGHT_CARD-BACKGROUND", "light", "card-background"),
            "text":                get_color("LIGHT_TEXT", "light", "text"),
            "text-header":         get_color("LIGHT_TEXT-HEADER", "light", "text-header"),
            "text-title":          get_color("LIGHT_TEXT-TITLE", "light", "text-title"),
            "text-subtitle":       get_color("LIGHT_TEXT-SUBTITLE", "light", "text-subtitle"),
            "card-shadow":         get_color("LIGHT_CARD-SHADOW", "light", "card-shadow"),
            "link":                get_color("LIGHT_LINK", "light", "link"),
            "link-hover":          get_color("LIGHT_LINK-HOVER", "light", "link-hover")
        },
        "dark": {
            "highlight-primary":   get_color("DARK_HIGHLIGHT-PRIMARY", "dark", "highlight-primary"),
            "highlight-secondary": get_color("DARK_HIGHLIGHT-SECONDARY", "dark", "highlight-secondary"),
            "highlight-hover":     get_color("DARK_HIGHLIGHT-HOVER", "dark", "highlight-hover"),
            "background":          get_color("DARK_BACKGROUND", "dark", "background"),
            "card-background":     get_color("DARK_CARD-BACKGROUND", "dark", "card-background"),
            "text":                get_color("DARK_TEXT", "dark", "text"),
            "text-header":         get_color("DARK_TEXT-HEADER", "dark", "text-header"),
            "text-title":          get_color("DARK_TEXT-TITLE", "dark", "text-title"),
            "text-subtitle":       get_color("DARK_TEXT-SUBTITLE", "dark", "text-subtitle"),
            "card-shadow":         get_color("DARK_CARD-SHADOW", "dark", "card-shadow"),
            "link":                get_color("DARK_LINK", "dark", "link"),
            "link-hover":          get_color("DARK_LINK-HOVER", "dark", "link-hover")
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
    "jellyfin"      : 8096,
    "qbittorrent"   : 8080,
    "home-assistant": 8123,
    "esphome"       : 6052
}

def get_local_url(container, name:str ) -> Tuple[str, int]:

    # Find used TCP ports
    ports = set()
    for port_proto, host_mappings in container.attrs['NetworkSettings']['Ports'].items():
        internal_port, proto = port_proto.split('/')
        if proto == "tcp" and host_mappings:
            for mapping in host_mappings:
                ports.add((int(internal_port), int(mapping['HostPort'])))

    logger.debug(f"Ports found: {ports}")

    # If only one port use it as UI port
    if len(ports) == 1:
        internal_port, external_port = next(iter(ports))

        protocol = "http"
        if internal_port in COMMON_HTTPS_PORTS:
            protocol = "https"

        return f"{protocol}://{HOSTNAME}:{external_port}", external_port

    # If more than one port find if any is a common HTTP/HTTPS port
    elif len(ports) > 1:
        for internal_port, external_port in ports:

            protocol = None

            if internal_port in COMMON_HTTP_PORTS:
                protocol = "http"
            elif internal_port in COMMON_HTTPS_PORTS:
                protocol = "https"

            if protocol is not None:
                logger.debug(f"Found common {protocol} port {internal_port} -> {external_port}")
                return f"{protocol}://{HOSTNAME}:{external_port}", external_port

        logger.error(f"More than one UI port found for {name}\nDisanbiguation needed with plato.ui-port")
        exit(1)


    else:
        # If no port is exposed, search known ports
        image_name = container.image.tags[0] if container.image.tags else ""
        container_name = container.name.lower()

        for service, port in KNOWN_PORTS.items():
            if service in image_name or service in container_name:
                logger.debug(f"Found known port for service {service}: {port}")
                return f"http://{HOSTNAME}:{port}", port

        logger.error(f"No port found for {name}\nPort must be provided with plato.ui-port")
        exit(1)

# ===================================================
#                  GENERATE CONFIG
# ===================================================

def generate_homer_config():
    logger.info("🔧 Generating Homer dashboard configuration...")

    categories = {}

    for container in safe_list_containers():

        # skip stopped/paused containers
        if container.status != "running":
            continue

        labels = container.labels

        category = labels.get("plato.category")

        if not category:
            continue

        container_name = container.name.lower()

        name        = labels.get("plato.name", container_name.title())
        url         = labels.get("plato.url")
        endpoint    = labels.get("plato.endpoint")
        ui_port     = labels.get("plato.ui-port")

        force_https = labels.get("plato.force-https", "false").lower() in ("1", "true", "yes")

        caddy       = labels.get("caddy")
        logger.debug(f"> Processing container {name}")

        if not url:
            # caddy-docker-proxy url
            if caddy:
                logger.debug(f"Caddy url found: {caddy}")
                url = "https://" + caddy
            elif ui_port:
                url = f"http://{HOSTNAME}:{ui_port}"
            else:
                url, ui_port = get_local_url(container, name)

            if endpoint:
                url = urljoin(url.rstrip('/') + '/', endpoint)

        if url and force_https:
            if "https" not in url:
                logger.debug(f"Force HTTPS on {url}")
                url = url.replace("http", "https")

        if not url:
            logger.error(f"Could not create URL for {name}")
            exit(1)

        try:
            position = int(labels.get("plato.position", 99))
        except (TypeError, ValueError):
            logger.error(f"plato.position must be an integer value for {name}")
            exit(1)

        result = {
            k: v
            for k, v in {
                "name"       : name,
                "url"        : url,
                "position"   : position,
                "subtitle"   : labels.get("plato.subtitle"),
                "tag"        : labels.get("plato.tag"),
                "tagstyle"   : labels.get("plato.tagstyle"),
                "keywords"   : labels.get("plato.keywords"),
                "icon"       : labels.get("plato.icon")
            }.items()
            if v is not None
        }

        custom_logo = labels.get("plato.custom-logo")

        if custom_logo:
            result['logo'] = custom_logo

        elif AUTOMATIC_ICONS:
            search_icon = container_name

            selfhst_icon = labels.get("plato.selfhst-icon")

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
                    logger.error("Provided logo is invalid: plato.selfhst-icon")
                    exit(1)

        categories.setdefault(category, []).append(result)

    # Sort each column
    for category in categories:
        categories[category].sort(key=lambda x: (x["position"], x["name"]))


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

    generate_homer_config()

    for event in client.events(decode=True, filters={"type": "container"}):
         # Skip exec-related events
        action = event["Action"]
        if action.startswith("exec_"):
            continue

        logger.debug(f"Container event: {event["Action"]} on {event["Actor"]["Attributes"].get("name")}")

        generate_homer_config()
