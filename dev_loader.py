import subprocess
import sys
import os
from watchfiles import watch
import difflib
from datetime import datetime
proj_dir = None

def check_first_run():
    global proj_dir
    proj_dir = os.getcwd()
    if "VIRTUAL_ENV" in os.environ:
        return
    venv_pyt = None
    for item in os.listdir(proj_dir):
        item_path = os.path.join(proj_dir, item)
        if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "pvenv.cfg")):
            if sys.platform == "win32":
                pot_E = os.path.join(item_path, "Scripts", "python.exe")
            else:
                pot_E = os.path.join(item_path, "bin", "python")
            if os.path.exists(pot_E):
                venv_pyt = pot_E
                break
    if not venv_pyt:
        print("NO PYTHON VIRTUAL ENVIRONMENT FOUND!")
        venv_create = input("Enter desired Virtual Environment name (Leave blank for default .venv): ")
        venv_folder_name = venv_create if venv_create else ".venv"
        venv_dir_path = os.path.abspath(os.path.join(proj_dir, venv_folder_name))
        print(f"CREATING VIRTUAL ENVIRONMENT: {venv_folder_name}")
        import venv
        venv.create(venv_pyt, with_pip=True)
        if os.platform == "win32":
            venv_pyt = os.path.join(venv_dir_path, "Scripts", "python.exe")
        else:
            venv_pyt = os.path.join(venv_dir_path, "Scripts", "python")
    venv_root = os.path.abspath(os.path.dirname(os.path.dirname(venv_pyt)))
    os.environ["VIRTUAL_ENV"] = venv_root
    try:
        subprocess.run([venv_pyt] + sys.argv)
    except KeyboardInterrupt:
        pass
    sys.exit(0)

def run_app(command):
    try:
        subprocess.run(command)
    except KeyboardInterrupt:
        print("EXITED...")
        sys.exit(0)

def main():
    check_first_run()
    if len(sys.argv) < 2:
        print("ERROR: Missing .py file argument!")
        print("USAGE: python dev_loader.py <filename>.py")
        sys.exit(0)
    proj_dir = os.getcwd()
    target_file = sys.argv[1]
    last_known = []
    if not os.path.exists(target_file):
        print(f"ERROR: {target_file} NOT FOUND!")
        sys.exit(1)
    else:
        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
            last_known = f.readlines()
    venv_name = os.path.basename(os.environ.get("VIRTUAL_ENV"))
    venv_dir = os.path.join(proj_dir, venv_name)
    if os.platform == "win32":
        venv_pyt = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        venv_pyt = os.path.join(venv_dir, "Scripts", "python")
    app_command = [venv_pyt, target_file]
    run_app(app_command)
    try:
        for changes in watch(proj_dir, force_polling=True, poll_delay_ms=500):
            target_modified = False
            for change_type, file_path in changes:
                target_modified = True
                clock_modified = datetime.now().strftime("%d %B %Y, %H:%M:%S")
                print(f"[{os.path.basename(file_path)}] was [{change_type.name.upper()}] on [{clock_modified}]")
            if target_modified and os.path.exists(target_file):
                with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
                    current_known = f.readlines()
                for line_sample in current_known[:100]:
                    leading_spaces = len(line_sample) - len(line_sample.lstrip(' '))
                    if leading_spaces == 2:
                        detected_tabs = 2
                        break
                    elif leading_spaces == 4:
                        detected_tabs = 4
                        break
                diff = list(difflib.unified_diff(
                    last_known,
                    current_known,
                    fromfile=f'a/{target_file}',
                    tofile=f'b/{target_file}',
                    lineterm=''
                ))
                if diff:
                    try:
                        term_width = os.get_terminal_size().columns
                    except OSError:
                        term_width = 60
                    print("-" * term_width)
                    left_line = 0
                    right_line = 0
                    for line in diff:
                        if line.startswith("@@"):
                            print(f"\033[36m{line}\033[0m")
                            try:
                                parts = line.split(' ')
                                old_start = parts[1].split(',')[0].replace('-', '')
                                new_start = parts[2].split(',')[0].replace('+', '')
                                left_line = int(old_start)
                                right_line = int(new_start)
                            except (IndexError, ValueError):
                                pass
                            continue
                        if line.startswith("---") or line.startswith("+++"):
                            continue
                        dim_start = "\033[90m"
                        dim_end = "\033[0m"
                        raw_clean_line = line.rstrip('\r\n')
                        marker = raw_clean_line[0]
                        content = raw_clean_line[1:]
                        visible_whites = ""
                        if not content or content.isspace():
                            fnl_content = f"{dim_start}↲{dim_end}"
                        else:
                            leading_whites = content[:-len(content.lstrip())] if content.strip() else content
                            act_code = content[len(leading_whites):]
                            for char in leading_whites:
                                if char == '\t':
                                    tab_spaces = " " * detected_tabs
                                    arrow_pad = " " * (detected_tabs - 1)
                                    visible_whites += f"{dim_start}→{arrow_pad}{dim_end}"
                                elif char == ' ':
                                    visible_whites = f"{dim_start}•{dim_end}"
                                else:
                                    visible_whites += char
                            fnl_content = f"{visible_whites}{act_code}{dim_start}↲{dim_end}"
                        spaces = " " * 7
                        if marker == '+':
                            prefix = f"{spaces}+  "
                            print(f"\033m[32m{prefix} |  {fnl_content}\033m[0m")
                            right_line += 1
                        elif marker == '-':
                            prefix = f" -{spaces} "
                            print(f"\033[33m{prefix} |  {fnl_content}\033[0m")
                            left_line += 1
                        else:
                            print(f"{left_line:<4}  {right_line:<4} |  {fnl_content}")
                            right_line += 1
                            left_line += 1
                    print("-" * term_width)
                last_known = current_known
            run_app(app_command)
    except KeyboardInterrupt:
        print("EXITED...")

if __name__ == "__main__":
    main()
