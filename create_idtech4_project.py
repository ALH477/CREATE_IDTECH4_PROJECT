import os
import subprocess
import zipfile
import tempfile
import shutil
import platform
import curses
import time
import threading
import logging
import re
import queue
try:
    import windows_curses  # For Windows compatibility
except ImportError:
    pass

import struct
import snappy
import uuid
import hashlib
import binascii

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MAGIC = b'\x55\xAA\xFE\xED\xFA\xCE\xDA\x7A'
PAGE_SIZE = 4096
PAGE_HEADER_SIZE = 32
FLAG_DATA_PAGE = 0x01
FLAG_TRIE_PAGE = 0x02
FLAG_FREE_LIST_PAGE = 0x04
FLAG_INDEX_PAGE = 0x08
HEADER_SIZE = 8 + 3 * (8 + 4)  # MAGIC + 3*(i64 + i32)

class ReverseTrieNode:
    def __init__(self, edge='', parent_page_id=-1, self_page_id=-1, document_id=None, children=None):
        self.edge = edge
        self.parent_page_id = parent_page_id
        self.self_page_id = self_page_id
        self.document_id = document_id
        self.children = children or {}

class Document:
    def __init__(self, id, first_page_id, current_version=0, paths=None):
        self.id = id
        self.first_page_id = first_page_id
        self.current_version = current_version
        self.paths = paths or []

class StreamDb:
    def __init__(self, path, use_compression=True):
        self.file = open(path, 'wb+')
        self.use_compression = use_compression
        self.page_size = PAGE_SIZE
        self.page_header_size = PAGE_HEADER_SIZE
        self.current_page_id = 0
        self.documents = {}  # uuid to Document
        self.trie_root_page_id = -1
        self.index_page_id = -1
        self._write_initial_header()

    def _write_initial_header(self):
        self.file.seek(0)
        self.file.write(MAGIC)
        self.file.write(struct.pack('<q i q i q i', -1, 0, -1, 0, -1, 0))
        self.file.flush()

    def allocate_page(self):
        page_id = self.current_page_id
        self.current_page_id += 1
        return page_id

    def write_raw_page(self, page_id, data, flags, version=0, prev_page_id=-1, next_page_id=-1):
        compressed = snappy.compress(data) if self.use_compression else data
        crc = binascii.crc32(compressed) & 0xffffffff
        data_length = len(compressed)
        header = struct.pack('<I i q q B i B B B', crc, version, prev_page_id, next_page_id, flags, data_length, 0, 0, 0)
        offset = HEADER_SIZE + page_id * self.page_size
        self.file.seek(offset)
        self.file.write(header)
        self.file.write(compressed)
        self.file.flush()

    def write_document(self, path, data):
        id = uuid.uuid4()
        first_page_id = -1
        prev_page_id = -1
        data_pos = 0
        max_chunk = self.page_size - self.page_header_size
        while data_pos < len(data):
            chunk_end = min(data_pos + max_chunk, len(data))
            chunk = data[data_pos:chunk_end]
            page_id = self.allocate_page()
            next_page_id = -1 if chunk_end == len(data) else self.allocate_page()
            self.write_raw_page(page_id, chunk, FLAG_DATA_PAGE, 0, prev_page_id, next_page_id)
            if first_page_id == -1:
                first_page_id = page_id
            prev_page_id = page_id
            data_pos = chunk_end
        doc = Document(id, first_page_id, 0, [path])
        self.documents[id] = doc
        self._trie_insert(path, id)

    def _trie_insert(self, path, doc_id):
        reversed_path = path[::-1]
        if self.trie_root_page_id == -1:
            self.trie_root_page_id = self.allocate_page()
            root_node = ReverseTrieNode('', -1, self.trie_root_page_id)
            self._write_trie_node(self.trie_root_page_id, root_node)
        current = self.trie_root_page_id
        remaining = reversed_path
        while remaining:
            node = self._read_trie_node(current)
            edge = node.edge
            common = 0
            min_len = min(len(remaining), len(edge))
            while common < min_len and remaining[common] == edge[common]:
                common += 1
            if common == len(edge):
                remaining = remaining[common:]
                if not remaining:
                    node.document_id = doc_id
                    self._write_trie_node(current, node)
                    return
                ch = remaining[0]
                if ch in node.children:
                    current = node.children[ch]
                else:
                    new_page = self.allocate_page()
                    new_node = ReverseTrieNode(remaining[1:], current, new_page, doc_id if len(remaining) == 1 else None)
                    self._write_trie_node(new_page, new_node)
                    node.children[ch] = new_page
                    self._write_trie_node(current, node)
                    return
            elif common == 0:
                ch = remaining[0]
                new_page = self.allocate_page()
                new_node = ReverseTrieNode(remaining[1:], current, new_page, doc_id if len(remaining) == 1 else None)
                self._write_trie_node(new_page, new_node)
                node.children[ch] = new_page
                self._write_trie_node(current, node)
                return
            else:
                # Split node
                split_node = ReverseTrieNode(edge[:common], node.parent_page_id, current, None, {edge[common]: node.self_page_id})
                suffix_page = self.allocate_page()
                suffix_node = ReverseTrieNode(edge[common:], current, suffix_page, node.document_id, node.children)
                self._write_trie_node(suffix_page, suffix_node)
                split_node.children[edge[common]] = suffix_page
                if node.parent_page_id != -1:
                    parent = self._read_trie_node(node.parent_page_id)
                    for k in list(parent.children.keys()):
                        if parent.children[k] == current:
                            parent.children[k] = current  # unchanged
                    self._write_trie_node(node.parent_page_id, parent)
                self._write_trie_node(current, split_node)
                remaining = remaining[common:]
                if not remaining:
                    split_node.document_id = doc_id
                    self._write_trie_node(current, split_node)
                    return
                ch = remaining[0]
                new_page = self.allocate_page()
                new_node = ReverseTrieNode(remaining[1:], current, new_page, doc_id if len(remaining) == 1 else None)
                self._write_trie_node(new_page, new_node)
                split_node.children[ch] = new_page
                self._write_trie_node(current, split_node)
                return

    def _serialize_trie_node(self, node):
        buf = b''
        edge_bytes = node.edge.encode('utf-8')
        buf += struct.pack('<i', len(edge_bytes))
        buf += edge_bytes
        buf += struct.pack('<q', node.parent_page_id)
        buf += struct.pack('<q', node.self_page_id)
        buf += struct.pack('<i', 1 if node.document_id else 0)
        if node.document_id:
            buf += node.document_id.bytes
        buf += struct.pack('<i', len(node.children))
        for ch, child_id in sorted(node.children.items()):
            buf += ch.encode('utf-8')
            buf += struct.pack('<q', child_id)
        return buf

    def _deserialize_trie_node(self, data):
        reader = 0
        edge_len = struct.unpack_from('<i', data, reader)[0]
        reader += 4
        edge = data[reader:reader + edge_len].decode('utf-8')
        reader += edge_len
        parent = struct.unpack_from('<q', data, reader)[0]
        reader += 8
        self_id = struct.unpack_from('<q', data, reader)[0]
        reader += 8
        has_doc = struct.unpack_from('<i', data, reader)[0]
        reader += 4
        doc_id = None
        if has_doc:
            doc_id = uuid.UUID(bytes=data[reader:reader + 16])
            reader += 16
        child_count = struct.unpack_from('<i', data, reader)[0]
        reader += 4
        children = {}
        for _ in range(child_count):
            ch = data[reader:reader + 1].decode('utf-8')
            reader += 1
            child_id = struct.unpack_from('<q', data, reader)[0]
            reader += 8
            children[ch] = child_id
        return ReverseTrieNode(edge, parent, self_id, doc_id, children)

    def _write_trie_node(self, page_id, node):
        data = self._serialize_trie_node(node)
        self.write_raw_page(page_id, data, FLAG_TRIE_PAGE)

    def _read_trie_node(self, page_id):
        offset = HEADER_SIZE + page_id * self.page_size + self.page_header_size
        self.file.seek(offset)
        compressed = self.file.read(self.page_size - self.page_header_size)
        data = snappy.decompress(compressed) if self.use_compression else compressed
        return self._deserialize_trie_node(data)

    def close(self):
        # Write index
        self.index_page_id = self.allocate_page()
        serialized_index = self._serialize_index()
        self.write_raw_page(self.index_page_id, serialized_index, FLAG_INDEX_PAGE)
        # Update header
        self.file.seek(len(MAGIC))
        self.file.write(struct.pack('<q i', self.index_page_id, 0))
        self.file.write(struct.pack('<q i', self.trie_root_page_id, 0))
        self.file.write(struct.pack('<q i', -1, 0))
        self.file.flush()
        self.file.close()

    def _serialize_index(self):
        buf = b''
        buf += struct.pack('<i', len(self.documents))
        for id, doc in sorted(self.documents.items(), key=lambda x: x[0]):
            buf += doc.id.bytes
            buf += struct.pack('<q', doc.first_page_id)
            buf += struct.pack('<i', doc.current_version)
            buf += struct.pack('<i', len(doc.paths))
            for p in doc.paths:
                p_bytes = p.encode('utf-8')
                buf += struct.pack('<i', len(p_bytes))
                buf += p_bytes
        return buf

def check_git_installed():
    try:
        subprocess.check_output(["git", "--version"], stderr=subprocess.STDOUT)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Git is not installed. Please install Git to use this script.")
        print("Download Git from: https://git-scm.com/downloads")
        return False

def run_git_command(cmd, cwd=None, timeout=60):
    try:
        subprocess.run(cmd, cwd=cwd, check=True, stderr=subprocess.STDOUT, timeout=timeout)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logger.error(f"Error running command: {' '.join(cmd)} - {e}")
        if hasattr(e, 'output'):
            logger.error(e.output.decode())
        return False

def check_subfolders(project_dir, expected_subfolders):
    missing = []
    for sub in expected_subfolders:
        sub_path = os.path.join(project_dir, sub)
        if not os.path.isdir(sub_path):
            missing.append(sub)
    return missing

def create_subfolders(stdscr, project_dir, missing_subfolders):
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
                logger.info(f"Created subfolders in {project_dir}: {missing_subfolders}")
                return True
            except Exception as e:
                stdscr.addstr(14, 0, f"Failed to create subfolders. Error: {e}")
                stdscr.addstr(15, 0, "Press any key to continue...")
                stdscr.refresh()
                stdscr.getch()
                logger.error(f"Failed to create subfolders in {project_dir}: {e}")
                return False
        elif key in (ord('n'), ord('N')):
            stdscr.addstr(14, 0, "Please create subfolders manually and retry.")
            stdscr.addstr(15, 0, "Press any key to continue...")
            stdscr.refresh()
            stdscr.getch()
            return False

def create_game_files(stdscr, project_dir):
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
                logger.info(f"Created game files in {project_dir}: {missing_files}")
                return True
            except Exception as e:
                stdscr.addstr(7, 0, f"Failed to create files. Error: {e}")
                stdscr.addstr(8, 0, "Press any key to continue...")
                stdscr.refresh()
                stdscr.getch()
                logger.error(f"Failed to create game files in {project_dir}: {e}")
                return False
        elif key in (ord('n'), ord('N')):
            stdscr.addstr(7, 0, "Please create files manually and retry.")
            stdscr.addstr(8, 0, "Press any key to continue...")
            stdscr.refresh()
            stdscr.getch()
            return False

def download_game_directory(stdscr, project_dir, default_repo="https://github.com/id-Software/DOOM-3.git"):
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
    if not repo_url.startswith('https://'):
        repo_url = 'https://' + repo_url.lstrip('http://')
        stdscr.addstr(2, 0, f"Adjusted to HTTPS: {repo_url}")
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
    stdscr.addstr(0, 0, "Cloning /neo/game from GitHub...   0%")
    stdscr.refresh()
    
    success = False
    error_msg = None
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            if not run_git_command(["git", "init"], cwd=temp_dir) or \
               not run_git_command(["git", "config", "core.sparseCheckout", "true"], cwd=temp_dir):
                error_msg = "Failed to configure Git."
                raise Exception(error_msg)
            with open(os.path.join(temp_dir, ".git", "info", "sparse-checkout"), "w") as f:
                f.write("neo/game/\n")
            if not run_git_command(["git", "remote", "add", "origin", repo_url], cwd=temp_dir):
                error_msg = "Failed to add remote."
                raise Exception(error_msg)
            
            # Run git pull with Popen for real-time output
            cmd = ["git", "pull", "origin", branch]
            process = subprocess.Popen(cmd, cwd=temp_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            q = queue.Queue()
            def read_output():
                for line in iter(process.stdout.readline, ''):
                    q.put(line)
                q.put(None)  # Sentinel for end
            thread = threading.Thread(target=read_output)
            thread.start()
            
            animation_running = True
            spinner_chars = ['|', '/', '-', '\\']
            spinner_idx = 0
            progress = 0
            last_line = ""
            progress_re = re.compile(r'Receiving objects:\s*(\d+)%')
            
            while animation_running:
                try:
                    line = q.get(timeout=0.2)
                    if line is None:
                        animation_running = False
                        break
                    last_line = line.strip()[:curses.COLS-1]
                    stdscr.addstr(1, 0, " " * (curses.COLS - 1))  # Clear line
                    stdscr.addstr(1, 0, last_line)
                    match = progress_re.search(line)
                    if match:
                        new_progress = int(match.group(1))
                        if new_progress > progress:
                            progress = new_progress
                except queue.Empty:
                    pass
                
                # Update spinner and progress
                stdscr.addstr(0, 0, " " * (curses.COLS - 1))  # Clear status line
                status = f"Cloning /neo/game from GitHub... {spinner_chars[spinner_idx]} {progress}%"
                stdscr.addstr(0, 0, status)
                stdscr.refresh()
                spinner_idx = (spinner_idx + 1) % len(spinner_chars)
            
            thread.join()
            process.wait()
            if process.returncode != 0:
                error_msg = "Failed to pull repository."
                raise Exception(error_msg)
            
            game_dir = os.path.join(temp_dir, "neo", "game")
            if not os.path.isdir(game_dir):
                error_msg = "/neo/game directory not found in repository."
                raise Exception(error_msg)
            if os.path.exists(destination_path):
                shutil.rmtree(destination_path)
            shutil.copytree(game_dir, destination_path)
            success = True
            logger.info(f"Downloaded /neo/game to {destination_path}")
        except Exception as e:
            error_msg = f"Failed to download /neo/game. Error: {e}"
            logger.error(error_msg)
    
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
        logger.info(f"Initialized Git repo in {project_dir}")
        return True
    except Exception as e:
        stdscr.addstr(2, 0, f"Failed to initialize Git repo. Error: {e}")
        stdscr.addstr(3, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        logger.error(f"Failed to initialize Git repo in {project_dir}: {e}")
        return False

def print_platform_instructions(stdscr):
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

def validate_project_dir(project_dir):
    abs_path = os.path.abspath(project_dir)
    cwd = os.getcwd()
    if not abs_path.startswith(cwd):
        logger.warning(f"Project dir {project_dir} is not a subdirectory of {cwd}")
        return None
    return abs_path

def setup_project(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, "--- Setting Up a New Project ---")
    stdscr.addstr(2, 0, "Enter project directory path (e.g., MyGame): ")
    curses.echo()
    project_dir_input = stdscr.getstr(3, 0).decode().strip()
    curses.noecho()
    project_dir = validate_project_dir(project_dir_input)
    if project_dir is None:
        stdscr.addstr(5, 0, "Invalid project directory: Must be relative to current working directory.")
        stdscr.addstr(6, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        return False
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
                    logger.info(f"Created project directory: {project_dir}")
                    break
                except Exception as e:
                    stdscr.addstr(7, 0, f"Failed to create directory. Error: {e}")
                    stdscr.addstr(8, 0, "Press any key to continue...")
                    stdscr.refresh()
                    stdscr.getch()
                    logger.error(f"Failed to create project directory {project_dir}: {e}")
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
    stdscr.clear()
    stdscr.addstr(0, 0, "--- Generating a .pk4 File ---")
    stdscr.addstr(2, 0, "Enter project directory path: ")
    curses.echo()
    project_dir_input = stdscr.getstr(3, 0).decode().strip()
    curses.noecho()
    project_dir = validate_project_dir(project_dir_input)
    if project_dir is None:
        stdscr.addstr(5, 0, "Invalid project directory: Must be relative to current working directory.")
        stdscr.addstr(6, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        return False
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
    output_path_input = stdscr.getstr(9, 0).decode().strip()
    output_path = os.path.join(asset_dir, pk4_name) if not output_path_input else validate_project_dir(output_path_input)
    if output_path is None:
        stdscr.addstr(10, 0, "Invalid output path.")
        stdscr.addstr(11, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        return False
    output_path = os.path.join(output_path, pk4_name) if output_path_input else output_path
    curses.noecho()
    exclude_dirs = ['.git', '__pycache__', '.DS_Store']
    exclude_exts = ['.bak', '.tmp', '.log']
    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            file_count = 0
            for root, dirs, files in os.walk(asset_dir):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                for file in files:
                    if any(file.endswith(ext) for ext in exclude_exts):
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, asset_dir)
                    zf.write(file_path, arcname)
                    file_count += 1
        stdscr.addstr(11, 0, f"Success! Packaged {file_count} files into {output_path}.")
        stdscr.addstr(12, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        logger.info(f"Generated PK4: {output_path} with {file_count} files")
        return True
    except Exception as e:
        stdscr.addstr(11, 0, f"Failed to create .pk4. Error: {e}")
        stdscr.addstr(12, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        logger.error(f"Failed to generate PK4 {output_path}: {e}")
        return False

def generate_sdb(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, "--- Generating a .sdb File ---")
    stdscr.addstr(2, 0, "Enter project directory path: ")
    curses.echo()
    project_dir_input = stdscr.getstr(3, 0).decode().strip()
    curses.noecho()
    project_dir = validate_project_dir(project_dir_input)
    if project_dir is None:
        stdscr.addstr(5, 0, "Invalid project directory: Must be relative to current working directory.")
        stdscr.addstr(6, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        return False
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
    stdscr.addstr(5, 0, "Enter .sdb file name (e.g., mygame.sdb): ")
    curses.echo()
    sdb_name = stdscr.getstr(6, 0).decode().strip()
    if not sdb_name.endswith('.sdb'):
        sdb_name += '.sdb'
    stdscr.addstr(8, 0, f"Enter output path for .sdb (Enter for default '{asset_dir}'): ")
    output_path_input = stdscr.getstr(9, 0).decode().strip()
    output_dir = validate_project_dir(output_path_input) if output_path_input else asset_dir
    if output_dir is None:
        stdscr.addstr(10, 0, "Invalid output path.")
        stdscr.addstr(11, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        return False
    output_path = os.path.join(output_dir, sdb_name)
    stdscr.addstr(11, 0, "Use compression? (y/n): ")
    stdscr.refresh()
    while True:
        key = stdscr.getch()
        if key in (ord('y'), ord('Y'), ord('n'), ord('N')):
            use_compression = key in (ord('y'), ord('Y'))
            break
    curses.noecho()
    exclude_dirs = ['.git', '__pycache__', '.DS_Store']
    exclude_exts = ['.bak', '.tmp', '.log']
    try:
        db = StreamDb(output_path, use_compression)
        file_count = 0
        for root, dirs, files in os.walk(asset_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if any(file.endswith(ext) for ext in exclude_exts):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, asset_dir).replace('\\', '/')
                with open(file_path, 'rb') as f:
                    data = f.read()
                db.write_document(arcname, data)
                file_count += 1
        db.close()
        stdscr.addstr(13, 0, f"Success! Packaged {file_count} files into {output_path}.")
        stdscr.addstr(14, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        logger.info(f"Generated SDB: {output_path} with {file_count} files")
        return True
    except Exception as e:
        stdscr.addstr(13, 0, f"Failed to create .sdb. Error: {e}")
        stdscr.addstr(14, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        logger.error(f"Failed to generate SDB {output_path}: {e}")
        return False

def curses_menu(stdscr):
    curses.curs_set(0)
    stdscr.timeout(-1)
    menu_items = [
        "1. Set up a new project - Create a project structure for IDTECH4",
        "2. Generate a .pk4 file - Package your assets into a .pk4 file",
        "3. Initialize Git repository for /game directory - Track only game logic",
        "4. Generate a .sdb file - Package your assets into a StreamDb file",
        "5. Exit - Quit the script"
    ]
    current_row = 0
    
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
        for i, line in enumerate(sierpinski.splitlines()):
            stdscr.addstr(i, 0, line)
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
                project_dir_input = stdscr.getstr(1, 0).decode().strip()
                curses.noecho()
                project_dir = validate_project_dir(project_dir_input)
                if project_dir is None or not os.path.exists(project_dir):
                    stdscr.addstr(3, 0, f"Error: Invalid or non-existent directory: {project_dir_input}")
                    stdscr.addstr(4, 0, "Press any key to continue...")
                    stdscr.refresh()
                    stdscr.getch()
                else:
                    initialize_git_repo(stdscr, project_dir)
            elif current_row == 3:
                generate_sdb(stdscr)
            elif current_row == 4:
                break

def main():
    if not check_git_installed():
        exit()
    try:
        curses.wrapper(curses_menu)
    except Exception as e:
        logger.error(f"Error running curses TUI: {e}")
        print(f"Error running TUI: {e}. Falling back to command-line mode.")
        print("Welcome to IDTECH4 Project Manager (Fallback Mode)")
        print("1. Set up a new project")
        print("2. Generate a .pk4 file")
        print("3. Initialize Git repo for /game")
        print("4. Generate a .sdb file")
        print("5. Exit")
        choice = input("Enter choice: ")
        if choice == '1':
            project_dir = input("Enter project directory: ")
            print("Setup not fully supported in fallback. Please use TUI.")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
