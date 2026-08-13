from melc.compiler import compile_source


def test_const_and_return():
    asm = compile_source(
        """
const ONE: u16 = 1;
fn main() -> u16 {
    return ONE;
}
"""
    )
    assert "const ONE = 1" in asm
    assert "mov r1, 1" in asm
    assert "ret" in asm


def test_let_assignment_and_if():
    asm = compile_source(
        """
fn main() -> void {
    let x: u16 = 1;
    x = x + 1;
    if x == 2 {
        out_write(x);
    }
}
"""
    )
    assert "add r1, r1, r2" in asm
    assert "cmp r1, r2" in asm
    assert "out r1" in asm


def test_static_bytes():
    asm = compile_source(
        """
static msg: [u8; _] = b"hi\\n\\0";
fn main() -> void {}
"""
    )
    assert "msg:" in asm
    assert '"hi\\n\\0"' in asm


def test_static_numeric_array():
    asm = compile_source(
        """
static points: [u8; 4] = [1, 2, 3, 255];
fn main() -> void {}
"""
    )
    assert "points:\nU8 1\nU8 2\nU8 3\nU8 255" in asm


def test_scalar_static_and_memory_intrinsics():
    asm = compile_source(
        """
static cursor: u16 = 0;
static framebuffer: [u8; 4] = zeroed;
fn main() -> void {
    cursor = framebuffer;
    store8(cursor, 65);
    let value: u8 = load8(cursor);
}
"""
    )
    assert "add r2, zr, cursor\nstore_16 [r2], r1" in asm
    assert "add r2, zr, cursor\nload_16 r1, [r2]" in asm
    assert "store_8 [r1], r2" in asm
    assert "load_8 r1, [r1]" in asm
    assert "cursor:\nU16 0" in asm


def test_screen_interfaces():
    asm = compile_source(
        """
fn main() -> void {
    screen_mode(0);
    screen_buffer(0x2000);
    screen_foreground(0xFC);
    screen_background(0);
    screen_font(1);
    screen_resolution(255);
}
"""
    )
    assert asm.count("screen r1, r2") == 6
    assert "mov r1, 0\nscreen r1, r2" in asm
    assert "mov r1, 1\nscreen r1, r2" in asm
    assert "mov r1, 4\nscreen r1, r2" in asm


def test_rgb888_immediate():
    asm = compile_source(
        """
fn main() -> void {
    screen_foreground(0xFFFF00);
}
"""
    )
    assert "mov r2, 255\nlsl r2, r2, 16\nor r2, r2, 65280" in asm
    assert "mov r1, 2\nscreen r1, r2" in asm


def test_time_snapshot_order():
    asm = compile_source(
        """
fn main() -> void {
    let low: u32 = time_low();
    let high: u32 = time_high();
}
"""
    )
    assert "time_0 r1" in asm
    assert "time_0 r2\ntime_1 r1" in asm


def test_explicit_time_snapshot():
    asm = compile_source(
        """
fn main() -> void {
    let low: u32 = time_low();
    let high: u32 = time_cached_high();
}
"""
    )
    assert "time_0 r1" in asm
    assert "time_1 r1" in asm


def test_atomic_time_snapshot():
    asm = compile_source(
        """
static high: u32 = 0;
static low: u32 = 0;
fn main() -> void {
    time_snapshot(high, low);
}
"""
    )
    assert "time_0 r1\ntime_1 r2" in asm
    assert "add r3, zr, high\nstore_32 [r3], r2" in asm
    assert "add r3, zr, low\nstore_32 [r3], r1" in asm
