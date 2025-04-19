import os
import subprocess
import zipfile
import tempfile
import shutil
import platform

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

def run_git_command(cmd, cwd=None):
    """
    Run a Git command with error handling.
    Args:
        cmd (list): List of command arguments.
        cwd (str): Working directory for the command.
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        subprocess.check_call(cmd, cwd=cwd, stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd)}")
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

def create_subfolders(project_dir, missing_subfolders):
    """
    Create missing subfolders if the user grants permission.
    Args:
        project_dir (str): Path to the project directory.
        missing_subfolders (list): List of missing subfolders.
    Returns:
        bool: True if subfolders were created or none were missing, False if user declined.
    """
    if not missing_subfolders:
        return True
    
    print("\nThe following required subfolders are missing:")
    print(", ".join(missing_subfolders))
    print("\nThese subfolders are needed for IDTECH4 and DarkRadiant:")
    print("- base: Core game assets (e.g., .pk4 files)")
    print("- def: Entity definitions (e.g., weapon.def)")
    print("- maps: Game maps (e.g., level1.map)")
    print("- models: 3D models (e.g., character.md5mesh)")
    print("- textures: Texture files (e.g., wall.dds)")
    print("- sounds: Audio files (e.g., shotgun.wav)")
    print("- scripts: Game scripts (e.g., game.script)")
    print("- guis: User interface files (e.g., mainmenu.gui)")
    
    while True:
        create = input("\nWould you like me to create these subfolders for you? (y/n): ").strip().lower()
        if create == 'y':
            try:
                for sub in missing_subfolders:
                    os.makedirs(os.path.join(project_dir, sub), exist_ok=True)
                print(f"\nCreated missing subfolders: {', '.join(missing_subfolders)}")
                return True
            except Exception as e:
                print(f"\nFailed to create subfolders. Error: {e}")
                return False
        elif create == 'n':
            print("\nPlease create the missing subfolders manually and rerun the script.")
            return False
        else:
            print("Please enter 'y' or 'n'.")

def create_game_files(project_dir):
    """
    Create placeholder game files (gamex86.dll/so, game.config) for DarkRadiant.
    Args:
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
    print("\nThe following game files are missing and needed for DarkRadiant:")
    print(", ".join(missing_files))
    while True:
        create = input("\nWould you like me to create these placeholder files? (y/n): ").strip().lower()
        if create == 'y':
            try:
                for file_name, content in game_files:
                    file_path = os.path.join(project_dir, file_name)
                    if not os.path.exists(file_path):
                        with open(file_path, 'w') as f:
                            f.write(content)
                print(f"\nCreated placeholder files: {', '.join(missing_files)}")
                return True
            except Exception as e:
                print(f"\nFailed to create game files. Error: {e}")
                return False
        elif create == 'n':
            print("\nPlease create these files manually and rerun the script.")
            return False
        else:
            print("Please enter 'y' or 'n'.")

def download_game_directory(project_dir, default_repo="https://github.com/id-Software/DOOM-3.git"):
    """
    Download the /neo/game directory from a GitHub repository using sparse checkout.
    Args:
        project_dir (str): Path to the project directory.
        default_repo (str): Default repository URL (Doom 3 source code).
    Returns:
        bool: True if successful or skipped, False if failed.
    """
    download = input("\nDo you want to download the /neo/game directory from a GitHub repository? (y/n): ").strip().lower()
    if download != 'y':
        print("Skipping download of /neo/game directory.")
        return True
    repo_url = input(f"Enter the GitHub repository URL (press Enter for default: {default_repo}): ").strip() or default_repo
    branch = input("Enter the branch name to download from (default: master): ").strip() or "master"
    destination = input("Enter the destination path for the /neo/game directory (relative to project directory, e.g., game): ").strip() or "game"
    destination_path = os.path.join(project_dir, destination)
    if os.path.exists(destination_path):
        overwrite = input(f"\n{destination_path} already exists. Overwrite? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("Skipping download to avoid overwriting existing directory.")
            return True
    temp_dir = tempfile.mkdtemp()
    try:
        if not run_git_command(["git", "init"], cwd=temp_dir) or \
           not run_git_command(["git", "config", "core.sparseCheckout", "true"], cwd=temp_dir):
            print("Failed to configure Git.")
            return False
        with open(os.path.join(temp_dir, ".git", "info", "sparse-checkout"), "w") as f:
            f.write("neo/game/\n")
        if not run_git_command(["git", "remote", "add", "origin", repo_url], cwd=temp_dir) or \
           not run_git_command(["git", "pull", "origin", branch], cwd=temp_dir):
            print("Failed to download repository.")
            return False
        game_dir = os.path.join(temp_dir, "neo", "game")
        if not os.path.isdir(game_dir):
            print("The /neo/game directory does not exist in the repository.")
            return False
        if os.path.exists(destination_path):
            shutil.rmtree(destination_path)
        shutil.copytree(game_dir, destination_path)
        print(f"\nCopied /neo/game directory to {destination_path}.")
        print("This contains the Doom 3 game logic source code (GPL v3). Keep modifications open-source!")
        return True
    except Exception as e:
        print(f"\nFailed to download /neo/game directory. Error: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def initialize_git_repo(project_dir):
    """
    Initialize a Git repository focused only on the /game directory.
    Creates a .gitignore file to ignore all other directories and files for clarity.
    Args:
        project_dir (str): Path to the project directory.
    Returns:
        bool: True if successful, False if failed.
    """
    git_init = input("\nWould you like to initialize a Git repository focused only on the /game directory? (y/n): ").strip().lower()
    if git_init != 'y':
        print("Skipping Git repository initialization.")
        return True
    
    game_dir = os.path.join(project_dir, "game")
    if not os.path.exists(game_dir):
        print(f"Error: {game_dir} does not exist. Please ensure the /game directory is present.")
        return False
    
    try:
        # Initialize Git repository
        if not run_git_command(["git", "init"], cwd=project_dir):
            print("Failed to initialize Git repository.")
            return False
        
        # Create .gitignore to ignore everything except /game
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
        
        # Add only the /game directory to the repository
        run_git_command(["git", "add", "game"], cwd=project_dir)
        run_git_command(["git", "commit", "-m", "Initial commit: Add /game directory for IDTECH4 game logic"], cwd=project_dir)
        print("\nInitialized Git repository and committed the /game directory.")
        print("Only the /game directory will be tracked, ensuring full clarity of what is pushed.")
        print("Use 'git push' to share to GitHub.")
        return True
    except Exception as e:
        print(f"\nFailed to initialize Git repository. Error: {e}")
        return False

def print_platform_instructions():
    """
    Print platform-specific setup instructions based on the detected OS.
    """
    os_type = platform.system()
    print("\nPlatform-Specific Setup Instructions:")
    if os_type == "Linux":
        print("### Linux")
        print("Detected Linux—excellent choice!")
        print("- Compile the game binary (`gamex86.so`):")
        print("  ```bash")
        print("  cd MyGame/game")
        print("  mkdir build && cd build")
        print("  cmake ..")
        print("  make")
        print("  ```")
    elif os_type == "Darwin":
        print("### macOS")
        print("Detected macOS—shiny!")
        print("  ```bash")
        print("  cd MyGame/game")
        print("  mkdir build && cd build")
        print("  cmake -G Xcode ..")
        print("  xcodebuild")
        print("  ```")
    elif os_type == "Windows":
        print("### Windows")
        print("Detected Windows—sorry about that!")
        print("- Install Visual Studio and the DirectX SDK.")
        print("- Open neo/doom.sln and build the `game` project.")
    else:
        print("### Unknown OS")
        print("Install a C++ compiler and compile the /game directory.")

def setup_project():
    """
    Set up a new IDTECH4 project, including directory structure, placeholder files, and optional Git initialization.
    """
    print("\n--- Setting Up a New Project ---")
    while True:
        project_dir = input("Enter the path to your project directory (e.g., MyGame): ").strip()
        if not os.path.exists(project_dir):
            create = input(f"\n{project_dir} does not exist. Create it? (y/n): ").strip().lower()
            if create == 'y':
                try:
                    os.makedirs(project_dir, exist_ok=True)
                    print(f"\nCreated project directory: {project_dir}")
                    break
                except Exception as e:
                    print(f"\nFailed to create directory. Error: {e}")
            elif create == 'n':
                print("Please enter a valid directory path.")
            else:
                print("Please enter 'y' or 'n'.")
        else:
            break
    expected_subfolders = ['base', 'def', 'maps', 'models', 'textures', 'sounds', 'scripts', 'guis']
    missing = check_subfolders(project_dir, expected_subfolders)
    if missing and not create_subfolders(project_dir, missing):
        return False
    if not create_game_files(project_dir):
        return False
    if not download_game_directory(project_dir):
        return False
    if not initialize_git_repo(project_dir):
        print("\nGit setup failed, but you can continue without it.")
    print_platform_instructions()
    print("\nProject setup complete!")
    return True

def generate_pk4():
    """
    Generate a .pk4 file from the project's assets.
    """
    print("\n--- Generating a .pk4 File ---")
    project_dir = input("Enter the project directory path: ").strip()
    if not os.path.exists(project_dir):
        print(f"Error: {project_dir} does not exist.")
        return False
    asset_dir = os.path.join(project_dir, 'base')
    if not os.path.exists(asset_dir):
        print(f"Error: {asset_dir} does not exist.")
        return False
    pk4_name = input("Enter the .pk4 file name (e.g., mygame.pk4): ").strip()
    if not pk4_name.endswith('.pk4'):
        pk4_name += '.pk4'
    output_path = input(f"Enter the output path for the .pk4 file (press Enter for default '{asset_dir}'): ").strip()
    output_path = os.path.join(asset_dir, pk4_name) if not output_path else os.path.join(output_path, pk4_name)
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
        print(f"\nSuccess! Packaged {file_count} files into {output_path}.")
        return True
    except Exception as e:
        print(f"\nFailed to create .pk4. Error: {e}")
        return False

def main():
    """
    Main TUI loop for the IDTECH4 Project Manager.
    """
    if not check_git_installed():
        exit()
    print("Welcome to the IDTECH4 Project Manager!")
    while True:
        print("\nMenu Options:")
        print("1. Set up a new project - Create a project structure for IDTECH4.")
        print("2. Generate a .pk4 file - Package your assets into a .pk4 file.")
        print("3. Initialize Git repository for /game directory - Track only the game logic source code.")
        print("4. Exit - Quit the script.")
        choice = input("Enter your choice (1-4): ").strip()
        if choice == '1':
            setup_project()
        elif choice == '2':
            generate_pk4()
        elif choice == '3':
            project_dir = input("Enter the project directory path: ").strip()
            if not os.path.exists(project_dir):
                print(f"Error: {project_dir} does not exist.")
            else:
                initialize_git_repo(project_dir)
        elif choice == '4':
            print("Exiting. Have a great day!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")
        another = input("\nDo you want to perform another action? (y/n): ").strip().lower()
        if another != 'y':
            print("Exiting. Have a great day!")
            break

if __name__ == "__main__":
    main()