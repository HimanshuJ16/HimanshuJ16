# Setup

Everything lives in the special profile repository **`HimanshuJ16/HimanshuJ16`**. GitHub renders its `README.md` on github.com/HimanshuJ16.

## The concept

The profile is a trading desk. The first screen is a terminal window: a ticker tape of the stack scrolls across the top, a shell session types out who you are, a candlestick chart labelled `HJ16` draws itself, and three "open positions" (HeatCodes, Algo-Trading-Skills, the options engine) fill in. Below it, the architecture of the NIFTY 50 options platform boots service by service with a live boot log, the tech stack is drawn as an order book (frontend bids, backend asks, infra in the spread), and a blotter of your real GitHub activity is regenerated every six hours as a list of fills. It fits because it is literally the thing you are building: a full-stack engineer whose side of the desk is quant finance, rendered in the visual language of the product itself rather than in badges.

## Where each file goes

| Path | What it is | Who writes it |
| --- | --- | --- |
| `README.md` | The profile. Embeds every panel through `<picture>` with dark and light sources | you, by hand |
| `assets/*-dark.svg`, `assets/*-light.svg` | Header, pipeline, order book, section rules, footer | `python3 scripts/build_svgs.py` |
| `scripts/build_svgs.py` | Generator for the static animated panels. Palette, copy and layout live here | you, when you want to change content |
| `scripts/blotter.py` | Renders recent public activity as `blotter-{dark,light}.svg` | the workflow |
| `.github/workflows/profile.yml` | Every 6 hours: blotter + contribution snake, pushed to the `output` branch | GitHub Actions |
| `SETUP.md` | This file | |

The README references two kinds of images:

- **Static panels** from `main`: `https://raw.githubusercontent.com/HimanshuJ16/HimanshuJ16/main/assets/<name>.svg`
- **Live panels** from `output`: `https://raw.githubusercontent.com/HimanshuJ16/HimanshuJ16/output/blotter-dark.svg`, `.../output/github-contribution-grid-snake-dark.svg`, and their light twins

## First-time steps

1. Merge this branch into `main` (or push it there directly).
2. Open the **Actions** tab, pick **Refresh profile panels**, and press **Run workflow** once. This creates or updates the `output` branch with the blotter and snake files. Until it has run, those two images 404; everything else renders immediately.
3. Confirm the workflow has write access: **Settings → Actions → General → Workflow permissions → Read and write permissions**. The workflow also declares `permissions: contents: write`, but the repository setting must allow it.
4. No secrets are needed. The built-in `GITHUB_TOKEN` is enough for the events API, the user/repo lookups, and pushing to `output`.

## Editing content

- Change any copy, colour or layout in `scripts/build_svgs.py`, then run `python3 scripts/build_svgs.py` and commit the regenerated `assets/`. Both themes are emitted from the same drawing so they never drift.
- The blotter maps GitHub event types to rows in `scripts/blotter.py` (`to_fill`). Add or rename mappings there. It only uses the standard library, and it always writes a valid SVG even if the API is unreachable, so a bad run never leaves a broken image.
- Test the blotter locally with `GITHUB_TOKEN=<a classic or fine-grained token with public read> python3 scripts/blotter.py --out dist`.

## Rendering notes

- All motion is SMIL inside the SVG files. GitHub's sanitizer leaves it alone because the SVG is loaded through `<img>`, not inlined.
- Typing and ticker widths are pinned with `textLength`, so the animation lands on character boundaries in whatever monospace font the viewer has.
- Chromium pauses SMIL for images that are off screen and starts them when they scroll into view, so the pipeline "boots" as the visitor reaches it.
- The `<picture>` element follows the viewer's GitHub theme, including when GitHub's theme differs from the OS theme.
