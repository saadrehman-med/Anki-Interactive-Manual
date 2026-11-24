---
title: "Creating Subdecks & Moving Cards"
---

Use nested deck names (`Parent::Child`) and the Card Browser's **Change Deck** action to organize decks and move cards without losing scheduling history.

```mermaid
flowchart LR
  Create["Create Deck (Parent::Child)"] --> Browser["Open Browser (B)"]
  Browser --> Select["Select Cards"]
  Select --> Change["Cards > Change Deck (Ctrl+D)"]
  Change --> Target["Pick Target Deck"]
```

<!-- tutorial:moving-and-renaming-decks:start -->

> [!mimik] Creating Subdecks & Moving Cards
> Create a nested subdeck with `::` notation, move cards in the Browser, and rename decks from the gear menu.
>
> ---
>
> ## Step 01: Create a Nested Subdeck
>
> ![Step 01: Create a Nested Subdeck](../assets/tutorials/moving-and-renaming-decks/step-01-create-deck.webp)
>
> Click **Create Deck** at the bottom of the Decks screen and enter a `Parent::Child` name such as `Demo deck::Subdeck` to nest it inside **Demo deck**.
>
> ---
>
> ## Step 02: Move Selected Cards via Cards > Change Deck
>
> ![Step 02: Move Selected Cards via Cards > Change Deck](../assets/tutorials/moving-and-renaming-decks/step-02-change-deck-menu.webp)
>
> Open the **Browser** (<kbd>B</kbd>), select the cards you want to move, and choose **Cards > Change Deck...** (<kbd>Ctrl</kbd>+<kbd>D</kbd>).
>
> ---
>
> ## Step 03: Rename or Manage a Deck from the Gear Menu
>
> ![Step 03: Rename or Manage a Deck from the Gear Menu](../assets/tutorials/moving-and-renaming-decks/step-03-deck-gear-rename.webp)
>
> Click the gear icon next to any deck to **Rename** it (you can also add or remove `::` nesting here) or **Delete** an empty deck.

<!-- tutorial:moving-and-renaming-decks:end -->
