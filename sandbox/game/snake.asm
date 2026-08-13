; ==========================================
; 贪吃蛇游戏模块 (/game/snake.asm)
; ==========================================

msg_game_over:
"Game Over! Press any key to exit."
U8 0

const DIR_UP = 0
const DIR_RIGHT = 1
const DIR_DOWN = 2
const DIR_LEFT = 3

const CHAR_WALL = 35        ; '#'
const CHAR_SNAKE_HEAD = 79  ; 'O'
const CHAR_SNAKE_BODY = 111 ; 'o'
const CHAR_FOOD = 42        ; '*'
const CHAR_SPACE = 32       ; ' '

const SNAKE_VRAM_BASE = 30000
const SNAKE_BODY_BASE = 40000
const SNAKE_HEAD_IDX = 44000
const SNAKE_TAIL_IDX = 44004
const SNAKE_DIR = 44008
const FOOD_POS = 44012
const LAST_TIME = 44016
const RAND_SEED = 44020
const MAX_LEN = 1000

; 暴露给外部调用的入口标签
pub start:
    ; 遵守 ABI，保存所有被调用者保存的寄存器
    push r3
    push r4
    push r5
    push r6
    push r7
    push r8
    push r9
    push r10
    push r11
    push r12
    push r13
    
    call snake_clear_screen
    call snake_draw_board
    call snake_init
    
    ; 初始化随机数种子和时间
    time_0 r1
    store_32 [RAND_SEED], r1
    store_32 [LAST_TIME], r1
    
    call snake_spawn_food
    
snake_loop:
    ; 非阻塞读取键盘
    keyboard r1
    jle snake_no_key, r1, 255
    and r1, r1, 255
    
    ; 处理按键 (WASD / Q)
    je snake_quit, r1, 113 ; 'q'
    je snake_quit, r1, 81  ; 'Q'
    
    je snake_set_up, r1, 119 ; 'w'
    je snake_set_up, r1, 87  ; 'W'
    je snake_set_left, r1, 97 ; 'a'
    je snake_set_left, r1, 65 ; 'A'
    je snake_set_down, r1, 115 ; 's'
    je snake_set_down, r1, 83 ; 'S'
    je snake_set_right, r1, 100 ; 'd'
    je snake_set_right, r1, 68 ; 'D'
    jmp snake_no_key
    
snake_set_up:
    load_32 r2, [SNAKE_DIR]
    je snake_no_key, r2, DIR_DOWN
    mov r2, DIR_UP
    store_32 [SNAKE_DIR], r2
    jmp snake_no_key
    
snake_set_down:
    load_32 r2, [SNAKE_DIR]
    je snake_no_key, r2, DIR_UP
    mov r2, DIR_DOWN
    store_32 [SNAKE_DIR], r2
    jmp snake_no_key
    
snake_set_left:
    load_32 r2, [SNAKE_DIR]
    je snake_no_key, r2, DIR_RIGHT
    mov r2, DIR_LEFT
    store_32 [SNAKE_DIR], r2
    jmp snake_no_key
    
snake_set_right:
    load_32 r2, [SNAKE_DIR]
    je snake_no_key, r2, DIR_LEFT
    mov r2, DIR_RIGHT
    store_32 [SNAKE_DIR], r2
    jmp snake_no_key
    
snake_no_key:
    ; 帧率控制 (100ms 一帧)
    time_0 r1
    load_32 r2, [LAST_TIME]
    sub r3, r1, r2
    jl snake_loop, r3, 100
    
    store_32 [LAST_TIME], r1
    
    ; 移动蛇
    call snake_move
    je snake_game_over, r1, 0
    jmp snake_loop
    
snake_game_over:
    ; 在屏幕中央打印 Game Over (Offset: 20 * 96 + 32 = 1952)
    mov r1, msg_game_over
    mov r2, 1952
    add r2, r2, SNAKE_VRAM_BASE
game_over_loop:
    load_8 r3, [r1]
    je game_over_wait, r3, 0
    store_8 [r2], r3
    inc r1
    inc r2
    jmp game_over_loop
    
game_over_wait:
    keyboard r1
    jle game_over_wait, r1, 255
    
snake_quit:
    ; 恢复寄存器并返回 OS
    pop r13
    pop r12
    pop r11
    pop r10
    pop r9
    pop r8
    pop r7
    pop r6
    pop r5
    pop r4
    pop r3
    ret


snake_clear_screen:
    mov r4, SNAKE_VRAM_BASE
    mov r5, 0
snake_clear_loop:
    store_8 [r4], zr
    inc r4
    inc r5
    jle snake_clear_loop, r5, 3840
    ret


snake_draw_board:
    mov r3, 0
draw_top_bottom:
    add r4, r3, SNAKE_VRAM_BASE
    mov r5, CHAR_WALL
    store_8 [r4], r5
    
    add r4, r3, 3744 ; 39 * 96
    add r4, r4, SNAKE_VRAM_BASE
    store_8 [r4], r5
    
    inc r3
    jl draw_top_bottom, r3, 96
    
    mov r3, 0
draw_left_right:
    mul r4, r3, 96
    add r4, r4, SNAKE_VRAM_BASE
    mov r5, CHAR_WALL
    store_8 [r4], r5
    
    mul r4, r3, 96
    add r4, r4, 95
    add r4, r4, SNAKE_VRAM_BASE
    store_8 [r4], r5
    
    inc r3
    jl draw_left_right, r3, 40
    ret


snake_init:
    mov r3, 2
    store_32 [SNAKE_HEAD_IDX], r3
    mov r3, 0
    store_32 [SNAKE_TAIL_IDX], r3
    
    mov r3, DIR_RIGHT
    store_32 [SNAKE_DIR], r3
    
    ; 初始化身体 (Offset: 20 * 96 + 40 = 1960)
    mov r3, 1960
    store_32 [SNAKE_BODY_BASE], r3
    add r4, r3, SNAKE_VRAM_BASE
    mov r5, CHAR_SNAKE_BODY
    store_8 [r4], r5
    
    mov r3, 1961
    mov r4, SNAKE_BODY_BASE
    add r4, r4, 4
    store_32 [r4], r3
    add r4, r3, SNAKE_VRAM_BASE
    store_8 [r4], r5
    
    mov r3, 1962
    mov r4, SNAKE_BODY_BASE
    add r4, r4, 8
    store_32 [r4], r3
    add r4, r3, SNAKE_VRAM_BASE
    mov r5, CHAR_SNAKE_HEAD
    store_8 [r4], r5
    ret


snake_spawn_food:
spawn_loop:
    ; 线性同余生成器 (LCG)
    ; 使用适合 16 位立即数的参数: multiplier=25173, increment=13849
    load_32 r3, [RAND_SEED]
    mul r3, r3, 25173
    add r3, r3, 13849
    store_32 [RAND_SEED], r3
    
    mod r4, r3, 3840
    
    ; 检查是否生成在墙壁上
    mod r5, r4, 96
    je spawn_loop, r5, 0
    je spawn_loop, r5, 95
    div r5, r4, 96
    je spawn_loop, r5, 0
    je spawn_loop, r5, 39
    
    ; 检查是否生成在蛇身上 (必须是空格)
    add r6, r4, SNAKE_VRAM_BASE
    load_8 r5, [r6]
    jne spawn_loop, r5, CHAR_SPACE
    
    ; 放置食物
    store_32 [FOOD_POS], r4
    mov r5, CHAR_FOOD
    store_8 [r6], r5
    ret


snake_move:
    load_32 r3, [SNAKE_HEAD_IDX]
    mul r4, r3, 4
    add r4, r4, SNAKE_BODY_BASE
    load_32 r5, [r4] ; r5 = 当前头部的显存偏移量
    
    load_32 r6, [SNAKE_DIR]
    
    je move_up, r6, DIR_UP
    je move_right, r6, DIR_RIGHT
    je move_down, r6, DIR_DOWN
    je move_left, r6, DIR_LEFT
    
move_up:
    sub r7, r5, 96
    jmp move_check
move_down:
    add r7, r5, 96
    jmp move_check
move_left:
    sub r7, r5, 1
    jmp move_check
move_right:
    add r7, r5, 1
    jmp move_check
    
move_check:
    ; r7 = 新头部的显存偏移量
    ; 1. 检查是否撞墙
    mod r8, r7, 96
    je move_end_collision, r8, 0
    je move_end_collision, r8, 95
    div r8, r7, 96
    je move_end_collision, r8, 0
    je move_end_collision, r8, 39
    
    ; 2. 检查是否撞到自己
    add r8, r7, SNAKE_VRAM_BASE
    load_8 r9, [r8]
    je move_end_collision, r9, CHAR_SNAKE_BODY
    je move_end_collision, r9, CHAR_SNAKE_HEAD
    
    ; 3. 检查是否吃到食物
    load_32 r10, [FOOD_POS]
    je eat_food, r7, r10
    
    ; 没吃到食物，移动尾巴 (擦除屏幕上的尾巴并更新指针)
    load_32 r11, [SNAKE_TAIL_IDX]
    mul r12, r11, 4
    add r12, r12, SNAKE_BODY_BASE
    load_32 r13, [r12]
    
    add r12, r13, SNAKE_VRAM_BASE
    mov r8, CHAR_SPACE
    store_8 [r12], r8
    
    add r11, r11, 1
    mod r11, r11, MAX_LEN
    store_32 [SNAKE_TAIL_IDX], r11
    jmp update_head
    
eat_food:
    call snake_spawn_food
    
update_head:
    ; 将旧头部字符改为身体字符
    add r8, r5, SNAKE_VRAM_BASE
    mov r9, CHAR_SNAKE_BODY
    store_8 [r8], r9
    
    ; 更新头部指针和坐标
    load_32 r3, [SNAKE_HEAD_IDX]
    add r3, r3, 1
    mod r3, r3, MAX_LEN
    store_32 [SNAKE_HEAD_IDX], r3
    
    mul r4, r3, 4
    add r4, r4, SNAKE_BODY_BASE
    store_32 [r4], r7
    
    ; 绘制新头部
    add r8, r7, SNAKE_VRAM_BASE
    mov r9, CHAR_SNAKE_HEAD
    store_8 [r8], r9
    
    mov r1, 1
    ret
    
move_end_collision:
    mov r1, 0
    ret