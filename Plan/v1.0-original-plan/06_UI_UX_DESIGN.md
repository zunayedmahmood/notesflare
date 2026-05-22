# NotesFlare — UI/UX Design Instructions

> **AI Instruction File 06 of 08**
> This file governs every visual and interaction decision in the NotesFlare interface. It defines layout rules, spacing principles, animation constraints, interaction states, and what the interface must never do. Read `01_BRAND_AND_ARCHITECTURE.md` before this file — all color tokens and font choices are defined there.

---

## 1. DESIGN PHILOSOPHY

NotesFlare must look and feel like **the quietest possible container for thought.**

Every visual element exists on a spectrum from "visible" to "invisible." The goal is to push every non-writing element toward invisible. The writing itself should feel like it exists in open space — not inside an application.

### Three Rules That Override Everything Else

**Rule 1: The writing area is the entire product.**
Everything else — the sidebar, the timestamps, the Flareon name — is infrastructure. If infrastructure competes with the writing area for attention, it is wrong.

**Rule 2: Never interrupt the user.**
No toasts. No modals. No confirmation dialogs. No loading states visible in the writing area. The only exception is the error message when a duplicate Flareon name is entered.

**Rule 3: Show less than you think you should.**
The instinct when building UI is to add elements that provide feedback, confirm actions, and demonstrate the system's intelligence. Resist this completely. The fewer elements on screen, the more powerful the writing area feels.

---

## 2. LAYOUT SPECIFICATION

### Full Layout Grid

```
┌──────────────────────────────────────────────────────────────────┐
│  [220px sidebar]  │  [remaining width — writing area]            │
│                   │                                              │
│  App label        │    [60px left pad]  [content]  [60px right] │
│  ─────────────    │                                              │
│  Flareon 1        │    FLAREON NAME (muted label)                │
│  Flareon 2  ←─    │                                              │
│  Flareon 3   active│   [Past burst — dimmed text]                │
│                   │   ─────────────────── timestamp ─            │
│  ─────────────    │   [Past burst — dimmed text]                 │
│  + New Flareon    │   ─────────────────── timestamp ─            │
│                   │                                              │
│                   │   [Active burst — full brightness text]      │
│                   │   ░ cursor                                   │
│                   │                                              │
└──────────────────────────────────────────────────────────────────┘
```

### Sidebar: 220px fixed
- Never resizable in V1
- Never collapsible in V1
- Fixed to the left edge
- Full viewport height

### Writing Area: `calc(100vw - 220px)`
- Content is centered within this space
- Max content width: `680px`
- Horizontal padding on both sides: `60px`
- Top padding: `80px` — this pushes content away from the window edge, giving a page-like feel
- Bottom padding: `200px` — extra bottom space so the last line of text is never at the screen edge

---

## 3. SIDEBAR DESIGN (DETAILED)

### Hierarchy
The sidebar has exactly three zones, in this vertical order:

```
[App label]         ← 24px from top, all-caps, muted
[Flareon list]      ← scrollable, fills remaining space
[Create button]     ← pinned to bottom
```

### App Label
- Text: "NotesFlare"
- Color: `--text-secondary` (#6B6B80)
- Font: `--font-ui`, 11px, uppercase, letter-spacing 0.1em, weight 500
- Padding: 0 16px
- Purpose: orient the user, not brand. Keep it quiet.

### Flareon List Items

**Default state:**
```css
padding: 8px 10px
border-radius: 6px
color: var(--text-secondary)
background: transparent
font-size: 13px
white-space: nowrap
overflow: hidden
text-overflow: ellipsis
```

**Hover state:**
```css
background: var(--bg-elevated)  /* #1C1C22 */
color: var(--text-secondary)    /* same — hover doesn't brighten text */
transition: background 0.1s
```

**Active state (selected Flareon):**
```css
background: var(--accent-flare-dim)  /* #3D356B */
color: var(--text-primary)           /* brighten only on selection */
```

**Important:** The active item's text is `--text-primary`. Everything else is `--text-secondary`. This creates hierarchy without adding any icons, borders, or indicators.

### Create Flareon Interaction

**Button (default):**
- Text: "+ New Flareon"
- Color: `--text-muted`
- Border: `1px dashed var(--border-subtle)`
- Border-radius: 6px
- Background: transparent

**Button (hover):**
- Border color: `--accent-flare`
- Text color: `--text-secondary`
- Transition: 0.15s

**Input (after click):**
- Replaces the button
- Auto-focused
- Border: `1px solid var(--accent-flare)` — slightly more prominent than button hover
- Background: `var(--bg-elevated)`
- Placeholder: "Flareon name..."
- On Enter: submit
- On Escape: cancel (return to button state, clear input)
- On blur with empty input: cancel

**Error state (duplicate name):**
- Small text below the input field
- Color: `#FF6B6B` (soft red that matches the dark theme)
- Font: 11px, `--font-ui`
- Text: "Already exists." (short, not verbose)

---

## 4. WRITING AREA DESIGN (DETAILED)

### Layout
```
[80px top space]
[Flareon Name Label — muted, uppercase, 11px]
[48px gap]
[Past burst 1]
[Burst separator]
[Past burst 2]
[Burst separator]
[Current burst textarea]
[200px bottom space]
```

### Flareon Name Label (FlareLabel component)
- Text: The Flareon name, unchanged
- Color: `--text-muted` (#3A3A50)
- Font: `--font-ui`, 11px, uppercase, letter-spacing 0.12em
- Margin bottom: 48px
- Purpose: anchor the user to the thinking domain without shouting it

### Past Burst Block (BurstBlock component)

Each past burst has:
1. A timestamp label + horizontal line separator
2. The burst content (read-only)

**Timestamp label:**
- Format: "Jan 15, 2:30 PM" (not "2025-01-15T14:30:00")
- Color: `--accent-burst` (#4A9EFF), opacity 0.7
- Font: `--font-ui`, 11px, letter-spacing 0.05em
- Positioned left of a horizontal line

**Horizontal line after timestamp:**
- Color: `--border-subtle`, opacity 0.5
- Height: 1px
- Fills remaining width after the timestamp text

**Past burst content:**
- Font: `--font-writing` (monospace)
- Font size: `--text-size-writing` (18px)
- Line height: `--line-height-writing` (1.85)
- Color: `--text-secondary` (#6B6B80) — dimmer than active
- `white-space: pre-wrap` — preserve line breaks
- `word-break: break-word` — prevent overflow

**Margin after each burst block:** 48px

### Active Burst Separator

When there are past bursts before the active writing area, show a separator for the active burst too:

**Active separator:**
- Same layout as past burst separators (timestamp + line)
- Timestamp color: `--accent-burst`, opacity **0.9** (slightly brighter than past bursts)
- Line color: `--accent-flare-dim` instead of `--border-subtle` (subtle purple tint — distinguishes the active session)
- Margin bottom: 24px (less than past burst blocks — it's adjacent to the active content)

### Active Textarea

The textarea is the most important element in the entire application. These styles are not suggestions — they define the product.

```css
width: 100%;
background: transparent;
border: none;
outline: none;
resize: none;
overflow: hidden;         /* No scrollbar inside textarea — it grows */

font-family: var(--font-writing);
font-size: var(--font-size-writing);      /* 18px */
line-height: var(--line-height-writing);  /* 1.85 */
color: var(--text-primary);              /* Full brightness — this is active */
caret-color: var(--cursor);             /* Purple cursor */

padding: 0;               /* No internal padding — handled by parent */
min-height: 60vh;         /* Textarea always feels spacious even when empty */
```

**The textarea must grow with content.** Use the `autoResize` function that sets `height: auto` then `height: scrollHeight`. This ensures the textarea never shows its own scrollbar — the page scrolls, not the textarea.

**Placeholder:**
- Text: "Start writing..."
- Color: `--text-muted` (#3A3A50)
- This is CSS `::placeholder` — apply via global CSS or inline style

**The cursor:**
- `caret-color: var(--cursor)` — the blinking cursor is accent purple
- This is the one intentional piece of visual personality in the entire writing area

---

## 5. TYPOGRAPHY RULES

### Writing Area: Monospace
All content in the writing area (both past bursts and the active textarea) uses `--font-writing`:
```
'iA Writer Quattro', 'Courier Prime', 'Courier New', monospace
```

**Why monospace?**
- Creates a strong visual separation between the writing content and the UI chrome
- Has deliberate, meditative quality — associated with focused writing tools
- Consistent character widths aid in reading back what was written

### UI: Inter (sans-serif)
All sidebar text, labels, timestamps, and buttons use `--font-ui`:
```
'Inter', system-ui, -apple-system, sans-serif
```

This contrast between the writing font and the UI font makes the writing area feel like a different *zone* — you step into it when you write.

### Font Loading
Load Inter from Google Fonts in `layout.tsx`. iA Writer Quattro is not freely available — fall back gracefully to Courier Prime (load from Google Fonts) or system monospace.

```html
<link
  href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&family=Courier+Prime:ital@0;1&display=swap"
  rel="stylesheet"
/>
```

---

## 6. ANIMATION AND TRANSITION RULES

### What IS animated
| Element | Property | Duration | Easing |
|---|---|---|---|
| Sidebar item hover | `background` | 100ms | linear |
| Create button hover | `border-color`, `color` | 150ms | ease |
| Writing area mount | `opacity` 0→1 | 200ms | ease-out |

### What is NOT animated
- Flareon switching (instant — the `key` prop change forces a re-mount)
- Sidebar list reordering (instant)
- Textarea content (instant)
- Save operations (silent, no animation)
- Error message appearance (instant — no slide-in, no fade-in)

### Why so little animation?
The product philosophy is about removing friction from thought. Animation adds a small but real delay between action and result. More importantly, animation draws attention — and anything that draws attention away from writing is wrong.

The one exception (`opacity` fade on writing area mount) is to prevent a jarring content-pop when switching Flareons. But it is 200ms — barely perceptible.

---

## 7. INTERACTION STATES: COMPLETE MAP

### Sidebar Button (Flareon item)

| State | Background | Text Color |
|---|---|---|
| Default | transparent | `--text-secondary` |
| Hover | `--bg-elevated` | `--text-secondary` |
| Active (selected) | `--accent-flare-dim` | `--text-primary` |
| Active + Hover | `--accent-flare-dim` | `--text-primary` (unchanged) |

### Create Flareon Button

| State | Border | Text |
|---|---|---|
| Default | `1px dashed --border-subtle` | `--text-muted` |
| Hover | `1px dashed --accent-flare` | `--text-secondary` |

### Create Flareon Input

| State | Border | Background |
|---|---|---|
| Active (focused) | `1px solid --accent-flare` | `--bg-elevated` |
| Error | `1px solid #FF6B6B` | `--bg-elevated` |

### Textarea

| State | Appearance |
|---|---|
| Empty | Shows placeholder `--text-muted` |
| Typing | Normal, no special state |
| Saving | No visual change |
| Saved | No visual change |
| Error | No visual change |

---

## 8. EMPTY STATES

### No Flareons Created Yet (Sidebar)
The Flareon list is empty. No message, no illustration, no onboarding. The "+ New Flareon" button is visible at the bottom. The writing area shows:

```
[centered vertically in the writing zone]
Select a Flareon to begin.

[color: --text-muted, font: --font-ui, 13px]
```

That's all. No prompt, no tutorial, no call-to-action besides what the UI naturally provides.

### Flareon With No History (First Open)
The writing area shows:
- Flareon name label at top
- Empty textarea with placeholder "Start writing..."

No burst separator (there's only one burst and it's active).

### Flareon With Only Empty Past Bursts
Past bursts with empty content are NOT rendered (`BurstBlock` returns `null` if `content.trim() === ""`).

---

## 9. SCROLL BEHAVIOR

**The page scrolls, not the textarea.** The `main` writing area container has `overflow-y: auto`. The textarea grows with content and never has its own scrollbar.

**On Flareon switch:** The `key` prop change remounts the `WritingArea` component. On remount, the page scroll should return to the bottom (where the active textarea is). This is the default behavior since the page is rendered fresh.

**Sidebar:** If the user has more Flareons than fit in the sidebar, the list scrolls independently of the writing area (`overflow-y: auto` on the nav element with `flex: 1`).

---

## 10. FOCUS MANAGEMENT

### Rule: The textarea must always be focused when a Flareon is open.

Implementation via `useEffect` in `WritingArea`:
```typescript
useEffect(() => {
  if (activeFlareon && textareaRef.current) {
    textareaRef.current.focus();
    const len = textareaRef.current.value.length;
    textareaRef.current.setSelectionRange(len, len);
  }
}, [activeFlareon]);
```

The cursor goes to the **end** of the content, not the beginning. This is because the user's most recent thought is at the end — they will continue from there.

### When focus leaves the textarea
The user may click the sidebar (to switch Flareons). When they do:
- The textarea loses focus
- The Flareon opens
- The new `WritingArea` receives focus via the `useEffect` above

There is no visual "unfocused" state for the textarea. The focus ring is hidden (`outline: none` on the textarea). The user may or may not have focus — the textarea always looks the same.

---

## 11. WINDOW CHROME

### macOS
- `titleBarStyle: "hiddenInset"` — native traffic lights visible in the top-left corner
- The sidebar background (`--bg-surface`) extends behind the traffic light area
- No window title shown (the app name is shown in the sidebar label instead)

### Windows / Linux
- Default frame (no custom titlebar styling in V1)
- Window title: "NotesFlare"

---

## 12. THINGS THE UI MUST NEVER DO

This list is as important as everything above.

- **Never show a "Saving..." indicator.** Ever. In any form.
- **Never show a "Saved ✓" checkmark.** Ever.
- **Never show a loading spinner.** In the writing area, in the sidebar, anywhere.
- **Never show a modal dialog** (except Electron's native error dialog on backend startup failure).
- **Never disable the textarea** while saving or loading.
- **Never show a character count, word count, or reading time.**
- **Never show a toolbar** above the writing area.
- **Never show formatting options** of any kind.
- **Never show a status bar** at the bottom.
- **Never animate text insertion or deletion.**
- **Never auto-scroll the page** without user action.
- **Never show keyboard shortcut hints** in the UI (no tooltip overlays, no bottom bar).
- **Never show the file path** of the database.
- **Never show the burst ID or entry ID** to the user.

---

## 13. DESIGN REVIEW CHECKLIST

Before any UI implementation is considered complete:

- [ ] The writing area occupies at least 80% of the viewport width
- [ ] Opening the app takes you directly to the writing area — no landing screen
- [ ] No element competes with the textarea for visual attention
- [ ] The Flareon name label is unobtrusive (muted, small, uppercase)
- [ ] Past burst text is visually dimmer than the current writing area
- [ ] The active burst's caret is purple (`--cursor`)
- [ ] No animations last longer than 200ms
- [ ] The sidebar does not have icons, badges, or status indicators
- [ ] No UI element mentions "save," "autosave," "sync," or "saved"
- [ ] The empty state is a single quiet sentence, nothing more
- [ ] The font in the writing area is distinctly different from the sidebar font
- [ ] The textarea grows with content (no internal scrollbar)
- [ ] The page scrolls naturally to accommodate long writing sessions
