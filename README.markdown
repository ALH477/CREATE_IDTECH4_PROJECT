# IDTECH4 Project Setup and .pk4 Packager

This Python script, created by [ALH477](https://github.com/ALH477), simplifies setting up a new game project for the IDTECH4 engine (e.g., Doom 3, Quake 4) and packaging assets into `.pk4` files. It was developed to streamline the creation of [*PetaByte Madness™*](https://demod.ltd) by [DeMoD LLC](https://demod.ltd), and is shared to make IDTECH4 development more accessible. Tailored for developers using [DarkRadiant](https://www.darkradiant.net/), it provides a project structure, placeholder files, and the option to download the Doom 3 `/neo/game` directory for game logic. The script also initializes a Git repository to streamline development and ensure FOSS compliance under the GPL v3 license.

## Features
- **Project Setup**: Creates a game directory with subfolders (`base`, `def`, `maps`, `models`, `textures`, `sounds`, `scripts`, `guis`) and placeholder files (`gamex86.dll`/`gamex86.so`, `game.config`) for DarkRadiant.
- **Doom 3 /neo/game Directory**: Downloads the `/neo/game` directory from [id-Software/DOOM-3](https://github.com/id-Software/DOOM-3) (default) or a user-specified repository, providing C++ code for game logic.
- **Git Integration**: Initializes a Git repository with a `.gitignore` focused on the `/game` directory, committing only the game logic source code to prevent accidental inclusion of assets.
- **Asset Packaging**: Packages assets into a `.pk4` file with the correct structure for the IDTECH4 engine.
- **FOSS Compliance**: Ensures compliance with the GPL v3 license for Doom 3 source code modifications.
- **User-Friendly TUI**: Offers a text-based menu to choose between setting up a project, generating a `.pk4` file, initializing a Git repository, or exiting.

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
  - Compile the game binary (`gamex86.so`):
    ```bash
    cd MyGame/game
    mkdir build && cd build
    cmake ..
    make
    ```

### macOS
- **Install Dependencies**:
  ```bash
  brew install git python cmake darkradiant
  ```
- **Compilation**:
  - Generate an Xcode project and build `gamex86.so`:
    ```bash
    cd MyGame/game
    mkdir build && cd build
    cmake -G Xcode ..
    xcodebuild
    ```

### Windows
- **Install Dependencies**:
  - Download and install [Git](https://git-scm.com/download/win).
  - Download and install [Python](https://www.python.org/downloads/windows/).
  - Download and install [DarkRadiant](https://www.darkradiant.net/).
  - Install [Visual Studio](https://visualstudio.microsoft.com/) with C++ development tools.
  - Install the [DirectX SDK (June 2010)](https://www.microsoft.com/en-us/download/details.aspx?id=6812).
- **Compilation**:
  - Open `neo/doom.sln` in Visual Studio.
  - Build the `game` project to generate `gamex86.dll`.

## Project Structure and Subfolder Usage

The IDTECH4 engine expects a specific directory structure for game assets and logic. Below is an explanation of each subfolder and how the engine utilizes the files within them:

- **`base/`**: 
  - **Purpose**: Stores the core game assets, including `.pk4` files (packaged assets).
  - **Engine Usage**: The engine loads `.pk4` files from this directory as the primary source of game content during runtime.
- **`def/`**: 
  - **Purpose**: Contains entity definition files (e.g., `weapon.def`).
  - **Engine Usage**: Defines properties and behaviors for game entities like weapons, enemies, and items, which the engine interprets to spawn and manage objects.
- **`maps/`**: 
  - **Purpose**: Holds map files (e.g., `level1.map`) designed in DarkRadiant.
  - **Engine Usage**: The engine loads these files to render game levels and environments.
- **`models/`**: 
  - **Purpose**: Contains 3D model files (e.g., `.md5mesh`) for characters, props, and environments.
  - **Engine Usage**: The engine uses these files to display 3D objects in the game world.
- **`textures/`**: 
  - **Purpose**: Houses texture files (e.g., `.dds`) applied to models and surfaces.
  - **Engine Usage**: The engine applies these textures to enhance the visual appearance of models and maps.
- **`sounds/`**: 
  - **Purpose**: Includes audio files (e.g., `.wav`, `.ogg`) for sound effects and music.
  - **Engine Usage**: The engine plays these files for in-game audio cues and background music.
- **`scripts/`**: 
  - **Purpose**: Contains script files (e.g., `.script`) for game logic and events.
  - **Engine Usage**: The engine executes these scripts to control gameplay mechanics and interactions.
- **`guis/`**: 
  - **Purpose**: Holds GUI files (e.g., `.gui`) for menus, HUDs, and in-game interfaces.
  - **Engine Usage**: The engine renders these files to display user interfaces.
- **`game/`**: 
  - **Purpose**: Contains the Doom 3 game logic source code (from `/neo/game`).
  - **Engine Usage**: Compiled into `gamex86.dll` or `gamex86.so`, this provides the core gameplay logic that the engine executes.

The `.pk4` file, typically placed in `base/`, packages these assets into a single archive, which the IDTECH4 engine unpacks and utilizes for efficient loading and distribution.

## Usage
1. Clone or download this repository:
   ```bash
   git clone https://github.com/ALH477/CREATE_IDTECH4_PROJECT.git
   ```
2. Navigate to the project directory:
   ```bash
   cd idtech4-project-packager
   ```
3. Run the script:
   ```bash
   python create_idtech4_project.py
   ```
4. Use the TUI to:
   - **Set up a new project**: Create the project structure, download `/neo/game`, and initialize a Git repository.
   - **Generate a .pk4 file**: Package assets into a `.pk4` file for distribution.
   - **Initialize Git repository for /game directory**: Track only the `/game` directory to avoid committing assets.
   - **Exit**: Quit the script.

## Compilation Instructions
- **Linux/macOS**: Use CMake to build `gamex86.so` from the `/game` directory.
- **Windows**: Use Visual Studio to build `gamex86.dll` from `neo/doom.sln`.

## FOSS Compliance
The Doom 3 source code is under GPL v3. Any modifications to `/neo/game` must remain open-source. Share your changes if distributed.

## Contributing
Contributions are welcome! Fork the repo, create a feature branch, and open a pull request.

## License
This project is under the MIT License. The Doom 3 `/neo/game` directory is under GPL v3, requiring any modifications to be FOSS. See the `LICENSE` file and the Doom 3 repository for details.

## Acknowledgements
- Created by [ALH477](https://github.com/ALH477) to streamline development of [*PetaByte Madness™*](https://demod.ltd/petabytemadness.html) by [DeMoD LLC](https://demod.ltd).
- Uses the Doom 3 source code from [id-Software/DOOM-3](https://github.com/id-Software/DOOM-3) (GPL v3).
- Script and README crafted with assistance from Grok, created by xAI, to make IDTECH4 development accessible.
