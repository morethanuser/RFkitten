#ifndef _H_CC1101_DONGLE_H_
#define _H_CC1101_DONGLE_H_

#define H(a,b) a |=(1<<(b))
#define L(a,b) a &=~(1<<(b))
#define IS(a,b) bit_is_set(a,b)
#define BS(a,b) (a & (1<<(b)))


#define ENABLE   L(PORTB, PB0)
#define DISABLE  H(PORTB, PB0)

#define LED_ON    H(PORTE, PE6)
#define LED_OFF   L(PORTE, PE6)

// some of CC1101 registers and states
#define TXFIFO      0x3F
#define RXFIFO      0xBF
#define STX         0x35
#define SRX         0x34
#define SFTX        0x3B
#define SFRX        0x3A
#define READ_BURST  0xC0
#define WRITE_BURST 0x40
#define RXBYTES     0x3B
#define TXBYTES     0x3A

#define PKTLEN      0x06
#define PATABLE     0x3E

#define MARCSTATE   0x35

#define SIDLE       0x36
#define SRES        0x30


#define MARCSTATE_IDLE             0x01
#define MARCSTATE_RX               0x0D
#define MARCSTATE_TXFIFO_UNDERFLOW 0x16


#endif

#ifndef F_CPU
   #error CPU speed unknown
#endif


