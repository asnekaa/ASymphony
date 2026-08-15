# Symphony Compiler for ASymphony

Symphony Compiler（`melc`）把 Melody 系统语言编译为 Symphony 文本汇编。

本目录中的版本基于 Symphony Compiler，并针对 ASymphony 架构进行了修改和扩展。

本编译器基于：
https://github.com/lovelyKoishi/Symphony-compiler

```text
.mel -> melc -> .txt
```

编译器只生成 `.txt` 汇编文件，不会自动运行汇编器或生成机器码。需要机器码时，可以再把 `.txt` 交给 ASymphony 汇编器。

## 快速开始

要求 Python 3.10 或更高版本。

直接从仓库运行：

```powershell
python -m melc examples\clock.mel -o examples\clock.txt
python -m melc examples\os.mel -o examples\os.txt
python -m melc examples\pixel_clock.mel -o examples\pixel_clock.txt
```

安装为命令行工具：

```powershell
pip install -e .
melc examples\pixel_clock.mel -o examples\pixel_clock.txt
```

省略 `-o` 时，编译器会把汇编输出到标准输出。

## Melody 示例

```melody
const SCREEN_WIDTH: u16 = 96;

static cursor: u16 = 0;
static message: [u8; _] = b"Hello\0";
static buffer: [u8; 80] = zeroed;
static points: [u8; 4] = [10, 20, 30, 40];

fn main() -> void {
    let count: u16 = 0;
    let imm limit: u16 = 10;

    while count < limit {
        count = count + 1;
    }

    loop {
    }
}
```

## 变量和静态数据

- `const`：编译期常量，不占运行时存储空间。
- `let`：默认可变的局部变量。
- `let imm`：初始化后不可重新赋值的局部变量。
- 标量 `static`：跨函数共享的可变全局存储，支持 `u8`、`u16`、`u32`。
- 字节字符串：`static text: [u8; _] = b"text\0";`。
- 清零数组：`static data: [u8; 64] = zeroed;`。
- 数值数组：`static data: [u8; 4] = [1, 2, 3, 4];`，也支持 `u16` 和 `u32`。

`[u8; _]` 表示数组长度由右侧字节字符串自动推断；`zeroed` 数组必须明确写出长度。

## 语句和表达式

当前支持：

- 函数定义和调用，最多 6 个参数。
- `return`、`if/else`、`while`、`loop`、`break`、`continue`。
- `+`、`-`、`*`、`/`、`%`、`&`、`|`、`^`、`~`、一元负号。
- `<<`、`>>`。
- `==`、`!=`、`<`、`<=`、`>`、`>=`。
- 十进制和十六进制整数。
- `true`、`false`。
- `//` 和 `#` 单行注释。
- 内联汇编块：`asm { "mov r1, 1" }`。

## 内置接口

内存：

```melody
let value: u8 = load8(address);
store8(address, value);
```

屏幕：

```melody
screen_mode(mode);
screen_buffer(address);
screen_foreground(color);
screen_background(color);
screen_font(font);
screen_resolution(setting);
screen_set(option, value);
```

时间：

```melody
let low: u32 = time_low();
let high: u32 = time_high();
let cached_high: u32 = time_cached_high();
time_snapshot(high_static, low_static);
```

其他：

```melody
keyboard_read();
counter();
out_write(value);
stack_set(value);
restart();
```

Symphony ISA 规格放在 [docs/isa.txt](docs/isa.txt)。

## 示例程序

### `examples/os.mel`

ASCII 32 字符模式的简单系统界面，包含键盘输入、退格、自动换行、输入缓冲区，以及 `echo`、`help`、`clear`、`time`、`reboot` 命令。

### `examples/clock.mel`

ASCII 32 数字时钟，显示 `HH:MM:SS`。启动时完成一次 Unix 纳秒时间戳换算，之后通过秒、分、时级联进位更新。

### `examples/pixel_clock.mel`

Pixel 32 圆形模拟时钟，分辨率为 `128x96`。示例使用中点圆算法绘制表盘、Bresenham 整数直线算法绘制刻度和指针。

## 测试

```powershell
pip install pytest
python -m pytest -q
```

测试覆盖词法和语法解析、变量、静态数据、数值数组、屏幕接口、32 位立即数构造，以及时间快照顺序。

## 当前限制

- 每个函数最多使用 `r7-r12` 六个局部寄存器，不支持自动栈溢出。
- 表达式使用 `r1-r6` 作为临时寄存器，极深表达式可能超过临时寄存器容量。
- 尚未实现完整静态类型检查。
- 尚未实现通用指针解引用、数组下标和指针类型推导。
- 当前通过 `load8`、`store8` 和地址算术访问字节内存。
- 没有优化器；性能敏感代码应避免在主循环中执行软件乘除法或整屏重绘。
