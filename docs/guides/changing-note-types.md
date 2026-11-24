---
title: "Changing Note Types on Existing Cards"
---

Convert existing notes from one note type to another (for example, **Basic** to **Basic (and reversed card)**) and map their fields without re-entering data. For full details, see the [official Anki Manual](https://docs.ankiweb.net/).

## Conversion Workflow

```mermaid
flowchart LR
  Select["Select Notes in Browser"] -->|"Ctrl+Shift+M"| Menu["Notes > Change Note Type..."]
  Menu --> Target["Choose New Note Type"]
  Target --> Map["Map Fields & Save"]
```

<!-- tutorial:changing-note-types:start -->

> [!mimik] Changing Note Types on Existing Cards
> Convert existing notes to another note type in the Card Browser and map their fields.
>
> ---
>
> ## Step 01: Select Notes in the Browser
>
> ![Step 01: Select Notes in the Browser](../assets/tutorials/changing-note-types/step-01-browser-select-notes.webp)
>
> Open **Browse** (`B`), filter to the deck or notes you want to convert, and select one or more rows.
>
> ---
>
> ## Step 02: Open Notes > Change Note Type...
>
> ![Step 02: Open Notes > Change Note Type...](../assets/tutorials/changing-note-types/step-02-notes-change-note-type.webp)
>
> Click **Notes > Change Note Type...** (or press `Ctrl+Shift+M`), pick the target note type, map each existing field to its destination field, and click **Save**.

<!-- tutorial:changing-note-types:end -->
