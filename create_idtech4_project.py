import os
import subprocess
import zipfile
import tempfile
import shutil
import platform
import curses
import time
import threading
try:
    import windows_curses  # For Windows compatibility
except ImportError:
    pass

def check_git_installed():
    """
    Check if Git is installed on the system.
    Returns:
        bool: True if Git is installed, False otherwise.
    """
    try:
        subprocess.check_output(["git", "--version"], stderr=subprocess.STDOUT)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Git is not installed. Please install Git to use this script.")
        print("Download Git from: https://git-scm.com/downloads")
        return False

def run_git_command(cmd, cwd=None, timeout=60):
    """
    Run a Git command with error handling and timeout.
    Args:
        cmd (list): List of command arguments.
        cwd (str): Working directory for the command.
        timeout (int): Timeout in seconds.
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        subprocess.run(cmd, cwd=cwd, check=True, stderr=subprocess.STDOUT, timeout=timeout)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"Error running command: {' '.join(cmd)}")
        if hasattr(e, 'output'):
            print(e.output.decode())
        return False

def check_subfolders(project_dir, expected_subfolders):
    """
    Check if the project directory contains the required subfolders.
    Args:
        project_dir (str): Path to the project directory.
        expected_subfolders (list): List of required subfolders.
    Returns:
        list: Missing subfolders, if any.
    """
    missing = []
    for sub in expected_subfolders:
        sub_path = os.path.join(project_dir, sub)
        if not os.path.isdir(sub_path):
            missing.append(sub)
    return missing

def create_subfolders(stdscr, project_dir, missing_subfolders):
    """
    Create missing subfolders with curses-based user input.
    Args:
        stdscr: Curses screen object.
        project_dir (str): Path to the project directory.
        missing_subfolders (list): List of missing subfolders.
    Returns:
        bool: True if subfolders were created or none were missing, False if user declined.
    """
    if not missing_subfolders:
        return True
    
    stdscr.clear()
    stdscr.addstr(0, 0, "Missing required subfolders: " + ", ".join(missing_subfolders))
    stdscr.addstr(2, 0, "These subfolders are needed for IDTECH4 and DarkRadiant:")
    stdscr.addstr(3, 0, "- base: Core game assets (e.g., .pk4 files)")
    stdscr.addstr(4, 0, "- def: Entity definitions (e.g., weapon.def)")
    stdscr.addstr(5, 0, "- maps: Game maps (e.g., level1.map)")
    stdscr.addstr(6, 0, "- models: 3D models (e.g., character.md5mesh)")
    stdscr.addstr(7, 0, "- textures: Texture files (e.g., wall.dds)")
    stdscr.addstr(8, 0, "- sounds: Audio files (e.g., shotgun.wav)")
    stdscr.addstr(9, 0, "- scripts: Game scripts (e.g., game.script)")
    stdscr.addstr(10, 0, "- guis: User interface files (e.g., mainmenu.gui)")
    stdscr.addstr(12, 0, "Create these subfolders? (y/n): ")
    stdscr.refresh()
    
    while True:
        key = stdscr.getch()
        if key in (ord('y'), ord('Y')):
            try:
                for sub in missing_subfolders:
                    os.makedirs(os.path.join(project_dir, sub), exist_ok=True)
                stdscr.addstr(14, 0, f"Created subfolders: {', '.join(missing_subfolders)}")
                stdscr.addstr(15, 0, "Press any key to continue...")
                stdscr.refresh()
                stdscr.getch()
                return True
            except Exception as e:
                stdscr.addstr(14, 0, f"Failed to create subfolders. Error: {e}")
                stdscr.addstr(15, 0, "Press any key to continue...")
                stdscr.refresh()
                stdscr.getch()
                return False
        elif key in (ord('n'), ord('N')):
            stdscr.addstr(14, 0, "Please create subfolders manually and retry.")
            stdscr.addstr(15, 0, "Press any key to continue...")
            stdscr.refresh()
            stdscr.getch()
            return False

def create_game_files(stdscr, project_dir):
    """
    Create placeholder game files with curses-based user input.
    Args:
        stdscr: Curses screen object.
        project_dir (str): Path to the project directory.
    Returns:
        bool: True if files were created or exist, False if user declined or error occurred.
    """
    os_type = platform.system()
    game_binary = 'gamex86.dll' if os_type == 'Windows' else 'gamex86.so'
    game_files = [
        (game_binary, "# Placeholder game binary\n# Replace with your compiled game binary\n# Compile from the /game directory source code"),
        ('game.config', f"// Basic game configuration for DarkRadiant\nfs_game base\nfs_basepath {project_dir}")
    ]
    missing_files = [file_name for file_name, _ in game_files if not os.path.exists(os.path.join(project_dir, file_name))]
    if not missing_files:
        return True
    
    stdscr.clear()
    stdscr.addstr(0, 0, "Missing game files needed for DarkRadiant: " + ", ".join(missing_files))
    stdscr.addstr(2, 0, f"- {game_binary}: Placeholder binary (replace later).")
    stdscr.addstr(3, 0, "- game.config: Configures DarkRadiant for assets.")
    stdscr.addstr(5, 0, "Create these placeholder files? (y/n): ")
    stdscr.refresh()
    
    while True:
        key = stdscr.getch()
        if key in (ord('y'), ord('Y')):
            try:
                for file_name, content in game_files:
                    file_path = os.path.join(project_dir, file_name)
                    if not os.path.exists(file_path):
                        with open(file_path, 'w') as f:
                            f.write(content)
                stdscr.addstr(7, 0, f"Created files: {', '.join(missing_files)}")
                stdscr.addstr(8, 0, "Press any key to continue...")
                stdscr.refresh()
                stdscr.getch()
                return True
            except Exception as e:
                stdscr.addstr(7, 0, f"Failed to create files. Error: {e}")
                stdscr.addstr(8, 0, "Press any key to continue...")
                stdscr.refresh()
                stdscr.getch()
                return False
        elif key in (ord('n'), ord('N')):
            stdscr.addstr(7, 0, "Please create files manually and retry.")
            stdscr.addstr(8, 0, "Press any key to continue...")
            stdscr.refresh()
            stdscr.getch()
            return False

def download_game_directory(stdscr, project_dir, default_repo="https://github.com/id-Software/DOOM-3.git"):
    """
    Download the /neo/game directory with curses-based user input and percentage updates.
    Args:
        stdscr: Curses screen object.
        project_dir (str): Path to the project directory.
        default_repo (str): Default repository URL (Doom 3 source code).
    Returns:
        bool: True if successful or skipped, False if failed.
    """
    stdscr.clear()
    stdscr.addstr(0, 0, "Download /neo/game directory from GitHub? (y/n): ")
    stdscr.refresh()
    
    while True:
        key = stdscr.getch()
        if key in (ord('y'), ord('Y')):
            break
        elif key in (ord('n'), ord('N')):
            stdscr.addstr(2, 0, "Skipping download of /neo/game directory.")
            stdscr.addstr(3, 0, "Press any key to continue...")
            stdscr.refresh()
            stdscr.getch()
            return True
    
    stdscr.clear()
    stdscr.addstr(0, 0, f"Enter GitHub repo URL (Enter for default: {default_repo}): ")
    curses.echo()
    repo_url = stdscr.getstr(1, 0).decode().strip() or default_repo
    stdscr.addstr(3, 0, "Enter branch name (default: master): ")
    branch = stdscr.getstr(4, 0).decode().strip() or "master"
    stdscr.addstr(6, 0, "Enter path for /neo/game (relative, e.g., game): ")
    destination = stdscr.getstr(7, 0).decode().strip() or "game"
    curses.noecho()
    destination_path = os.path.join(project_dir, destination)
    
    if os.path.exists(destination_path):
        stdscr.addstr(9, 0, f"{destination_path} exists. Overwrite? (y/n): ")
        stdscr.refresh()
        while True:
            key = stdscr.getch()
            if key in (ord('y'), ord('Y')):
                break
            elif key in (ord('n'), ord('N')):
                stdscr.addstr(11, 0, "Skipping download to avoid overwriting.")
                stdscr.addstr(12, 0, "Press any key to continue...")
                stdscr.refresh()
                stdscr.getch()
                return True
    
    stdscr.clear()
    stdscr.addstr(0, 0, "Cloning /neo/game from GitHub... 0%")
    stdscr.refresh()
    
    # Percentage updates at 25% intervals
    progress = 0
    success = False
    error_msg = None
    temp_dir = tempfile.mkdtemp()
    
    def run_clone():
        nonlocal success, error_msg
        try:
            if not run_git_command(["git", "init"], cwd=temp_dir) or \
               not run_git_command(["git", "config", "core.sparseCheckout", "true"], cwd=temp_dir):
                error_msg = "Failed to configure Git."
                return
            with open(os.path.join(temp_dir, ".git", "info", "sparse-checkout"), "w") as f:
                f.write("neo/game/\n")
            if not run_git_command(["git", "remote", "add", "origin", repo_url], cwd=temp_dir) or \
               not run_git_command(["git", "pull", "origin", branch], cwd=temp_dir, timeout=120):
                error_msg = "Failed to download repository."
                return
            game_dir = os.path.join(temp_dir, "neo", "game")
            if not os.path.isdir(game_dir):
                error_msg = "/neo/game directory not found in repository."
                return
            if os.path.exists(destination_path):
                shutil.rmtree(destination_path)
            shutil.copytree(game_dir, destination_path)
            success = True
        except Exception as e:
            error_msg = f"Failed to download /neo/game. Error: {e}"
    
    # Start cloning in a separate thread
    clone_thread = threading.Thread(target=run_clone)
    clone_thread.start()
    
    # Display percentage updates at 25% intervals
    start_time = time.time()
    last_percent = 0
    while clone_thread.is_alive():
        elapsed = time.time() - start_time
        progress = min(int(elapsed * 10), 100)  # Fake progress: 10% per second, max 100%
        current_percent = (progress // 25) * 25  # Round down to nearest 25%
        if current_percent > last_percent and current_percent in [25, 50, 75, 100]:
            last_percent = current_percent
            stdscr.clear()
            stdscr.addstr(0, 0, f"Cloning /neo/game from GitHub... {current_percent}%")
            stdscr.refresh()
        time.sleep(0.1)
    
    clone_thread.join()
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    stdscr.clear()
    if success:
        stdscr.addstr(0, 0, f"Copied /neo/game to {destination_path}.")
        stdscr.addstr(1, 0, "This is Doom 3 game logic source (GPL v3). Keep mods open-source!")
    else:
        stdscr.addstr(0, 0, error_msg or "Unknown error during cloning.")
    stdscr.addstr(3, 0, "Press any key to continue...")
    stdscr.refresh()
    stdscr.getch()
    return success

def initialize_git_repo(stdscr, project_dir):
    """
    Initialize a Git repository for /game directory with curses-based input.
    Args:
        stdscr: Curses screen object.
        project_dir (str): Path to the project directory.
    Returns:
        bool: True if successful, False if failed.
    """
    stdscr.clear()
    stdscr.addstr(0, 0, "Initialize Git repo for /game directory only? (y/n): ")
    stdscr.refresh()
    
    while True:
        key = stdscr.getch()
        if key in (ord('y'), ord('Y')):
            break
        elif key in (ord('n'), ord('N')):
            stdscr.addstr(2, 0, "Skipping Git repository initialization.")
            stdscr.addstr(3, 0, "Press any key to continue...")
            stdscr.refresh()
            stdscr.getch()
            return True
    
    game_dir = os.path.join(project_dir, "game")
    if not os.path.exists(game_dir):
        stdscr.addstr(2, 0, f"Error: {game_dir} does not exist. Ensure /game is present.")
        stdscr.addstr(3, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        return False
    
    try:
        if not run_git_command(["git", "init"], cwd=project_dir):
            stdscr.addstr(2, 0, "Failed to initialize Git repository.")
            stdscr.addstr(3, 0, "Press any key to continue...")
            stdscr.refresh()
            stdscr.getch()
            return False
        
        gitignore_content = """\
# Ignore everything by default
*

# Include only the /game directory and its contents
!/game
!/game/**
"""
        gitignore_path = os.path.join(project_dir, ".gitignore")
        with open(gitignore_path, "w") as f:
            f.write(gitignore_content)
        
        run_git_command(["git", "add", "game"], cwd=project_dir)
        run_git_command(["git", "commit", "-m", "Initial commit: Add /game directory for IDTECH4 game logic"], cwd=project_dir)
        stdscr.addstr(2, 0, "Initialized Git repo and committed /game directory.")
        stdscr.addstr(3, 0, "Only /game will be tracked, ensuring clarity for pushes.")
        stdscr.addstr(4, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        return True
    except Exception as e:
        stdscr.addstr(2, 0, f"Failed to initialize Git repo. Error: {e}")
        stdscr.addstr(3, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        return False

def print_platform_instructions(stdscr):
    """
    Print platform-specific setup instructions.
    Args:
        stdscr: Curses screen object.
    """
    os_type = platform.system()
    stdscr.clear()
    stdscr.addstr(0, 0, "Platform-Specific Setup Instructions:")
    if os_type == "Linux":
        stdscr.addstr(2, 0, "Linux (The One True Path)")
        stdscr.addstr(3, 0, "- Compile gamex86.so:")
        stdscr.addstr(4, 0, "  cd MyGame/game")
        stdscr.addstr(5, 0, "  mkdir build && cd build")
        stdscr.addstr(6, 0, "  cmake ..")
        stdscr.addstr(7, 0, "  make")
    elif os_type == "Darwin":
        stdscr.addstr(2, 0, "macOS (Fancy but FOSS)")
        stdscr.addstr(3, 0, "- Compile gamex86.so:")
        stdscr.addstr(4, 0, "  cd MyGame/game")
        stdscr.addstr(5, 0, "  mkdir build && cd build")
        stdscr.addstr(6, 0, "  cmake -G Xcode ..")
        stdscr.addstr(7, 0, "  xcodebuild")
    elif os_type == "Windows":
        stdscr.addstr(2, 0, "Windows (Ugh, really?)")
        stdscr.addstr(3, 0, "- Install Visual Studio & DirectX SDK.")
        stdscr.addstr(4, 0, "- Open neo/doom.sln, build `game` project.")
    else:
        stdscr.addstr(2, 0, "Unknown OS")
        stdscr.addstr(3, 0, "Install C++ compiler, compile /game.")
    stdscr.addstr(9, 0, "Press any key to continue...")
    stdscr.refresh()
    stdscr.getch()

def setup_project(stdscr):
    """
    Set up a new IDTECH4 project with curses-based input.
    Args:
        stdscr: Curses screen object.
    Returns:
        bool: True if successful, False if failed.
    """
    stdscr.clear()
    stdscr.addstr(0, 0, "--- Setting Up a New Project ---")
    stdscr.addstr(2, 0, "Enter project directory path (e.g., MyGame): ")
    curses.echo()
    project_dir = stdscr.getstr(3, 0).decode().strip()
    curses.noecho()
    if not os.path.exists(project_dir):
        stdscr.addstr(5, 0, f"{project_dir} does not exist. Create it? (y/n): ")
        stdscr.refresh()
        while True:
            key = stdscr.getch()
            if key in (ord('y'), ord('Y')):
                try:
                    os.makedirs(project_dir, exist_ok=True)
                    stdscr.addstr(7, 0, f"Created project directory: {project_dir}")
                    stdscr.addstr(8, 0, "Press any key to continue...")
                    stdscr.refresh()
                    stdscr.getch()
                    break
                except Exception as e:
                    stdscr.addstr(7, 0, f"Failed to create directory. Error: {e}")
                    stdscr.addstr(8, 0, "Press any key to continue...")
                    stdscr.refresh()
                    stdscr.getch()
                    return False
            elif key in (ord('n'), ord('N')):
                stdscr.addstr(7, 0, "Please enter a valid directory path.")
                stdscr.addstr(8, 0, "Press any key to continue...")
                stdscr.refresh()
                stdscr.getch()
                return False
    
    expected_subfolders = ['base', 'def', 'maps', 'models', 'textures', 'sounds', 'scripts', 'guis']
    missing = check_subfolders(project_dir, expected_subfolders)
    if missing and not create_subfolders(stdscr, project_dir, missing):
        return False
    if not create_game_files(stdscr, project_dir):
        return False
    if not download_game_directory(stdscr, project_dir):
        return False
    if not initialize_git_repo(stdscr, project_dir):
        stdscr.addstr(0, 0, "Git setup failed, but you can continue.")
        stdscr.addstr(1, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
    print_platform_instructions(stdscr)
    stdscr.clear()
    stdscr.addstr(0, 0, "Project setup complete!")
    stdscr.addstr(1, 0, "Press any key to continue...")
    stdscr.refresh()
    stdscr.getch()
    return True

def generate_pk4(stdscr):
    """
    Generate a .pk4 file with curses-based input.
    Args:
        stdscr: Curses screen object.
    Returns:
        bool: True if successful, False if failed.
    """
    stdscr.clear()
    stdscr.addstr(0, 0, "--- Generating a .pk4 File ---")
    stdscr.addstr(2, 0, "Enter project directory path: ")
    curses.echo()
    project_dir = stdscr.getstr(3, 0).decode().strip()
    curses.noecho()
    if not os.path.exists(project_dir):
        stdscr.addstr(5, 0, f"Error: {project_dir} does not exist.")
        stdscr.addstr(6, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        return False
    asset_dir = os.path.join(project_dir, 'base')
    if not os.path.exists(asset_dir):
        stdscr.addstr(5, 0, f"Error: {asset_dir} does not exist.")
        stdscr.addstr(6, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        return False
    stdscr.addstr(5, 0, "Enter .pk4 file name (e.g., mygame.pk4): ")
    curses.echo()
    pk4_name = stdscr.getstr(6, 0).decode().strip()
    if not pk4_name.endswith('.pk4'):
        pk4_name += '.pk4'
    stdscr.addstr(8, 0, f"Enter output path for .pk4 (Enter for default '{asset_dir}'): ")
    output_path = stdscr.getstr(9, 0).decode().strip()
    output_path = os.path.join(asset_dir, pk4_name) if not output_path else os.path.join(output_path, pk4_name)
    curses.noecho()
    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            file_count = 0
            for root, _, files in os.walk(asset_dir):
                for file in files:
                    if file.endswith(('.bak', '.tmp', '.log')):
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, asset_dir)
                    zf.write(file_path, arcname)
                    file_count += 1
        stdscr.addstr(11, 0, f"Success! Packaged {file_count} files into {output_path}.")
        stdscr.addstr(12, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        return True
    except Exception as e:
        stdscr.addstr(11, 0, f"Failed to create .pk4. Error: {e}")
        stdscr.addstr(12, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        return False

# Placeholder functions for future external scripts (commented out)
"""
def convert_assets(stdscr):
    # Placeholder for asset conversion tool (e.g., PNG to .dds, FBX to .md5mesh)
    stdscr.clear()
    stdscr.addstr(0, 0, "--- Converting Assets ---")
    stdscr.addstr(2, 0, "Not implemented yet. Check future commits!")
    stdscr.addstr(3, 0, "Press any key to continue...")
    stdscr.refresh()
    stdscr.getch()
    return False

def generate_scripts(stdscr):
    # Placeholder for script generation tool (e.g., .script files for weapons, AI)
    stdscr.clear()
    stdscr.addstr(0, 0, "--- Generating Scripts ---")
    stdscr.addstr(2, 0, "Not implemented yet. Check future commits!")
    stdscr.addstr(3, 0, "Press any key to continue...")
    stdscr.refresh()
    stdscr.getch()
    return False

def edit_maps(stdscr):
    # Placeholder for map editing tool (e.g., procedural .map generation)
    stdscr.clear()
    stdscr.addstr(0, 0, "--- Editing Maps ---")
    stdscr.addstr(2, 0, "Not implemented yet. Check future commits!")
    stdscr.addstr(3, 0, "Press any key to continue...")
    stdscr.refresh()
    stdscr.getch()
    return False

def manage_entities(stdscr):
    # Placeholder for entity management tool (e.g., .def file editing)
    stdscr.clear()
    stdscr.addstr(0, 0, "--- Managing Entities ---")
    stdscr.addstr(2, 0, "Not implemented yet. Check future commits!")
    stdscr.addstr(3, 0, "Press any key to continue...")
    stdscr.refresh()
    stdscr.getch()
    return False

def build_binary(stdscr):
    # Placeholder for build automation tool (e.g., compile gamex86.so/.dll)
    stdscr.clear()
    stdscr.addstr(0, 0, "--- Building Binary ---")
    stdscr.addstr(2, 0, "Not implemented yet. Check future commits!")
    stdscr.addstr(3, 0, "Press any key to continue...")
    stdscr.refresh()
    stdscr.getch()
    return False
"""

def curses_menu(stdscr):
    """
    Main curses TUI loop with ASCII Sierpinski triangle.
    Args:
        stdscr: Curses screen object.
    """
    curses.curs_set(0)
    stdscr.timeout(-1)
    menu_items = [
        "1. Set up a new project - Create a project structure for IDTECH4",
        "2. Generate a .pk4 file - Package your assets into a .pk4 file",
        "3. Initialize Git repository for /game directory - Track only game logic",
        "4. Exit - Quit the script"
        # Placeholder menu items for future tools
        #"5. Convert assets - Convert PNG to .dds, FBX to .md5mesh",
        #"6. Generate scripts - Create .script files for weapons, AI",
        #"7. Edit maps - Procedural .map file generation",
        #"8. Manage entities - Edit .def files for entities",
        #"9. Build binary - Compile gamex86.so or .dll"
    ]
    current_row = 0
    
    # ASCII Sierpinski triangle (8 lines, provided by ALH477)
    sierpinski = """\
        /\\
       /__\\
      /\\  /\\
     /__\\/__\\
    /\\      /\\
   /__\\    /__\\
  /\\  /\\  /\\  /\\
 /__\\/__\\/__\\/__\\
"""
    
    while True:
        stdscr.clear()
        # Display Sierpinski triangle
        for i, line in enumerate(sierpinski.splitlines()):
            stdscr.addstr(i, 0, line)
        # Display menu below triangle
        stdscr.addstr(10, 0, "Welcome to the IDTECH4 Project Manager!")
        stdscr.addstr(11, 0, "Built for PetaByte Madness™ by DeMoD LLC")
        stdscr.addstr(12, 0, "Use arrow keys to navigate, Enter to select")
        
        for idx, item in enumerate(menu_items):
            if idx == current_row:
                stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(14 + idx, 0, item)
                stdscr.attroff(curses.A_REVERSE)
            else:
                stdscr.addstr(14 + idx, 0, item)
        
        stdscr.refresh()
        key = stdscr.getch()
        
        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(menu_items) - 1:
            current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if current_row == 0:
                setup_project(stdscr)
            elif current_row == 1:
                generate_pk4(stdscr)
            elif current_row == 2:
                stdscr.clear()
                stdscr.addstr(0, 0, "Enter project directory path: ")
                curses.echo()
                project_dir = stdscr.getstr(1, 0).decode().strip()
                curses.noecho()
                if not os.path.exists(project_dir):
                    stdscr.addstr(3, 0, f"Error: {project_dir} does not exist.")
                    stdscr.addstr(4, 0, "Press any key to continue...")
                    stdscr.refresh()
                    stdscr.getch()
                else:
                    initialize_git_repo(stdscr, project_dir)
            elif current_row == 3:
                break
            # Placeholder calls for future tools
            #elif current_row == 4:
            #    convert_assets(stdscr)
            #elif current_row == 5:
            #    generate_scripts(stdscr)
            #elif current_row == 6:
            #    edit_maps(stdscr)
            #elif current_row == 7:
            #    manage_entities(stdscr)
            #elif current_row == 8:
            #    build_binary(stdscr)

def main():
    """
    Main entry point for the IDTECH4 Project Manager.
    """
    if not check_git_installed():
        exit()
    try:
        curses.wrapper(curses_menu)
    except Exception as e:
        print(f"Error running curses TUI: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
