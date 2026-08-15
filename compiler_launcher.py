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
        result = subprocess.run(
            [PYTHON, "-m", "melc", file_path, "-o", output_path],
            cwd=COMPILER_DIR,
            capture_output=True,
            text=True
        )

        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print(result.stderr)

        if result.returncode == 0:
            messagebox.showinfo(
                "编译完成",
                f"已生成：\n{output_path}"
            )
        else:
            error = result.stderr.strip() or result.stdout.strip()

            messagebox.showerror(
                "编译失败",
                f"编译器错误：\n\n{error}"
            )

    except Exception as e:
        messagebox.showerror(
            "运行错误",
            str(e)
        )

root.destroy()
