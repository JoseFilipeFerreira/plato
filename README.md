# 🏺 Plato – Homer Dashboard Generator

Reads labels from docker, crossreferences with nginx to get external url and
generates on runtime the Homer Dashboard

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
| SUBTITLE                          | Homer           |
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

## 🏷 Docker Labels

```yaml
labels:
  com.homer.category      # (Mandatory) Category name; must match CATEGORY_ICONS
  com.homer.name          # Service name; defaults to container_name if not provided
  com.homer.icon          # Optional icon
  com.homer.logo          # Logo URL/path; defaults to /www/assets/tools/{name}.png if not provided and com.homer.icon not set
  com.homer.subtitle      # Optional subtitle
  com.homer.tag           # Optional tag
  com.homer.tagstyle      # Optional tag style
  com.homer.keywords      # Comma-separated keywords
  and com.homer.ui_port
  com.homer.ui_port       # Optional; used to disambiguate multiple ports or host-mounted containers
  com.homer.url           # Optional main service URL; overrides nginx search
  com.homer.importance    # Defaults to 0; higher numbers appear first in the category
```
