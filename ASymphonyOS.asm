jmp main

msg_welcome:
"ASymphonyOS v0.1\n"
"Screen: ASCII 8 (96*40)\n"
"Type 'help' for commands.\n\n"
U8 0

msg_prompt:
"> "
U8 0

msg_newline:
"\n"
U8 0

msg_error:
"Unknown command. Type 'help'.\n"
U8 0

msg_help:
"Available commands:\n"
"  help        - Show this message\n"
"  clear       - Clear the screen\n"
"  echo <text> - Display text\n"
"  reboot      - Restart system\n"
U8 0

cmd_str_help:
"help"
U8 0

cmd_str_clear:
"clear"
U8 0

cmd_str_echo_space:
"echo "
U8 0

cmd_str_reboot:
"reboot"
U8 0

const arg_1 = r1
const res_1 = r1
const arg_2 = r2
const res_2 = r2

const cursor = r3
const vram_ptr = r4
const buf_ptr = r5

const VAR_CURSOR_POS = 10000    ; Cursor position
const VAR_INPUT_BUFFER = 20000  ; Command input buffer (32 bytes)
const VRAM_BASE = 30000         ; Video RAM base address
const SCREEN_SIZE = 3840        ; Screen size: 96 * 40 = 3840
const ENTER = 10                ; Enter key ASCII
const BACKSPACE = 13            ; Backspace key ASCII
const SPACE = 32                ; Space character ASCII



boot:
    push r3
    const screen_opt = r3
    
    screen screen_opt, 0
    inc screen_opt
    screen screen_opt, VRAM_BASE

    ; 清屏并重置光标
    call sys_clear_screen
	
    ; 打印欢迎信息
    mov arg_1, msg_welcome
    call sys_print_string
    
    pop r3
    ret



os_shell:
    ; 打印提示符 "> "
    mov arg_1, msg_prompt
    call sys_print_string
    
    call wait_input
    
    ret



sys_clear_screen:
    push r4
    push r5
    
    const loop_cnt = r5

    clr loop_cnt
    mov vram_ptr, VRAM_BASE

	clear_loop:
    store_8 [vram_ptr], zr
    inc vram_ptr
    inc loop_cnt
    jle clear_loop, loop_cnt, SCREEN_SIZE 

    ; 光标归零
    store_32 [VAR_CURSOR_POS], zr
    
    pop r5
    pop r4
    ret



sys_print_string:
    push r3
    push r4

    const str_ptr = r3
    const char_val = r4
    
    mov str_ptr, arg_1

	print_str_loop:
    load_8 char_val, [str_ptr]
    je print_str_end, char_val, 0

    mov arg_1, char_val
    call sys_print_char
    
    add str_ptr, str_ptr, 1
    jmp print_str_loop

	print_str_end:
    pop r4
    pop r3
    ret



sys_print_char:
    push r3
    push r4
    push r5

    const temp_val = r5
    
    load_32 cursor, [VAR_CURSOR_POS]

    ; 处理换行符 '\n'
    je char_newline, arg_1, ENTER

    ; 处理退格符 '\b'
    je char_backspace, arg_1, BACKSPACE

    ; 正常字符写入显存
    mov vram_ptr, VRAM_BASE
    add vram_ptr, cursor
    store_8 [vram_ptr], arg_1
    inc cursor
    jmp char_check_scroll

	char_backspace:
    je char_update_cursor, cursor, 0 ; 如果已经在行首，不退格
    dec cursor
    mov vram_ptr, VRAM_BASE
    add vram_ptr, cursor
    mov temp_val, SPACE
    store_8 [vram_ptr], temp_val
    jmp char_update_cursor

	char_newline:
    ; cursor = (cursor / 96 + 1) * 96
    div vram_ptr, cursor, 96
    inc vram_ptr
    mul cursor, vram_ptr, 96

	char_check_scroll:
    jl char_update_cursor, cursor, SCREEN_SIZE
    call sys_clear_screen
    clr cursor

	char_update_cursor:
    store_32 [VAR_CURSOR_POS], cursor
    
    pop r5
    pop r4
    pop r3
    ret



wait_input:
    push r3
    push r4
    push r5
    
    const key_char = r3
    const check_empty = r4
	
    ; 初始化输入缓冲区指针
    mov buf_ptr, VAR_INPUT_BUFFER
	
	wait_input_loop:
    ; 读取键盘输入
    call sys_read_key
    mov key_char, res_1

    ; 处理回车键 (Enter, ASCII 10)
    je handle_enter, key_char, ENTER

    ; 处理退格键 (Backspace, ASCII 8)
    je handle_backspace, key_char, BACKSPACE

    ; 处理普通字符输入 (存入缓冲区并回显)
    store_8 [buf_ptr], key_char
    inc buf_ptr
    
    mov arg_1, key_char
    call sys_print_char
    jmp wait_input_loop

	handle_backspace:
    ; 如果缓冲区为空，则忽略退格
    je wait_input_loop, buf_ptr, VAR_INPUT_BUFFER
    
    ; 缓冲区指针回退
    dec buf_ptr
    
    ; 屏幕执行退格动作
    mov arg_1, BACKSPACE
    call sys_print_char
    jmp wait_input_loop

	handle_enter:
    ; 打印换行
    mov arg_1, ENTER
    call sys_print_char

    ; 缓冲区末尾写入 0 (字符串结束符)
    store_8 [buf_ptr], zr

    ; --- 解析命令 ---
    
    ; 检查是否为空命令 (直接按回车)
    load_8 check_empty, [VAR_INPUT_BUFFER]
    je wait_input_end, check_empty, 0

    ; 比较 "help"
    mov arg_1, VAR_INPUT_BUFFER
    mov arg_2, cmd_str_help
    call sys_strcmp
    eq res_1, 1
    mov.c arg_1, msg_help
    call.c sys_print_string
    jmp.c wait_input_end

    ; 比较 "clear"
    mov arg_1, VAR_INPUT_BUFFER
    mov arg_2, cmd_str_clear
    call sys_strcmp
    eq res_1, 1
    call.c sys_clear_screen
    je wait_input_end, res_1, 1

    ; 检查 "echo " 前缀
    mov arg_1, VAR_INPUT_BUFFER
    mov arg_2, cmd_str_echo_space
    call sys_check_prefix
    jne not_echo_cmd, res_1, 1
    ; 打印 echo 后面的文本
    mov arg_1, VAR_INPUT_BUFFER
    add arg_1, 5
    call sys_print_string    
    mov arg_1, msg_newline
    call sys_print_string
    jmp wait_input_end
    not_echo_cmd:

    ; 比较 "reboot"
    mov arg_1, VAR_INPUT_BUFFER
    mov arg_2, cmd_str_reboot
    call sys_strcmp
    je main, res_1, 1
    
    ; 未知命令
    mov arg_1, msg_error
    call sys_print_string
    
    wait_input_end:
    pop r5
    pop r4
    pop r3
    ret



sys_read_key:
    push r3
    const key_val = r3
    

	wait_press:
    keyboard key_val
    jle wait_press, key_val, 255
    and res_1, key_val, 0b11111111

    pop r3
    ret



; ------------------------------------------
; sys_strcmp: 比较两个字符串是否相等
; 参数: arg_1 (字符串1指针), arg_2 (字符串2指针)
; 返回值: res_1 (1 表示相等, 0 表示不相等)
; ------------------------------------------
sys_strcmp:
    push r3
    push r4
    push r5
    push r6

    const ptr1 = r3
    const ptr2 = r4
    const c1 = r5
    const c2 = r6

    mov ptr1, arg_1
    mov ptr2, arg_2

	strcmp_loop:
    load_8 c1, [ptr1]
    load_8 c2, [ptr2]
    
    ; 如果字符相等且为 0 (到达末尾)，返回 1
    je strcmp_same, c1, 0
    
    ; 如果字符不相等，返回 0
    jne strcmp_diff, c1, c2
    
    ; 继续比较下一个字符
    inc ptr1
    inc ptr2
    jmp strcmp_loop

	strcmp_same:
    mov res_1, 1
    jmp strcmp_end

	strcmp_diff:
    clr res_1

	strcmp_end:
    pop r6
    pop r5
    pop r4
    pop r3
    ret



; ------------------------------------------
; sys_check_prefix: 检查字符串是否以特定前缀开头
; 参数: arg_1 (字符串指针), arg_2 (前缀指针)
; 返回值: res_1 (1 表示是前缀, 0 表示不是)
; ------------------------------------------
sys_check_prefix:
    push r3
    push r4
    push r5
    push r6

    const check_prefix_str_ptr = r3
    const prefix_ptr = r4
    const str_ch = r5
    const prefix_ch = r6
    
    mov check_prefix_str_ptr, arg_1
    mov prefix_ptr, arg_2

check_prefix_loop:
    load_8 prefix_ch, [prefix_ptr]
    load_8 str_ch, [check_prefix_str_ptr]
    
    je check_prefix_match, prefix_ch, 0
    jne check_prefix_nomatch, str_ch, prefix_ch
    
    inc check_prefix_str_ptr
    inc prefix_ptr
    jmp check_prefix_loop

check_prefix_match:
    mov res_1, 1
    jmp check_prefix_end

check_prefix_nomatch:
    clr res_1

check_prefix_end:
    pop r6
    pop r5
    pop r4
    pop r3
    ret



main:
    call boot
main_loop:
    call os_shell
    jmp main_loop
