import os
import shutil

SRC = r"C:\Users\pc\AppData\Roaming\Turing Complete\schematics\architecture\ASymphony\circuit.data"
DST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "circuit.data")

if not os.path.isfile(SRC):
    print(f"[错误] 文件不存在: {SRC}")
    raise SystemExit(1)

shutil.copy2(SRC, DST)

print(f"[复制完成] {DST}")