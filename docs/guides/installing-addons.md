---
title: "Installing Anki Add-ons"
---

Find, download, and install community add-ons using their AnkiWeb code. For full details on managing add-ons, see the [official Anki Manual](https://docs.ankiweb.net/addons.html) and our [Managing Add-ons](../manual/addons.md) walkthrough.

## Add-on Installation Workflow

```mermaid
flowchart LR
  Browse["Browse ankiweb.net/shared/addons"] -->|"Copy Code"| Open["Tools > Add-ons (Ctrl+Shift+A)"]
  Open -->|"Get Add-ons..."| Paste["Paste Code & Click OK"]
  Paste --> Restart["Restart Anki"]
```

## 1. Find an Add-on & Copy Its Code on AnkiWeb

Visit [ankiweb.net/shared/addons](https://ankiweb.net/shared/addons) to browse by **Title**, **Modified**, or **Anki** version, or search in the top-right bar.

![AnkiWeb Shared Add-ons directory](../assets/tutorials/ankiweb-addons/step-01-ankiweb-browse.png)

Open the add-on's page, scroll to **Download**, check **Supported Anki versions**, and copy the numeric code box (you can also use **All Add-Ons** or **Contact Author** below it).

![AnkiWeb Add-on Download Code section](../assets/tutorials/ankiweb-addons/step-02-ankiweb-code.png)

## 2. Install in Anki

1. Open **Tools > Add-ons** (`Ctrl+Shift+A`).
2. Click **Get Add-ons...**, paste the numeric code, and click **OK**.
3. Restart Anki for the add-on to take effect.
