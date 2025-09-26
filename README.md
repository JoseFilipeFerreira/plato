# 🏺 Plato – Homer Dashboard Generator

Reads labels from docker, crossreferences with nginx to get external url and
generates on runtime the Homer Dashboard

## 🏷 Docker Labels

The claim to fame of this software is simple. The only label you have to add to
each docker container you want to show on the page is `com.plato.category`. Every other tag is optional.

If the container only has one exposed port it will be considered the UI port. If
not, you have to disambiguate using `com.plato.ui_port`. Then this port is used
to search the nginx config to see if there is any external URL.

Full list of labels is as follow:

```yaml
labels:
  com.plato.category      # (Mandatory) Category name; must match CATEGORY_ICONS
  com.plato.name          # Service name; defaults to container_name if not provided
  com.plato.icon          # Optional icon
  com.plato.logo          # Logo URL/path; defaults to /www/assets/tools/{name}.png if not provided and com.homer.icon not set
  com.plato.subtitle      # Optional subtitle
  com.plato.tag           # Optional tag
  com.plato.tagstyle      # Optional tag style
  com.plato.keywords      # Comma-separated keywords
  com.plato.ui_port       # Optional; used to disambiguate multiple ports or host-mounted containers
  com.plato.url           # Optional main service URL; overrides nginx search
  com.plato.importance    # Defaults to 0; higher numbers appear first in the category
```
---

## 🌟 Mandatory Environment Variables

| Variable        | Description                                                                                  |
|-----------------|----------------------------------------------------------------------------------------------|
| CATEGORY_ICONS  | Comma-separated mapping of categories to FontAwesome icons. Example: `Botnet=fas fa-cloud, Media=fas fa-photo-video, Download=fas fa-download, Utilities=fas fa-toolbox, Infrastructure=fas fa-tasks-alt` |
| HOSTNAME        | The hostname of the container or service.                                                   |

---


## ⚙️ Optional Environment Variables (with defaults)

| Variable                          | Default         |
|-----------------------------------|-----------------|
| TITLE                             | Demo dashboard  |
| SUBTITLE                          | Plato           |
| LOGO                              | logo.png        |
| COLUMNS                           | auto            |
| HEADER                            | true            |
| FOOTER                            | false           |

### Light Theme Colors

| Variable                          | Default         |
|-----------------------------------|-----------------|
| COLORS_LIGHT_HIGHLIGHT-PRIMARY    | #3367d6         |
| COLORS_LIGHT_HIGHLIGHT-SECONDARY  | #4285f4         |
| COLORS_LIGHT_HIGHLIGHT-HOVER      | #5a95f5         |
| COLORS_LIGHT_BACKGROUND           | #f5f5f5         |
| COLORS_LIGHT_CARD-BACKGROUND      | #ffffff         |
| COLORS_LIGHT_TEXT                 | #363636         |
| COLORS_LIGHT_TEXT-HEADER          | #ffffff         |
| COLORS_LIGHT_TEXT-TITLE           | #303030         |
| COLORS_LIGHT_TEXT-SUBTITLE        | #424242         |
| COLORS_LIGHT_CARD-SHADOW          | rgba(0, 0, 0, 0.1) |
| COLORS_LIGHT_LINK                 | #3273dc         |
| COLORS_LIGHT_LINK-HOVER           | #363636         |

### Dark Theme Colors

| Variable                          | Default           |
|----------------------------------|-----------------|
| COLORS_DARK_HIGHLIGHT-PRIMARY     | #3367d6         |
| COLORS_DARK_HIGHLIGHT-SECONDARY   | #4285f4         |
| COLORS_DARK_HIGHLIGHT-HOVER       | #5a95f5         |
| COLORS_DARK_BACKGROUND            | #131313         |
| COLORS_DARK_CARD-BACKGROUND       | #2b2b2b         |
| COLORS_DARK_TEXT                  | #eaeaea         |
| COLORS_DARK_TEXT-HEADER           | #ffffff         |
| COLORS_DARK_TEXT-TITLE            | #fafafa         |
| COLORS_DARK_TEXT-SUBTITLE         | #f5f5f5         |
| COLORS_DARK_CARD-SHADOW           | rgba(0, 0, 0, 0.4) |
| COLORS_DARK_LINK                  | #3273dc         |
| COLORS_DARK_LINK-HOVER            | #ffdd57         |


---

## Deploy

```yaml
services:
  plato:
    image: josefilipeferreira/plato
    container_name: plato
    volumes:
      - ${DATADIR}/plato/assets:/www/assets
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /etc/nginx:/etc/nginx:ro # optional if you want auto external URL
    environment:
      HOSTNAME: "kiwi"
      CATEGORY_ICONS: "Media=fas fa-photo-video, Download=fas fa-download, Utilities=fas fa-toolbox"
    ports:
      - 8084:8080
```
