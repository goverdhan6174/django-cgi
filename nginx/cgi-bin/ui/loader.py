import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import threading
import subprocess
import os

def browse_file():
    # Open a file dialog to select the Python script to run
    file_path = filedialog.askopenfilename(filetypes=[("Python files", "*.py")])
    if file_path:
        script_entry.delete(0, tk.END)
        script_entry.insert(0, file_path)

def run_script():
    script_path = script_entry.get()
    procid = procid_entry.get()
    pprocid = pprocid_entry.get()

    # Check if the script path is provided
    if not script_path or not os.path.isfile(script_path):
        result_label.config(text="Please select a valid script", fg="red")
        return
    
    # Check if procid is provided
    if not procid:
        result_label.config(text="Please enter procid", fg="red")
        return
    
    progress_bar.start()  # Start the loader
    run_button.config(state=tk.DISABLED)  # Disable button while running

    # Build the command with the arguments
    command = ['python', script_path, procid]
    if pprocid:
        command.append(pprocid)
    
    # Use subprocess to run the script in a separate process
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    progress_bar.stop()  # Stop the loader when the script finishes
    run_button.config(state=tk.NORMAL)  # Enable button again
    
    if process.returncode == 0:
        result_label.config(text="Success", fg="green")
    else:
        result_label.config(text="Failed", fg="red")
    
    print(f"Output: {stdout.decode()}")
    if stderr:
        print(f"Error: {stderr.decode()}")

# Initialize the main window
root = tk.Tk()
root.title("Script Loader")

# Set up the UI elements
ttk.Label(root, text="Select Script:").pack(pady=5)
script_entry = ttk.Entry(root, width=50)
script_entry.pack(pady=5, padx=10)
browse_button = tk.Button(root, text="Browse", command=browse_file)
browse_button.pack(pady=5)

ttk.Label(root, text="Enter procid:").pack(pady=5)
procid_entry = ttk.Entry(root)
procid_entry.pack(pady=5)

ttk.Label(root, text="Enter pprocid (optional):").pack(pady=5)
pprocid_entry = ttk.Entry(root)
pprocid_entry.pack(pady=5)

progress_bar = ttk.Progressbar(root, mode='indeterminate', length=300)
progress_bar.pack(pady=20)

run_button = tk.Button(root, text="Run Script", command=lambda: threading.Thread(target=run_script).start())
run_button.pack(pady=10)

result_label = tk.Label(root, text="")
result_label.pack(pady=10)

# Start the Tkinter event loop
root.mainloop()
