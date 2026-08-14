import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox

ROOT = os.path.dirname(os.path.abspath(__file__))
COMPILER_DIR = os.path.join(ROOT, "Symphony-compiler")
VENV_PYTHON = os.path.join(COMPILER_DIR, ".venv", "Scripts", "python.exe")
PYTHON = VENV_PYTHON if os.path.isfile(VENV_PYTHON) else "python"

root = tk.Tk()
root.withdraw()

file_path = filedialog.askopenfilename(
    title="选择 Mel 文件",
    initialdir=ROOT,
    filetypes=[("Mel files", "*.mel"), ("All files", "*.*")]
)

if file_path:
    output_path = os.path.splitext(file_path)[0] + ".txt"
    try:
        subprocess.run(
            [PYTHON, "-m", "melc", file_path, "-o", output_path],
            cwd=COMPILER_DIR,
            check=True
        )
        messagebox.showinfo("编译完成", f"已生成：\n{output_path}")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("编译失败", f"编译器返回错误代码：{e.returncode}")
    except Exception as e:
        messagebox.showerror("错误", str(e))

root.destroy()
