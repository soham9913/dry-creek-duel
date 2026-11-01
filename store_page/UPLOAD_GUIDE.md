# Putting Dry Creek Duel on itch.io — step by step

## 1. Build the two files (on your Windows PC)

Double-click these in the game folder. Each one sets everything up the first time, which takes a few minutes.

| Script | Makes | What it is |
| --- | --- | --- |
| `build_web.bat` | `release\dry-creek-duel-web.zip` | The browser version (most players will play this one) |
| `build_windows.bat` | `release\DryCreekDuel-windows.zip` | The Windows download (no Python needed to play) |

**Test them before uploading:**
- Web: run `build_web.bat --serve` from a terminal in the game folder, then open http://localhost:8000. Click the page once to start (browsers only play sound after a click).
- Windows: open `build\dist\DryCreekDuel\DryCreekDuel.exe`.

If you change the sounds, run `python tools\render_sounds.py` first. If you change how the game looks, run `python tools\make_store_assets.py` to remake the screenshots.

## 2. Create the project page

1. Sign in at itch.io, then **Dashboard → Create new project**.
2. **Title:** Dry Creek Duel. **Project URL:** for example `dry-creek-duel`.
3. **Short description:** copy it from `DESCRIPTION.md`.
4. **Classification:** Games. **Kind of project:** **HTML** (this lets it play in the browser).
5. **Release status:** Released.
6. **Pricing:** choose **$0 or donate** and set a **suggested donation of $2.00**.
   - Browser games can always be played for free, so donations are how HTML games earn money.
   - itch.io recommends not charging below $2, because each payment has a fixed fee of about $0.30.

## 3. Upload the files

1. **Upload files →** `dry-creek-duel-web.zip`. Tick **"This file will be played in the browser."**
2. **Upload files →** `DryCreekDuel-windows.zip`. Tick the **Windows** platform box.

## 4. Embed options (for the browser version)

- **Viewport dimensions:** **960 × 640**
- **Fullscreen button:** ✔ on
- **Mobile friendly:** off (the game is built for keyboard and mouse)
- **Automatically start on page load:** off (a click is needed for sound)
- If the game shows a black screen on itch.io but works at localhost, try ticking **SharedArrayBuffer support** and refresh.

## 5. Make the page look good

- **Cover image:** `store_page/cover.png` (630 × 500)
- **Screenshots:** `screenshot_1.png` to `screenshot_6.png`
- **Description:** paste from `DESCRIPTION.md`, then insert `gameplay.gif` where it says to.
- **Genre, tags, "Made with", inputs:** listed at the bottom of `DESCRIPTION.md`.
- **Edit theme** (top of the page editor): a dark background (#1b0d09) with an orange link colour (#e4572e) matches the game.

## 6. Test as a draft, then publish

1. Leave **Visibility** on **Draft** and **Save**.
2. Open the page with **View page**. Play a full run in the browser: menu, a duel, pause, Settings, and reloading the page (your best time should still be there).
3. When everything works, set **Visibility → Public** and save.

## 7. Getting paid (before your first payout)

- **Settings → Payments:** add PayPal or Payoneer.
- itch.io asks you to complete a **tax interview** (a one-time $3 verification fee) before it pays out. As a seller outside the US, a tax treaty may lower the default 30% US withholding; the interview handles this.
- itch.io keeps 10% by default (you can change this), and the payment processor takes about 2.9% + $0.30 per payment.

## 8. After launch

- Post a **devlog** on the page ("Dry Creek Duel 1.0 is out!") because devlogs show up in itch.io feeds.
- For updates, bump `VERSION` in `config.py`, rebuild, and replace the uploaded files. Players keep their saves.
