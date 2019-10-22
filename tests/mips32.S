.org 0x80010000
.log

.macro loadi register value
lui register, value
ori register, register, <<value
.endmacro

.macro store dst src
sw src, 0(dst)
.endmacro

.macro load dst src
lw dst, 0(src)
.endmacro

.macro write address value
loadi $t0, address
loadi $t1, value
store $t0, $t1
.endmacro

.macro gpu_ctrl command param
write 0x1f801814
.endmacro

main:

;load $t0, 0x1f801814
;load $t1, 0x03000000

;store $t0, $t1

; reset gpu
;gpu_ctrl 0, 0
;gpu_ctrl 4, 0 ; disable dma
;gpu_ctrl 3, 1

write 0x1f801814 0x08000036
write 0x1f801814 0x03000000

write 0x1f801810 0x2000ffff
write 0x1f801810 0x00640064
write 0x1f801810 0x00c800c8
write 0x1f801810 0x012c012c

loop:
j loop
