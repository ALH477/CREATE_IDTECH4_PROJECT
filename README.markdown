# IDTECH4 Project Setup and .pk4 Packager

This Python suite, created by [ALH477](https://github.com/ALH477), streamlines IDTECH4 engine development (e.g., Doom 3, Quake 4) with a modular set of tools, built to power [*PetaByte Madness™*](https://demod.ltd/petabytemadness.html) by [DeMoD LLC](https://demod.ltd) and shared to modernize IDTECH4 for all. Tailored for [DarkRadiant](https://www.darkradiant.net/), it offers project setup, asset packaging, and Git integration via a curses TUI, with external scripts for advanced features like main menu generation and asset organization. Licensed under MIT and GPL v3, it’s a FOSS beacon for IDTECH4’s niche.

## Features
- **Project Setup**: Creates a game directory with subfolders (`base`, `def`, `maps`, `models`, `textures`, `sounds`, `scripts`, `guis`) and placeholder files (`gamex86.dll`/`gamex86.so`, `game.config`) for DarkRadiant.
- **Doom 3 /neo/game Directory**: Downloads `/neo/game` from [id-Software/DOOM-3](https://github.com/id-Software/DOOM-3) or a custom repo, providing C++ game logic.
- **Git Integration**: Initializes a Git repo with a `.gitignore` tracking only `/game`, ensuring no accidental asset commits.
- **Asset Packaging**: Packages assets into `.pk4` files for IDTECH4.
- **User-Friendly TUI**: Curses-based menu for project setup, .pk4 generation, Git init, and future tools.
- **Planned Tools (In Development)**:
  - *Main Menu Generator*: Creates animated menus with Bink video support (future external script).
  - *Asset Organizer*: Structures assets for seamless .pk4 integration (future external script).
- **FOSS Compliance**: Ensures GPL v3 for `/neo/game` modifications.

## Installation Instructions by Platform

### Linux
#### Arch Linux
```bash
sudo pacman -S git python base-devel cmake darkradiant
```

#### Debian/Ubuntu
```bash
sudo apt install git python3 build-essential cmake darkradiant
```

#### Fedora
```bash
sudo dnf install git python3 gcc-c++ cmake darkradiant
```

- **Compilation**:
  ```bash
  cd MyGame/game
  mkdir build && cd build
  cmake ..
  make
  ```

### macOS
```bash
brew install git python cmake darkradiant
```
- **Compilation**:
  ```bash
  cd MyGame/game
  mkdir build && cd build
  cmake -G Xcode ..
  xcodebuild
  ```

### Windows
- Install [Git](https://git-scm.com/download/win), [Python](https://www.python.org/downloads/windows/), [DarkRadiant](https://www.darkradiant.net/), [Visual Studio](https://visualstudio.microsoft.com/) with C++ tools, [DirectX SDK (June 2010)](https://www.microsoft.com/en-us/download/details.aspx?id=6812), and `windows-curses`:
  ```bash
  pip install windows-curses
  ```
- **Compilation**:
  - Open `neo/doom.sln` in Visual Studio, build `game` project for `gamex86.dll`.

### Dependencies
Install additional dependencies for external scripts:
```bash
pip install -r requirements.txt
```

## Project Structure
- `base/`: Core assets, .pk4 files (engine loads at runtime).
- `def/`: Entity definitions (e.g., `weapon.def`, spawns objects).
- `maps/`: Map files (e.g., `level1.map`, renders levels).
- `models/`: 3D models (e.g., `.md5mesh`, displays objects).
- `textures/`: Textures (e.g., `.dds`, skins models/maps).
- `sounds/`: Audio (e.g., `.wav`, `.ogg`, in-game sounds).
- `scripts/`: Scripts (e.g., `.script`, game logic).
- `guis/`: GUI files (e.g., `.gui`, menus/HUDs).
- `game/`: Doom 3 logic source (compiles to `gamex86.dll`/`so`).
- `tools/`: External scripts (e.g., `main_menu_generator.py`, in development).

The `.pk4` file in `base/` packages assets for efficient engine loading.

## Usage
1. Clone the repository:
   ```bash
   git clone https://github.com/ALH477/idtech4-project-packager.git
   ```
2. Navigate to the directory:
   ```bash
   cd idtech4-project-packager
   ```
3. Run the script:
   ```bash
   python create_idtech4_project.py
   ```
4. Use the TUI (arrow keys, Enter):
   - **Set up a new project**: Create structure, download `/neo/game`, init Git.
   - **Generate a .pk4 file**: Package assets into `.pk4`.
   - **Initialize Git for /game**: Track only game logic.
   - **Exit**: Quit.
   - *(Future)* Run external tools like main menu generator via TUI.

## Compilation
- **Linux/macOS**: `cmake` and `make` for `gamex86.so`.
- **Windows**: Visual Studio for `gamex86.dll` from `neo/doom.sln`.

## FOSS Compliance
Doom 3 `/neo/game` is GPL v3. Modifications must be open-source and shared if distributed.

## Contributing
Fork, branch, and PR! Add scripts to `tools/` (e.g., `main_menu_generator.py`) or enhance existing ones. Follow MIT/GPL v3 licenses.

## License
MIT License for this project. Doom 3 `/neo/game` is GPL v3. See `LICENSE` and [Doom 3 repo](https://github.com/id-Software/DOOM-3).

## Acknowledgements
- Created by [ALH477](https://github.com/ALH477) for [*PetaByte Madness™*](https://demod.ltd/petabytemadness.html) by [DeMoD LLC](https://demod.ltd).
- Uses [id-Software/DOOM-3](https://github.com/id-Software/DOOM-3) (GPL v3).
- Crafted with Grok by xAI for IDTECH4 accessibility.