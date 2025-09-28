import crossplane
import docker
import os
import re
import yaml
from pathlib import Path

client = docker.from_env()

HOSTNAME = os.getenv("HOSTNAME")
if not HOSTNAME:
    print("HOSTNAME must be provided")
    exit(1)

SELFHST_ICONS = Path("/www/assets/selfhst-icons/png")
CUSTOM_ICONS = Path("/www/assets/custom")

AUTOMATIC_ICONS = os.getenv("AUTOMATIC_ICONS", "True").lower() in ("1", "true", "yes")

CATEGORY_ICONS = os.getenv("CATEGORY_ICONS")

if CATEGORY_ICONS:
    CATEGORY_ICONS_DICT = dict(
        (k.strip(), v.strip())
        for k, v in (item.split("=", 1) for item in CATEGORY_ICONS.split(",") if "=" in item)
    )
else:
    print("CATEGORY_ICONS not provided. Column order will be random")
    CATEGORY_ICONS_DICT = {}

NGINX_CONFIG_PATH = os.getenv("NGINX_CONFIG_PATH", "/etc/nginx/nginx.conf")

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



def get_nginx_port_url_map(nginx_conf=NGINX_CONFIG_PATH):
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
    return {port: sorted(urls) for port, urls in port_url_map.items()}


def get_ui_port(container, name):
    unique_ports = set()

    for _, host_mappings in container.attrs['NetworkSettings']['Ports'].items():
        if host_mappings:
            for mapping in host_mappings:
                unique_ports.add(mapping['HostPort'])

    if len(unique_ports) == 0:
        print(f"No port found for {name}\nDisanbiguation needed with com.plato.ui_port")
        exit(1)

    if len(unique_ports) > 1:
        print(f"More than one port found for {name}\nDisanbiguation needed with com.plato.ui_port")
        exit(1)

    return next(iter(unique_ports))

NGINX_URL_PAIRS = get_nginx_port_url_map()


categories = {}

for container in client.containers.list():

    labels = container.labels

    category = labels.get("com.plato.category")

    if not category:
        continue

    container_name = container.name.lower()

    name     = labels.get("com.plato.name", container_name.title())
    url      = labels.get("com.plato.url")
    ui_port  = labels.get("com.plato.ui_port")

    if not url:
        if not ui_port:
            ui_port = get_ui_port(container, name)

        if ui_port:
            url = [f"http://{HOSTNAME}:{ui_port}"]
        if NGINX_URL_PAIRS:
            url = NGINX_URL_PAIRS.get(ui_port, url)

    if not url:
        print(f"Could not create URL for {name}")
        exit(1)


    try:
        importance = float(labels.get("com.plato.importance", 0))
    except (TypeError, ValueError):
        print(f"com.plato.importance must be a float value for {name}")
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
            print(f"Found Custom icon for {name}: {search_icon}")
        elif os.path.exists(selfhst_icon_path):
            result['logo'] = str(Path(*selfhst_icon_path.parts[2:]))
            print(f"Found selfh.st icon for {name}: {search_icon}")
        else:
            print(f"Icon not found for {name}: {search_icon}")
            if selfhst_icon:
                print("Provided logo is invalid: com.plato.selfhst-icon")
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

print(yaml.dump(configuration, sort_keys=False, default_flow_style=False))

with open("/www/assets/config.yml", "w") as f:
    yaml.dump(configuration, f, default_flow_style=False, sort_keys=False)
