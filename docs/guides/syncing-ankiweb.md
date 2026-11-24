---
title: "Syncing Across Devices: Upload vs Download"
---

Connect Anki to your AnkiWeb account and choose the right option when a full-sync conflict dialog appears. For full details, see the [official Anki Manual](https://docs.ankiweb.net/syncing.html).

## Upload vs Download Decision Map

```mermaid
flowchart TD
  Conflict["Sync Conflict: Upload or Download?"] --> Question{"Which copy has your latest cards & progress?"}
  Question -->|"This device"| Upload["Click Upload to AnkiWeb (overwrites AnkiWeb)"]
  Question -->|"AnkiWeb / another device"| Download["Click Download from AnkiWeb (overwrites this device)"]
```

<!-- tutorial:syncing-ankiweb:start -->

> [!mimik] Syncing Across Devices: Upload vs Download
> Trigger a sync and choose the right option when a full-sync conflict dialog appears.
>
> ---
>
> ## Step 01: Click Sync (or Press Y)
>
> ![Step 01: Click Sync (or Press Y)](../assets/tutorials/syncing-ankiweb/step-01-sync-button.webp)
>
> Click **Sync** in the top toolbar (or press `Y`) to sync your collection with AnkiWeb.
>
> ---
>
> ## Step 02: Choose Upload to AnkiWeb (Keep This Device)
>
> ![Step 02: Choose Upload to AnkiWeb (Keep This Device)](../assets/tutorials/syncing-ankiweb/step-02-upload-to-ankiweb.webp)
>
> Click **Upload to AnkiWeb** when **this device** has your latest cards and review history. This overwrites AnkiWeb with your local collection.
>
> ---
>
> ## Step 03: Choose Download from AnkiWeb (Keep Server Copy)
>
> ![Step 03: Choose Download from AnkiWeb (Keep Server Copy)](../assets/tutorials/syncing-ankiweb/step-03-download-from-ankiweb.webp)
>
> Click **Download from AnkiWeb** when **another device / AnkiWeb** has your latest changes. This replaces your local decks with AnkiWeb's copy.

<!-- tutorial:syncing-ankiweb:end -->
