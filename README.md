# 🏺 Plato – Homer Dashboard Generator

Plato replaces your current Homer dashboard. To generate the config you just
need to add labels to the docker services you want to display and plato does the
rest. It also crossreferences with nginx to get external url and generates a
Homer Dashboard dinamically as containers are started and stoped.

Includes automatic selfh.st icons for ease of use.

## 🏷 Docker Labels

The claim to fame of this software is simple. The only label you **need** to add to
each docker container on the page is `com.plato.category`. Every other tag is optional.

- If the container only has one exposed port it will be considered the UI port.
- If not, you have to disambiguate using `com.plato.ui-port`
- This port is then used to search your NGINX config (if provided) for the
    external url of the service.
- Plato uses the container name to search the selfh.st icon list. To override this, use `com.plato.selfhst-icon`.

Full list of labels is as follow:

```yaml
labels:
  com.plato.category      # (Mandatory) Category name; must match CATEGORY_ICONS
  com.plato.name          # Optional; Service name; defaults to container name if not provided
  com.plato.selfhst-icon  # Optional; Overrides container name for selfh.st icons
  com.plato.custom-logo   # Optional; Logo URL/path; overrides everything
  com.plato.icon          # Optional;
  com.plato.subtitle      # Optional;
  com.plato.tag           # Optional;
  com.plato.tagstyle      # Optional;
  com.plato.keywords      # Optional;
  com.plato.ui-port       # Optional; disambiguates multiple ports or host-mounted containers
  com.plato.url           # Optional; main service URL; overrides everything
  com.plato.importance    # Optional; Defaults to 0; higher numbers appear first
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
| AUTOMATIC_ICONS                   | True                    | If you want to auto search icons based on container name |

### Homer Specific

| Variable                          | Default                |
|-----------------------------------|------------------------|
| TITLE                             | Demo dashboard         |
| SUBTITLE                          | Plato                  |
| LOGO                              | logo.png               |
| COLUMNS                           | auto                   |
| HEADER                            | true                   |
| FOOTER                            | false                  |
| COLORS_LIGHT_HIGHLIGHT-PRIMARY    | #3367d6                |
| COLORS_LIGHT_HIGHLIGHT-SECONDARY  | #4285f4                |
| COLORS_LIGHT_HIGHLIGHT-HOVER      | #5a95f5                |
| COLORS_LIGHT_BACKGROUND           | #f5f5f5                |
| COLORS_LIGHT_CARD-BACKGROUND      | #ffffff                |
| COLORS_LIGHT_TEXT                 | #363636                |
| COLORS_LIGHT_TEXT-HEADER          | #ffffff                |
| COLORS_LIGHT_TEXT-TITLE           | #303030                |
| COLORS_LIGHT_TEXT-SUBTITLE        | #424242                |
| COLORS_LIGHT_CARD-SHADOW          | rgba(0, 0, 0, 0.1)     |
| COLORS_LIGHT_LINK                 | #3273dc                |
| COLORS_LIGHT_LINK-HOVER           | #363636                |
| COLORS_DARK_HIGHLIGHT-PRIMARY     | #3367d6                |
| COLORS_DARK_HIGHLIGHT-SECONDARY   | #4285f4                |
| COLORS_DARK_HIGHLIGHT-HOVER       | #5a95f5                |
| COLORS_DARK_BACKGROUND            | #131313                |
| COLORS_DARK_CARD-BACKGROUND       | #2b2b2b                |
| COLORS_DARK_TEXT                  | #eaeaea                |
| COLORS_DARK_TEXT-HEADER           | #ffffff                |
| COLORS_DARK_TEXT-TITLE            | #fafafa                |
| COLORS_DARK_TEXT-SUBTITLE         | #f5f5f5                |
| COLORS_DARK_CARD-SHADOW           | rgba(0, 0, 0, 0.4)     |
| COLORS_DARK_LINK                  | #3273dc                |
| COLORS_DARK_LINK-HOVER            | #ffdd57                |
| PWA_NAME                          | Plato Dashboard        |
| PWA_SHORT_NAME                    | Plato                  |
| PWA_DESCRIPTION                   | Plato Server Dashboard |
| PWA_BACKGROUND_COLOR              | #ffffff                |
| PWA_THEME_COLOR                   | #3367D6"               |

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
