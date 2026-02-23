# 🏺 Plato – Homer Dashboard Generator

Plato replaces your current Homer dashboard. To dinamically generate a dashboard you just
need to add labels to the docker services you want to display and plato does the
rest. It also crossreferences with nginx and caddy-docker-proxy to get the
external url of a given service.

Includes automatic selfh.st icons for ease of use.

## 🏷 Docker Labels

The claim to fame of this software is simple. The only label you **need** to add to
each docker container on the page is `plato.category`. Every other tag is optional.

- If the container only has one exposed port it will be considered the UI port.
- If not, you have to disambiguate using `plato.ui-port`
- This port is then used to search your NGINX config (if provided) for the
    external url of the service.
- Plato uses the container name to search the selfh.st icon list. To override this, use `plato.selfhst-icon`.

Full list of labels is as follow:

```yaml
labels:
  plato.category      # (Mandatory) Category name
  plato.name          # Optional; Service name; defaults to container name if not provided
  plato.selfhst-icon  # Optional; Overrides container name for selfh.st icons
  plato.custom-logo   # Optional; Logo URL/path; overrides everything
  plato.icon          # Optional;
  plato.subtitle      # Optional;
  plato.tag           # Optional;
  plato.tagstyle      # Optional;
  plato.keywords      # Optional;
  plato.ui-port       # Optional; disambiguates multiple ports or host-mounted containers
  plato.url           # Optional; main service URL; overrides everything
  plato.endpoint      # Optional; main service endpoint; appends to the generated url
  plato.force-https   # Optional; force https on the URL
  plato.importance    # Optional; Defaults to 0; higher numbers appear first
```
---

## 🌟 Mandatory Environment Variables

| Variable        | Description                   |
|-----------------|-------------------------------|
| HOSTNAME        | The hostname of the machine.  |

---


## ⚙️ Optional Environment Variables (with defaults)

| Variable                          | Default         | Description |
|-----------------------------------|-----------------|-------------|
| CATEGORY_ICONS                    | ""              | Comma-separated mapping of categories to FontAwesome icons. Example: `Botnet=fas fa-cloud, Media=fas fa-photo-video, Download=fas fa-download, Utilities=fas fa-toolbox, Infrastructure=fas fa-tasks-alt` |
| THEME                             | "default"       | Base theme for the dashboard. See themes inside themes folder |
| AUTOMATIC_ICONS                   | True                    | If you want to auto search icons based on container name |
| LOG_LEVEL                         | INFO                    | |

### Homer Specific

| Variable                   | Default                |
|----------------------------|------------------------|
| TITLE                      | Demo dashboard         |
| SUBTITLE                   | Plato                  |
| LOGO                       | logo.png               |
| COLUMNS                    | auto                   |
| HEADER                     | true                   |
| FOOTER                     | false                  |
| LIGHT_HIGHLIGHT-PRIMARY    | `based on THEME`       |
| LIGHT_HIGHLIGHT-SECONDARY  | `based on THEME`       |
| LIGHT_HIGHLIGHT-HOVER      | `based on THEME`       |
| LIGHT_BACKGROUND           | `based on THEME`       |
| LIGHT_CARD-BACKGROUND      | `based on THEME`       |
| LIGHT_TEXT                 | `based on THEME`       |
| LIGHT_TEXT-HEADER          | `based on THEME`       |
| LIGHT_TEXT-TITLE           | `based on THEME`       |
| LIGHT_TEXT-SUBTITLE        | `based on THEME`       |
| LIGHT_CARD-SHADOW          | `based on THEME`       |
| LIGHT_LINK                 | `based on THEME`       |
| LIGHT_LINK-HOVER           | `based on THEME`       |
| DARK_HIGHLIGHT-PRIMARY     | `based on THEME`       |
| DARK_HIGHLIGHT-SECONDARY   | `based on THEME`       |
| DARK_HIGHLIGHT-HOVER       | `based on THEME`       |
| DARK_BACKGROUND            | `based on THEME`       |
| DARK_CARD-BACKGROUND       | `based on THEME`       |
| DARK_TEXT                  | `based on THEME`       |
| DARK_TEXT-HEADER           | `based on THEME`       |
| DARK_TEXT-TITLE            | `based on THEME`       |
| DARK_TEXT-SUBTITLE         | `based on THEME`       |
| DARK_CARD-SHADOW           | `based on THEME`       |
| DARK_LINK                  | `based on THEME`       |
| DARK_LINK-HOVER            | `based on THEME`       |
| PWA_NAME                   | Plato Dashboard        |
| PWA_SHORT_NAME             | Plato                  |
| PWA_DESCRIPTION            | Plato Server Dashboard |
| PWA_BACKGROUND_COLOR       | #ffffff                |
| PWA_THEME_COLOR            | #3367D6"               |

---

## Deploy

```yaml
services:
  plato:
    image: josefilipeferreira/plato
    container_name: plato
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /etc/nginx:/etc/nginx:ro # optional if you want auto external URL
      # - /path/to/icons/custom:/www/assets/custom if you want to add or override icons to selfhst list
    environment:
      HOSTNAME: "kiwi"
      CATEGORY_ICONS: "Media=fas fa-photo-video, Download=fas fa-download, Utilities=fas fa-toolbox"
    ports:
      - 8080:8080
```
