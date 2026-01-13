#!/usr/bin/env python3
"""
WeOrder Development Manager (Roburst Start/Stop/Restart)
Usage: python scripts/dev_manager.py [start|stop|restart|clean]
"""
import sys
import os
import subprocess
import time
import signal

# Configuration
BACKEND_PORT = 9202
FRONTEND_PORT = 5173
BACKEND_CMD = ["venv/bin/uvicorn", "main:app", "--reload", "--port", str(BACKEND_PORT)]
FRONTEND_DIR = "frontend"
FRONTEND_CMD = ["npm", "run", "dev"]

def get_pid_by_port(port):
    """Finds PID using a specific port."""
    try:
        result = subprocess.check_output(f"lsof -t -i :{port}", shell=True)
        return int(result.strip())
    except subprocess.CalledProcessError:
        return None

def kill_process_on_port(port, name):
    """Kills process on a port safely."""
    pid = get_pid_by_port(port)
    if pid:
        print(f"⚠️  Found existing {name} on port {port} (PID: {pid}). Killing...")
        try:
            os.kill(pid, signal.SIGKILL)
            time.sleep(1) # Give it a moment to die
            print(f"✅ Killed {name}.")
        except ProcessLookupError:
            print(f"   Process {pid} already gone.")
    else:
        print(f"✅ Port {port} ({name}) is clear.")

def start_backend():
    print(f"🚀 Starting Backend on port {BACKEND_PORT}...")
    # Run in background, detached purely for this script's purpose? 
    # Or creating a new terminal tab is better for dev?
    # For now, let's suggest the user runs this in a main session or use Popen
    return subprocess.Popen(BACKEND_CMD, cwd=os.getcwd())

def start_frontend():
    print(f"🚀 Starting Frontend on port {FRONTEND_PORT}...")
    return subprocess.Popen(FRONTEND_CMD, cwd=os.path.join(os.getcwd(), FRONTEND_DIR))

def action_stop():
    print("🛑 Stopping services...")
    kill_process_on_port(BACKEND_PORT, "Backend")
    kill_process_on_port(FRONTEND_PORT, "Frontend")
    print("✅ All services stopped.")

def action_start():
    action_stop() # Always clean first
    print("🟢 Starting services...")
    
    # We will start them as subprocesses
    try:
        be_proc = start_backend()
        fe_proc = start_frontend()
        
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
