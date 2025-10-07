# IDTECH4 Project Setup and .pk4/.sdb Packager
![Screenshot from 2025-04-21 02-52-28](https://github.com/user-attachments/assets/ba10b13a-86ba-4544-87be-f42365e3a7da)

This Python suite, created by [ALH477](https://x.com/demodllc), streamlines IDTECH4 engine development (e.g., Doom 3, Quake 4) with a modular set of tools, built to power [*PetaByte Madness™*](https://demod.ltd/petabytemadness.html) by [DeMoD LLC](https://demod.ltd) and shared to modernize IDTECH4 for all. Tailored for [DarkRadiant](https://www.darkradiant.net/), it offers project setup, asset packaging, and Git integration via a curses-based TUI, with external scripts for advanced features like main menu generation and asset organization. Licensed under MIT and GPL v3, it’s a FOSS beacon for IDTECH4’s niche.

## Features
- **Project Setup**: Creates a game directory with subfolders (`base`, `def`, `maps`, `models`, `textures`, `sounds`, `scripts`, `guis`) and placeholder files (`gamex86.dll`/`gamex86.so`, `game.config`) for DarkRadiant.
- **Doom 3 /neo/game Directory**: Downloads `/neo/game` from [id-Software/DOOM-3](https://github.com/id-Software/DOOM-3) or a custom repo, providing C++ game logic.
- **Git Integration**: Initializes a Git repo with a `.gitignore` tracking only `/game`, ensuring no accidental asset commits.
- **Asset Packaging**:
  - Packages assets into `.pk4` files (ZIP-based) for IDTECH4.
  - Packages assets into `.sdb` files (StreamDb format) with optional Snappy compression and path-based indexing via a reverse trie, optimized for IDTECH4 asset management.
- **User-Friendly TUI**: Curses-based menu for project setup, `.pk4` and `.sdb` generation, Git initialization, and future tools, with an enhanced loading animation for Git cloning.
- **Planned Tools (In Development)**:
  - *Main Menu Generator*: Creates animated menus with Bink video support (future external script).
  - *Asset Organizer*: Structures assets for seamless `.pk4` and `.sdb` integration (future external script).
- **FOSS Compliance**: Ensures GPL v3 for `/neo/game` modifications.

## Installation Instructions by Platform

### Linux
#### Arch Linux
```bash
sudo pacman -S git python base-devel cmake darkradiant python-snappy
```

#### Debian/Ubuntu
```bash
sudo apt install git python3 build-essential cmake darkradiant python3-snappy libsnappy-dev
```

#### Fedora
```bash
sudo dnf install git python3 gcc-c++ cmake darkradiant python3-snappy libsnappy-devel
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
brew install git python cmake darkradiant snappy
pip install python-snappy
```
- **Compilation**:
  ```bash
  cd MyGame/game
  mkdir build && cd build
  cmake -G Xcode ..
  xcodebuild
  ```

### Windows
- Install [Git](https://git-scm.com/download/win), [Python](https://www.python.org/downloads/windows/), [DarkRadiant](https://www.darkradiant.net/), [Visual Studio](https://visualstudio.microsoft.com/) with C++ tools, [DirectX SDK (June 2010)](https://www.microsoft.com/en-us/download/details.aspx?id=6812), and Python dependencies:
  ```bash
  pip install windows-curses python-snappy
  ```
- **Compilation**:
  - Open `neo/doom.sln` in Visual Studio, build `game` project for `gamex86.dll`.

### NixOS
Create a `shell.nix` in your project directory to set up a development environment with all dependencies:
```nix
{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    git
    python3
    (python3.withPackages (ps: with ps; [
      python-snappy
    ]))
    cmake
    darkradiant
  ];
}
```

Enter the environment:
```bash
nix-shell
```

Alternatively, for a Flake-based setup, create a `flake.nix`:
```nix
{
  description = "IDTECH4 Project Manager Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux"; # Adjust for your system (e.g., "aarch64-darwin")
      pkgs = import nixpkgs { inherit system; };
    in {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          git
          python3
          (python3.withPackages (ps: with ps; [
            python-snappy
          ]))
          cmake
          darkradiant
        ];
      };
    };
}
```

Enter the environment:
```bash
nix develop
```

- **Compilation**:
  ```bash
  cd MyGame/game
  mkdir build && cd build
  cmake ..
  make
  ```

## Project Structure
- `base/`: Core assets, `.pk4` or `.sdb` files (engine loads at runtime).
- `def/`: Entity definitions (e.g., `weapon.def`, spawns objects).
- `maps/`: Map files (e.g., `level1.map`, renders levels).
- `models/`: 3D models (e.g., `.md5mesh`, displays objects).
- `textures/`: Textures (e.g., `.dds`, skins models/maps).
- `sounds/`: Audio (e.g., `.wav`, `.ogg`, in-game sounds).
- `scripts/`: Scripts (e.g., `.script`, game logic).
- `guis/`: GUI files (e.g., `.gui`, menus/HUDs).
- `game/`: Doom 3 logic source (compiles to `gamex86.dll`/`so`).
- `tools/`: External scripts (e.g., `main_menu_generator.py`, in development).

The `.pk4` file (ZIP-based) or `.sdb` file (StreamDb format with path indexing and optional compression) in `base/` packages assets for efficient engine loading.

## StreamDB Integration
StreamDB is a custom, page-based, file-backed database designed for efficient asset storage and retrieval in IDTECH4 projects. It supports binary document storage with UUID indexing, path-based searches via a reverse trie, optional Snappy compression, and chained pages for large files. The script's TUI includes a ".sdb generation" option to package assets from the `base/` directory into a `.sdb` file, providing an alternative to `.pk4` with features like quick mode (skipping CRC checks for speed) and transaction support (in the full Rust implementation). This enables scalable, low-overhead asset management, particularly useful for real-time engines like IDTECH4.

The Python script implements a simplified version of StreamDB for packaging, while the full Rust implementation (integrated via FFI in IDTECH4 forks) adds advanced features like memory-mapped I/O, LRU caching, free lists, and recovery. StreamDB is part of DeMoD LLC's ecosystem, enhancing persistence in the DeMoD-LISP SDK and DCF for IoT, gaming, and multimedia applications.

## Usage
1. Clone the repository:
   ```bash
   git clone https://github.com/ALH477/CREATE_IDTECH4_PROJECT.git
   ```
2. Navigate to the directory:
   ```bash
   cd CREATE_IDTECH4_PROJECT
   ```
3. Run the script:
   ```bash
   python3 create_idtech4_project.py
   ```
4. Use the TUI (arrow keys, Enter):
   - **Set up a new project**: Create structure, download `/neo/game`, initialize Git.
   - **Generate a .pk4 file**: Package assets into `.pk4` (ZIP format).
   - **Initialize Git for /game**: Track only game logic.
   - **Generate a .sdb file**: Package assets into a StreamDb file with optional Snappy compression and path-based indexing.
   - **Exit**: Quit.
   - *(Future)* Run external tools like main menu generator via TUI.

## Compilation
- **Linux/macOS**: Use `cmake` and `make` for `gamex86.so`.
- **Windows**: Use Visual Studio to build `gamex86.dll` from `neo/doom.sln`.

## DeMoD LLC's Modernization of IDTech4 into DTech
DeMoD LLC, founded by the self-taught 22-year-old Asher LeRoy, is a bootstrapped IT/audio company specializing in real-time audio effects, generative FX, and Web3 asset trading for musicians, with a focus on empowering creators in Japan through AI, blockchain, and open-source tools. As part of their mission to democratize advanced technology, DeMoD has modernized the IDTech4 engine (from Doom 3) into a custom fork called DTech.

DTech enhances IDTech4 with:
- **DeMoD Communications Framework (DCF) Integration**: Replaces legacy UDP networking with DCF's low-latency, modular, P2P-enabled system supporting gRPC, UDP, and plugins for IoT/gaming interoperability.
- **StreamDB Asset Loading**: Substitutes traditional `.pk4` ZIP files with StreamDB, a page-based database for efficient, versioned asset storage with reverse trie indexing, Snappy compression, and streaming reads—optimized for embedded systems, servers, and cross-platform use.
- **Advanced Audio System**: Improves entity-based audio modes, DSP drivers, and sound processing for immersive horror FPS experiences, with robust error handling and dynamic mode switching based on proximity.
- **Export Compliance and Openness**: Ensures GPL-3.0 licensing, avoids encryption for EAR/ITAR compliance, and structures repositories for scalability across platforms (e.g., WASM compatibility).

This modernization transforms IDTech4 into a versatile engine for modern applications, blending retro gaming with cutting-edge tech for low-latency, fault-tolerant systems in music, IoT, and Web3.

## FOSS Compliance
Doom 3 `/neo/game` is licensed under GPL v3. Modifications must be open-source and shared if distributed.

## Contributing
Fork, branch, and submit a PR! Add scripts to `tools/` (e.g., `main_menu_generator.py`) or enhance existing ones. Follow MIT and GPL v3 licenses.

## License
MIT License for this project. Doom 3 `/neo/game` is GPL v3. See `LICENSE` and [Doom 3 repo](https://github.com/id-Software/DOOM-3).

## Acknowledgements
- Created by [ALH477](https://github.com/ALH477) for [*PetaByte Madness™*](https://demod.ltd/petabytemadness.html) by [DeMoD LLC](https://demod.ltd).
- Uses [id-Software/DOOM-3](https://github.com/id-Software/DOOM-3) (GPL v3).
- Crafted with Grok by xAI for IDTECH4 accessibility.
