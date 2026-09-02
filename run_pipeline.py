import subprocess
import sys

def run_script(script_name):
    try:
        subprocess.run([sys.executable, script_name], check=True)
    except subprocess.CalledProcessError:
        print(f"\n❌ ERROR: {script_name} failed to run. Stopping pipeline.")
        sys.exit(1)

if __name__ == "__main__":
    print("🚦 STARTING FULL ANPR PIPELINE 🚦")
    
    run_script("main.py")
    run_script("add_missing_data.py")
    run_script("visualize.py")
    
    print("\n✅ PIPELINE COMPLETE! Check data/output/out.mp4")