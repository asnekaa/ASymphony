import os
import shutil
import filecmp

SRC = r"C:\Users\pc\AppData\Roaming\Turing Complete\schematics\architecture\ASymphony"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DST = os.path.join(BASE_DIR, "architecture")


def rel(path):
    return os.path.relpath(path, BASE_DIR)


def sync(src, dst):
    if not os.path.exists(dst):
        os.makedirs(dst)
        print(f"[创建目录] {rel(dst)}")

    src_items = set(os.listdir(src))
    dst_items = set(os.listdir(dst))

    for name in dst_items - src_items:
        path = os.path.join(dst, name)

        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

        print(f"[删除] {rel(path)}")

    for name in src_items:
        src_path = os.path.join(src, name)
        dst_path = os.path.join(dst, name)

        if os.path.isdir(src_path):
            if os.path.exists(dst_path) and not os.path.isdir(dst_path):
                os.remove(dst_path)
                print(f"[删除] {rel(dst_path)}")

            if not os.path.exists(dst_path):
                os.makedirs(dst_path)
                print(f"[创建目录] {rel(dst_path)}")

            sync(src_path, dst_path)

        else:
            if os.path.exists(dst_path):
                if os.path.isdir(dst_path):
                    shutil.rmtree(dst_path)
                    shutil.copy2(src_path, dst_path)
                    print(f"[覆盖] {rel(dst_path)}")

                elif filecmp.cmp(src_path, dst_path, shallow=False):
                    print(f"[不变] {rel(dst_path)}")

                else:
                    shutil.copy2(src_path, dst_path)
                    print(f"[覆盖] {rel(dst_path)}")

            else:
                shutil.copy2(src_path, dst_path)
                print(f"[复制] {rel(dst_path)}")


if not os.path.isdir(SRC):
    print(f"[错误] 源目录不存在: {SRC}")
    raise SystemExit(1)

print("=========================================================================================")
print(f"源文件夹:   {SRC}")
print(f"目标文件夹: {DST}")
print("=========================================================================================\n")

sync(SRC, DST)
print("\n同步完成。")