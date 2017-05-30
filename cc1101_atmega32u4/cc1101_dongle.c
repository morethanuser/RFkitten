#include "cc1101_dongle.h"
#include "usb_desc.h"

#include <avr/io.h>
#include <avr/wdt.h>
#include <avr/power.h>
#include <avr/interrupt.h>


struct spi_reg { 
   uint16_t reg;
   uint16_t val;
};


uint8_t spi_write(uint8_t data) {
   L(TIMSK0, TOIE0);
      SPDR = data;
      while(!(SPSR & (1 << SPIF)));
   H(TIMSK0, TOIE0);
   return SPDR;
}


uint8_t spi_strobe(uint8_t s) {
   uint8_t r = 0;
   ENABLE;
      r = spi_write(s);
   DISABLE;
   return r;
}


void spi_reg_write(struct spi_reg *r) {
   ENABLE;
      spi_write(r->reg | WRITE_BURST);
      spi_write(r->val);
   DISABLE;
}

void spi_patable_write(uint8_t *patable) {
   uint8_t i;
   ENABLE;
      spi_write(PATABLE | WRITE_BURST);
      for (i = 0; i < 8; i++)
         spi_write(patable[i]);

   DISABLE;
}



void spi_reg_read(struct spi_reg *r) {
   ENABLE;
      spi_write(r->reg | READ_BURST);
      r->val = spi_write(0);
   DISABLE;
}


uint8_t spi_reg_read_single(uint8_t a) {
   uint8_t r = 0;
   ENABLE;
      spi_write(a | READ_BURST);
      r = spi_write(0);
   DISABLE;
   return r;
}


USB_ClassInfo_CDC_Device_t serial = {
		.Config = {
				.ControlInterfaceNumber   = INTERFACE_ID_CDC_CCI,
				.DataINEndpoint           = {
						.Address          = CDC_TX_EPADDR,
						.Size             = CDC_TXRX_EPSIZE,
						.Banks            = 1,
					},
				.DataOUTEndpoint = {
						.Address          = CDC_RX_EPADDR,
						.Size             = CDC_TXRX_EPSIZE,
						.Banks            = 1,
					},
				.NotificationEndpoint = {
						.Address          = CDC_NOTIFICATION_EPADDR,
						.Size             = CDC_NOTIFICATION_EPSIZE,
						.Banks            = 1,
					},
			},
	};


void EVENT_USB_Device_Connect(void) { }
void EVENT_USB_Device_Disconnect(void) { }
void EVENT_USB_Device_ConfigurationChanged(void) { CDC_Device_ConfigureEndpoints(&serial); }
void EVENT_USB_Device_ControlRequest(void) { CDC_Device_ProcessControlRequest(&serial); }


uint8_t usb_cfg = 0;
void EVENT_CDC_Device_ControLineStateChanged(USB_ClassInfo_CDC_Device_t *const CDCInterfaceInfo) {
   L(EIMSK, INT2);
	usb_cfg = (CDCInterfaceInfo->State.ControlLineStates.HostToDevice & CDC_CONTROL_LINE_OUT_DTR) != 0;
}


void led_strobe() {
   static uint8_t strobe = 0;
   if(strobe) {
      strobe = 0;
      LED_ON;
   }
   else {
      LED_OFF;
      strobe = 1;
   }
}


uint8_t packet_len = 0;
uint8_t bytes_to_send = 0;

uint8_t buff[128] = {};
uint8_t buff_idx = 0;

uint8_t timer = 0;


ISR(TIMER0_OVF_vect) {  
   CDC_Device_USBTask(&serial);
   USB_USBTask();

   timer++;

   // blink led periodically
   if (timer > 40) {
      led_strobe();
      timer = 0;
   }
}  


// FIFO above threshold interrupt
ISR(INT2_vect) {
   volatile uint8_t val = spi_reg_read_single(RXBYTES);
   volatile uint8_t i = 0;

   ENABLE;
   spi_write(READ_BURST | RXFIFO);
   for(i = 0; i < (val & 0x7F); i++) {
      buff[buff_idx++] = spi_write(0);
   } 
   DISABLE;
   
   // this is only good for small data rates,
   // probably ring buffer would be better here
   for(i = 0; i < buff_idx; i++) {   
      CDC_Device_SendByte(&serial, buff[i]);
   }
   buff_idx = 0;

   CDC_Device_USBTask(&serial);
   USB_USBTask();
}



/****************************************************************************/
/*                                                                          */
/****************************************************************************/
int main()
{
   H(DDRE, PE6);  // led

   L(DDRD, PD2);  // GDO2
   L(DDRD, PD3);  // GDO0

   L(PORTD, PD2);
   L(PORTD, PD3);

   H(DDRB, PB0);  // SS
   H(DDRB, PB1);  // SCK
   H(DDRB, PB2);  // MOSI
   L(DDRB, PB3);  // MISO

   DISABLE;
   H(SPSR, SPI2X);
   H(SPCR, MSTR);
   H(SPCR, SPE);

	MCUSR &= ~(1 << WDRF);
	wdt_disable();
	clock_prescale_set(clock_div_1);
	USB_Init();

   H(TCCR0B, CS00);
   H(TCCR0B, CS02);
   H(TIMSK0, TOIE0);

   H(EICRA, ISC20);
   H(EICRA, ISC21);
   L(EIMSK, INT2);

   GlobalInterruptEnable();

   // reset CC1101
   DISABLE; 
   _delay_us(50);
   ENABLE; 
   spi_strobe(SRES);
   _delay_us(200);
   spi_strobe(SIDLE);
   spi_strobe(SFRX);
   spi_strobe(SFTX);

   int16_t c = 0;
   struct spi_reg r;
   uint8_t r_idx = 0;
   uint8_t pa_table[8] = { 0 };
   uint8_t pa_table_idx = 0;

   uint8_t state = 0;

	while(1) {
		c = CDC_Device_ReceiveByte(&serial);

      if (c < 0)
         continue;

      // if we have seen DTR before, push config into cc1101
      if (usb_cfg > 0) {

         if (usb_cfg == 1) {
             // first stage is to flush buffs and change cc1101 state
             // to idle
             usb_cfg = 2;

             spi_strobe(SIDLE);
             while(spi_reg_read_single(MARCSTATE) != MARCSTATE_IDLE);
             spi_strobe(SFRX);
//              while(spi_reg_read_single(MARCSTATE) != MARCSTATE_IDLE);
             spi_strobe(SFTX);
//              while(spi_reg_read_single(MARCSTATE) != MARCSTATE_IDLE);
             buff_idx = 0;

             for(pa_table_idx = 0; pa_table_idx < 8; pa_table_idx++)
               pa_table[pa_table_idx] = 0;
             pa_table_idx = 0;
         }

         // if we hit end of config 0xFF, back to normal operation, enable
         // fifo interrupt
         if (c == 0xff && r_idx == 0) {
            usb_cfg = 0;
            spi_strobe(SRX);
            while(spi_reg_read_single(MARCSTATE) != MARCSTATE_RX);
            H(EIMSK, INT2);
            continue;
         }

         if (r_idx == 0) {
            r.reg = c;
            r_idx++;
         } else {
            r.val = c;
            r_idx = 0;

            // in this special case, copy PKTLEN to variable
            if (r.reg == PKTLEN) {
               packet_len = r.val;
               bytes_to_send = packet_len;
            }

            if (r.reg == PATABLE) {
               if (pa_table_idx < 7) {
                  pa_table[pa_table_idx] = r.val;
                  pa_table_idx++;
               }
               else {
                  pa_table[pa_table_idx] = r.val;
                  spi_patable_write(pa_table);
            
                  for(pa_table_idx = 0; pa_table_idx < 8; pa_table_idx++)
                     pa_table[pa_table_idx] = 0;
                  pa_table_idx = 0;
               }

            } else {
               spi_reg_write(&r);
            }
         }

      } else {

         // we've got some data, push it to TX fifo, then
         // push over air
         ENABLE;
            spi_write(TXFIFO);
            spi_write(c);
         DISABLE;

         bytes_to_send--;

         if(bit_is_set(PIND, PD3) || bytes_to_send == 0) {
            spi_strobe(STX);

            do {
               state = spi_reg_read_single(MARCSTATE);
            } while(state != MARCSTATE_TXFIFO_UNDERFLOW && 
                    state != MARCSTATE_IDLE);

            spi_strobe(SFTX);
            while(spi_reg_read_single(MARCSTATE) != MARCSTATE_IDLE);
         }
         
         if (bytes_to_send == 0) {
            bytes_to_send = packet_len;
            spi_strobe(SRX);
            while(spi_reg_read_single(MARCSTATE) != MARCSTATE_RX);
         }
      }
   } 
}
