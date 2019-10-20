.org 0x80010000
.log

.macro load register value
lui register, >>value
ori register, register, <<value
.endmacro

main:

load $t0, 0x1f801814
j main
