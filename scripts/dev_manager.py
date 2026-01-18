#!/usr/bin/env python3
"""
WeOrder Development Manager (Robust Start/Stop/Restart)
Usage: python scripts/dev_manager.py [start|stop|restart|clean]
"""
import sys
import os
import subprocess
import time
import signal
import psutil

# Configuration
BACKEND_PORT = 9202
FRONTEND_PORT = 5173
# Use the standard .venv
BACKEND_CMD = [".venv/bin/uvicorn", "main:app", "--reload", "--port", str(BACKEND_PORT)] 
FRONTEND_DIR = "frontend"
FRONTEND_CMD = ["npm", "run", "dev"]

PID_FILE = ".dev_manager.pids"

def save_pids(backend_pid, frontend_pid):
    with open(PID_FILE, "w") as f:
        f.write(f"{backend_pid},{frontend_pid}")

def load_pids():
    if not os.path.exists(PID_FILE):
        return None, None
    try:
        with open(PID_FILE, "r") as f:
            content = f.read().strip()
            parts = content.split(",")
            return int(parts[0]), int(parts[1])
    except:
        return None, None

def clear_pids():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

def kill_process_tree(pid):
    """Kills a process and all its children (cleanly)."""
    if not pid: 
        return
        
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        # Kill children first
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass
        
        # Kill parent
        parent.terminate()
        
        # Wait for death
        gone, alive = psutil.wait_procs(children + [parent], timeout=3)
        
        # Force kill if still alive
        for p in alive:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass
                
        print(f"✅ Killed PID {pid} and children.")
        
    except psutil.NoSuchProcess:
        print(f"   PID {pid} already gone.")
    except Exception as e:
        print(f"   Error killing {pid}: {e}")

def get_pid_by_port(port):
    """Finds PID using a specific port (Fallback)."""
    try:
        # lsof might return multiple lines if workers logic is complex
        result = subprocess.check_output(f"lsof -t -i :{port}", shell=True)
        pids = result.strip().split()
        return int(pids[0]) if pids else None # Return first one (likely parent or main worker)
    except subprocess.CalledProcessError:
        return None

def kill_process_on_port(port, name):
    """Kills process on a port safely (Fallback)."""
    pid = get_pid_by_port(port)
    if pid:
        print(f"⚠️  Found existing {name} on port {port} (PID: {pid}). Killing...")
        kill_process_tree(pid)
    else:
        print(f"✅ Port {port} ({name}) is clear.")

def start_backend():
    print(f"🚀 Starting Backend on port {BACKEND_PORT}...")
    # start_new_session=True creates a new process group, enabling killpg if needed
    # But psutil logic above handles tree nicely too.
    return subprocess.Popen(BACKEND_CMD, cwd=os.getcwd())

def start_frontend():
    print(f"🚀 Starting Frontend on port {FRONTEND_PORT}...")
    return subprocess.Popen(FRONTEND_CMD, cwd=os.path.join(os.getcwd(), FRONTEND_DIR))

def action_stop():
    print("🛑 Stopping services...")
    
    # 1. Try known PIDs first
    be_pid, fe_pid = load_pids()
    if be_pid:
        print(f"   Stopping recorded Backend (PID: {be_pid})...")
        kill_process_tree(be_pid)
    if fe_pid:
        print(f"   Stopping recorded Frontend (PID: {fe_pid})...")
        kill_process_tree(fe_pid)
        
    # 2. Fallback to ports (Double tap)
    kill_process_on_port(BACKEND_PORT, "Backend")
    kill_process_on_port(FRONTEND_PORT, "Frontend")
    
    clear_pids()
    print("✅ All services stopped.")

def action_start():
    action_stop() # Always clean first
    print("🟢 Starting services...")
    
    try:
        be_proc = start_backend()
        fe_proc = start_frontend()
        
        save_pids(be_proc.pid, fe_proc.pid)
        
        print("\n✨ System is running! Press Ctrl+C to stop both.")
        be_proc.wait()
        fe_proc.wait()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        action_stop()

def action_clean():
    """Nuclear option: Cleans node_modules and venv (optional)"""
    print("☢️  Cleaning Frontend Dependencies...")
    frontend_nm = os.path.join(os.getcwd(), FRONTEND_DIR, "node_modules")
    if os.path.exists(frontend_nm):
        subprocess.run(f"rm -rf {frontend_nm}", shell=True)
        print("   Deleted node_modules.")
    print("   Please run 'npm install' manually or add install logic here.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/dev_manager.py [start|stop|restart|clean]")
        sys.exit(1)
        
    cmd = sys.argv[1]
    if cmd == "start":
        action_start()
    elif cmd == "stop":
        action_stop()
    elif cmd == "restart":
        action_start()
    elif cmd == "clean":
        action_clean()
    else:
        print(f"Unknown command: {cmd}")
