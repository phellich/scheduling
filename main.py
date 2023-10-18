from tqdm import tqdm
import subprocess
import ctypes

SCHEDULING_VERSION = 1

def compile_code():
    compile_command = ["gcc", "-O3", "-o", f"scheduling/scheduling_v{SCHEDULING_VERSION}", f"scheduling/scheduling_v{SCHEDULING_VERSION}.c", "-lm"]
    # compile_command = ["gcc", "-m64", "-O3", "-shared", "-o", 
    #                f"scheduling/scheduling_v{SCHEDULING_VERSION}.dll", 
    #                f"scheduling/scheduling_v{SCHEDULING_VERSION}.c", "-lm"]
    subprocess.run(compile_command)

def run_code():
    run_command = [f"./scheduling/scheduling_v{SCHEDULING_VERSION}"]
    subprocess.run(run_command)

def main():
    compile_code()
    # lib = ctypes.CDLL(f"./scheduling/scheduling_v{SCHEDULING_VERSION}.dll") # python is 64 bits and compiler too (check with gcc --version)
    print("Hello")
    for _ in tqdm(range(1)):
        run_code()

if __name__ == "__main__":
    main()
