# -*- coding: utf-8 -*-
#
# gdb-frontend is a easy, flexible and extensionable gui debugger
#
# https://github.com/rohanrhu/gdb-frontend
# https://oguzhaneroglu.com/projects/gdb-frontend/
#
# Licensed under GNU/GPLv3
# Copyright (C) 2019, Oğuzhan Eroğlu (https://oguzhaneroglu.com/) <rohanrhu2@gmail.com>

import os
import sys
import shutil
import json
import base64
import subprocess
import time
import re
import signal
import platform
import webbrowser
import atexit

import config
config.init()

import statics
import util
import api.globalvars

import api.globalvars
api.globalvars.init()

path = os.path.dirname(os.path.realpath(__file__))

gdb_args = ""
gdb_executable = "gdb"
tmux_executable = "tmux"
terminal_id = "gdb-frontend"
api.globalvars.terminal_id = terminal_id
credentials = False
is_random_port = False

arg_config = {}
arg_config["TERMINAL_ID"] = terminal_id

config.WORKDIR = os.getcwd()
arg_config["WORKDIR"] = config.WORKDIR

terminate_sub_procs = True

dontopenuionstartup = False

def argHandler_gdbArgs(args):
    global gdb_args

    gdb_args = args

def argHandler_gdbExecutable(path):
    global gdb_executable

    if not os.path.exists(path):
        print("[Error] GDB executable: "+path+" not found.\n")
        exit(0)

    gdb_executable = path

def argHandler_tmuxExecutable(path):
    global tmux_executable

    if not os.path.exists(path):
        print("[Error] Tmux executable: "+path+" not found.\n")
        exit(0)

    tmux_executable = path

def argHandler_tmuxArgs(args):
    global tmux_args

    tmux_args = " " + str.strip(args) + " "

def argHandler_terminalId(name):
    global terminal_id

    terminal_id = name
    api.globalvars.terminal_id = terminal_id
    arg_config["TERMINAL_ID"] = terminal_id

def argHandler_credentials(_credentials):
    global credentials

    if ":" not in _credentials:
        print("[Error] Credentials format must be such as USER:PASS.\n")
        exit(0)

    credentials = _credentials

    arg_config["CREDENTIALS"] = credentials
    config.CREDENTIALS = credentials

def argHandler_host(address):
    arg_config["HOST_ADDRESS"] = address
    config.HOST_ADDRESS = address

def argHandler_listen(address):
    arg_config["BIND_ADDRESS"] = address
    config.BIND_ADDRESS = address

def argHandler_port(port):
    global is_random_port
    
    port = int(port)

    if port == 0:
        is_random_port = True
        arg_config["HTTP_PORT"] = 0
        config.HTTP_PORT = 0
    else:
        arg_config["HTTP_PORT"] = port
        config.HTTP_PORT = port

def argHandler_readonly():
    arg_config["IS_READONLY"] = True
    config.IS_READONLY = True

def argHandler_workdir(path):
    arg_config["WORKDIR"] = path
    config.WORKDIR = path

def argHandler_pluginsDir(path):
    arg_config["PLUGINS_DIR"] = path
    config.PLUGINS_DIR = path

def argHandler_verbose():
    config.VERBOSE = True
    arg_config["VERBOSE"] = True

def argHandler_dontopenuionstartup():
    global dontopenuionstartup
    dontopenuionstartup = True

def argHandler_urlBase(path):
    arg_config["URL_BASE"] = path
    config.URL_BASE = path

def argHandler_help():
    global gdb_executable

    print("GDBFrontend is a easy, flexible and extensionable gui debugger.\n")
    print("Options:")
    print("  --help, -h:\t\t\t\t\tShows this help message.")
    print("  --version, -v:\t\t\t\tShows version.")
    print("  --gdb-args=\"ARGS\", -G \"ARGS\":\t\t\tSpecifies GDB command line arguments. (Optional)")
    print("  --gdb-executable=PATH, -g PATH:\t\tSpecifies GDB executable path (Default is \"gdb\" command on PATH environment variable.)")
    print("  --tmux-executable=PATH, -tmux PATH:\t\tSpecifies Tmux executable path (Default is \"tmux\" command on PATH environment variable.)")
    print("  --terminal-id=NAME, -t NAME:\t\t\tSpecifies tmux terminal identifier name (Default is \"gdb-frontend\".)")
    print("  --credentials=USER:PASS, -c USER:PASS:\tSpecifies username and password for accessing to debugger.")
    print("  --host=IP, -H IP:\t\t\t\tSpecifies current host address that you can access via for HTTP and WS servers.")
    print("  --listen=IP, -l IP:\t\t\t\tSpecifies listen address for HTTP and WS servers.")
    print("  --port=PORT, -p PORT:\t\t\t\tSpecifies HTTP port. (0 for random port.)")
    print("  --url-base=PATH, -u PATH:\t\t\tSpecifies URL base path. (Default: /)")
    print("  --readonly, -r:\t\t\t\tMakes code editor readonly. (Notice: This option is not related to security.)")
    print("  --workdir, -w:\t\t\t\tSpecifies working directory.")
    print("  --plugin-dir, -P:\t\t\t\tSpecifies plugins directory.")
    print("  --dontopenuionstartup, -D:\t\t\tAvoids opening UI just after startup.")
    print("  --verbose, -V:\t\t\t\tEnables verbose output.")
    print("")

    exit(0)

def argHandler_version():
    global gdb_executable

    print("GDBFrontend is a easy, flexible and extensionable gui debugger.\n")
    print("Version: " + util.versionString(statics.VERSION))
    print("")

    exit(0)

def quit_tmux_gdb():
    global tmux_executable
    global terminal_id
    
    proc = subprocess.Popen([
        tmux_executable,
        "list-panes", 
        "-t",
        terminal_id,
        "-F",
        "\"#{pane_pid}\""
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    proc.wait()

    tmux_bash_pid = False

    try:
        tmux_bash_pid = int(re.search("(\\d+)", proc.stdout.readline().__str__())[0])
    except Exception as e:
        print("[Error] Tmux Bash PID is not found.", e)
    
    if tmux_bash_pid:
        print("Sending SIGKILL to PGID: %s." % tmux_bash_pid)

        try:
            os.killpg(tmux_bash_pid, signal.SIGKILL)
        except Exception as e:
            print("[Error] Process group can not stopped with SIGKILL.", e)

args = [
    ["--verbose", "-V", argHandler_verbose, False],
    ["--gdb-args", "-G", argHandler_gdbArgs, True],
    ["--gdb-executable", "-g", argHandler_gdbExecutable, True],
    ["--tmux-executable", "-tmux", argHandler_tmuxExecutable, True],
    ["--terminal-id", "-t", argHandler_terminalId, True],
    ["--credentials", "-c", argHandler_credentials, True],
    ["--host", "-H", argHandler_host, True],
    ["--listen", "-l", argHandler_listen, True],
    ["--port", "-p", argHandler_port, True],
    ["--readonly", "-r", argHandler_readonly, False],
    ["--workdir", "-w", argHandler_workdir, True],
    ["--plugins-dir", "-P", argHandler_pluginsDir, True],
    ["--help", "-h", argHandler_help, False],
    ["--dontopenuionstartup", "-D", argHandler_dontopenuionstartup, False],
    ["--url-base", "-u", argHandler_urlBase, True],
    ["--version", "-v", argHandler_version, False]
]

value_expected_arg = []

for _user_arg in sys.argv[1:]:
    is_exists = False

    if value_expected_arg:
        value_expected_arg[2](_user_arg)
        value_expected_arg = []

        continue

    for _arg in args:
        if len(_user_arg) > 2 and _user_arg[:2] == "--":
            arg = _user_arg.split("=")
            val = "=".join(arg[1:])
            arg = arg[0]

            if arg == _arg[0]:
                is_exists = True

                if _arg[3] and val == "":
                    print("Missing value for option:", _arg[0])
                    exit(0)

                if _arg[3]:
                    _arg[2](val)
                else:
                    _arg[2]()

                break
        elif _arg[1] and (_user_arg == _arg[1]):
            is_exists = True

            if _arg[3]:
                value_expected_arg = _arg
            else:
                _arg[2]()

            break

    if not is_exists:
        print("Invalid argument:", _user_arg)
        print("")
        argHandler_help()
        exit(0)

if value_expected_arg:
    print("Missing value for option:", value_expected_arg[0] + (", " + value_expected_arg[1]) if value_expected_arg[1] else "")
    exit(0)

if gdb_executable == "gdb" and not shutil.which("gdb"):
    print("\033[0;32;31m[Error] GDB is not installed. Please install GDB on your system and run GDBFrontend again.\033[0m")
    exit(1)

if tmux_executable == "tmux" and not shutil.which("tmux"):
    print("\033[0;32;31m[Error] Tmux is not installed. Please install Tmux on your system and run GDBFrontend again.\033[0m")
    exit(1)

print("GDBFrontend "+statics.VERSION_STRING)

if is_random_port:
    import mmap
    import ctypes
    
    mmap_path = '/tmp/gdbfrontend-mmap-'+terminal_id
    arg_config["MMAP_PATH"] = mmap_path
    
    if os.path.exists(mmap_path):
        fd = os.open(mmap_path, os.O_RDWR)
        os.write(fd, b"\0" * mmap.PAGESIZE)
    else:
        fd = os.open(mmap_path, os.O_CREAT | os.O_TRUNC | os.O_RDWR)
        os.write(fd, b"\0" * mmap.PAGESIZE)

    mmapBuff = mmap.mmap(fd, mmap.PAGESIZE, mmap.MAP_SHARED, mmap.PROT_WRITE)

@atexit.register
def exiting():
    global terminate_sub_procs

    if not terminate_sub_procs:
        return
    
    global is_random_port
    global mmap_path
    
    quit_tmux_gdb()
    subprocess.Popen([tmux_executable, "kill-session", "-t", terminal_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE).wait()

    if is_random_port:
        os.remove(mmap_path)

    print("Stopped GDBFrontend.")

try:
    proc = subprocess.run([gdb_executable, "--configuration"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    if "--with-python" not in repr(proc.stdout):
        print("[Error] Your GDB ("+gdb_executable+") doesn't have embedded Python. Please install a GDB version with embedded Python or you can build it yourself.")
        terminate_sub_procs = False
        exit(1)
    
    subprocess.Popen([tmux_executable, "kill-session", "-t", terminal_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE).wait()
    
    if not is_random_port:
        os.system(
            tmux_executable +
            " -f \"" + path + "/tmux.conf\" new-session -s " + terminal_id +
            " -d '" + gdb_executable +
            " -ex \"python import sys, os; sys.path.insert(0, \\\""+path+"\\\"); import config, json, base64; config.init(); " +
            "config.setJSON(base64.b64decode(\\\""+base64.b64encode(json.dumps(arg_config).encode()).decode()+"\\\").decode()); import gdbfrontend\"" +
            " " + gdb_args +
            "; read;'"
        )
    else:
        os.system(
            tmux_executable +
            " -f \"" + path + "/tmux.conf\" new-session -d -s " + terminal_id
        )

    if config.WORKDIR:
        os.system(
            tmux_executable +
            " -f \"" + path + "/tmux.conf\" send-keys -t " + terminal_id +
            " \"cd " + config.WORKDIR + "\"" +
            " ENTER"
        )

    if not is_random_port:
        print("Listening on %s: http://%s:%d/" % (config.BIND_ADDRESS, config.HOST_ADDRESS, config.HTTP_PORT))
        print(("Open this address in web browser: \033[0;32;40mhttp://%s:%d/\033[0m" % (config.HOST_ADDRESS, config.HTTP_PORT)))

        gf_url = "http://%s:%d/" % (config.HOST_ADDRESS, config.HTTP_PORT)

        if not dontopenuionstartup:
            if 'Microsoft' in platform.uname().release or 'microsoft' in platform.uname().release:
                os.system("/mnt/c/windows/system32/rundll32.exe url.dll,FileProtocolHandler %s" % gf_url)
            elif os.environ.get('DISPLAY'):
                if os.geteuid() != 0 and shutil.which("chrome"):
                    subprocess.Popen(
                        "chrome --app=" + gf_url,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        close_fds=True,
                        shell=True,
                        executable='/bin/bash'
                    )
                elif os.geteuid() != 0 and shutil.which("chromium"):
                    subprocess.Popen(
                        "chromium --app=" + gf_url,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        close_fds=True,
                        shell=True,
                        executable='/bin/bash'
                    )
                else:
                    webbrowser.open(gf_url)

        while True: time.sleep(0.1)
    else:
        os.system(
            tmux_executable +
            " -f \"" + path + "/tmux.conf\" send-keys -t " + terminal_id +
            " \"" +
            gdb_executable +
            " -ex \\\"python import sys, os; sys.path.insert(0, '"+path+"'); import config, json, base64; config.init(); " +
            "config.setJSON(base64.b64decode('"+base64.b64encode(json.dumps(arg_config).encode()).decode()+"').decode()); import gdbfrontend\\\"" +
            " " + gdb_args +
            "; read;" +
            "\" "
        )
        os.system(
            tmux_executable +
            " -f \"" + path + "/tmux.conf\" send-keys -t " + terminal_id +
            " ENTER"
        )

        http_port = ctypes.c_uint16.from_buffer(mmapBuff, 0)
        
        while not http_port.value: pass

        config.HTTP_PORT = http_port.value

        print("Listening on %s: http://%s:%d/" % (config.BIND_ADDRESS, config.HOST_ADDRESS, config.HTTP_PORT))
        print(("Open this address in web browser: \033[0;32;40mhttp://%s:%d/\033[0m" % (config.HOST_ADDRESS, config.HTTP_PORT)))

        gf_url = "http://%s:%d/" % (config.HOST_ADDRESS, config.HTTP_PORT)

        if not dontopenuionstartup:
            if 'Microsoft' in platform.uname().release or 'microsoft' in platform.uname().release:
                os.system("/mnt/c/windows/system32/rundll32.exe url.dll,FileProtocolHandler %s" % gf_url)
            elif os.environ.get('DISPLAY'):
                if os.geteuid() != 0 and shutil.which("chrome"):
                    subprocess.Popen(
                        "chrome --app=" + gf_url,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        close_fds=True,
                        shell=True,
                        executable='/bin/bash'
                    )
                elif os.geteuid() != 0 and shutil.which("chromium"):
                    subprocess.Popen(
                        "chromium --app=" + gf_url,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        close_fds=True,
                        shell=True,
                        executable='/bin/bash'
                    )
                else:
                    webbrowser.open(gf_url)

        while True: time.sleep(0.1)
except KeyboardInterrupt as e:
    print("Keyboard interrupt.")
    exit(0)
