# THE FRACTURED GATE

**THE FRACTURED GATE** is a 2D dark-fantasy medieval pixel-art roguelike action game built with **Python 3.12+** and **Pygame-CE**.

---

## Core Features (Phase 1 Prototype)

- **Deterministic Procedural Dungeon Generation**:
  - Non-overlapping rooms of varying dimensions connected via orthogonal corridors.
  - Minimum Spanning Tree (`DungeonGraph`) plus configurable maze loops.
  - Guaranteed graph and tile-level walkability from the **Entrance Room** to all **3 Shrine Rooms** and the **Boss Room**.
  - Biome-specific generation parameters for **Enchanted Forest**, **Crystal Cavern**, and **Demon Castle**.
- **3-Stage Run Structure**:
  - Stages 1 & 2 randomize between *Enchanted Forest* and *Crystal Cavern*; Stage 3 is always *Demon Castle*.
  - Activate 3 guarded Shrines per stage to unlock the Boss Gate, defeat the Stage Boss, and claim the Grand Chest in the post-Stage-3 **Treasure Room**.
- **Real-Time Combat & Data-Driven Characters**:
  - **Warrior** (Unlocked by default), **Mage** (Locked – Blue Crystals), **Archer** (Locked – Blue Crystals).
  - Directional melee arcs, ranged projectiles, Active Skills (`Q` & `E`), Dodge-Dash (`Space`) with invulnerability frames, and knockback physics.
- **Persistent Progression & Save System**:
  - JSON save profile (`saves/profile.save.json`) with automatic `.bak` backup recovery.
  - Spend **Gold** to unlock character skills and **Blue Crystals** to unlock new heroes.
- **Pixel-Art Rendering Pipeline**:
  - Internal `640x360` resolution scaled via nearest-neighbor to `1280x720` (resizable) at 60 FPS.

---

## Controls

| Input | Action |
| :--- | :--- |
| `W / A / S / D` or Arrow Keys | Move character |
| `Mouse Cursor` | Aim direction |
| `Left Mouse Button (LMB)` | Basic Attack |
| `Q` | Active Skill 1 (unlockable with Gold) |
| `E` | Active Skill 2 (unlockable with Gold) |
| `Space` | Dash / Dodge (grants invulnerability frames) |
| `F` | Interact (Activate Shrines / Enter Stage Portal / Open Treasure Chest) |
| `Esc` | Pause Game / Back in Menus |

---

## Setup & Running in VS Code (Windows 10/11)

1. **Create and activate the virtual environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
3. **Run the game**:
   ```powershell
   python main.py
   ```
4. **Run automated tests (210+ test cases including 200+ procedural seeds)**:
   ```powershell
   pytest -v
   ```
5. **Build standalone Windows `.exe` with PyInstaller**:
   ```powershell
   pyinstaller --noconfirm --onefile --windowed --name TheFracturedGate main.py
   ```
