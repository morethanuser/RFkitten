from enum import Enum
from math import pow,floor,ceil
from re import findall

import serial,sys
from time import sleep

class Config(object):
   IOCFG2   = 0x00
   IOCFG1   = 0x01
   IOCFG0   = 0x02
   FIFOTHR  = 0x03
   SYNC1    = 0x04
   SYNC0    = 0x05
   PKTLEN   = 0x06
   PKTCTRL1 = 0x07
   PKTCTRL0 = 0x08
   ADDR     = 0x09
   CHANNR   = 0x0A
   FSCTRL1  = 0x0B
   FSCTRL0  = 0x0C
   FREQ2    = 0x0D
   FREQ1    = 0x0E
   FREQ0    = 0x0F
   MDMCFG4  = 0x10
   MDMCFG3  = 0x11
   MDMCFG2  = 0x12
   MDMCFG1  = 0x13
   MDMCFG0  = 0x14
   DEVIATN  = 0x15
   MCSM2    = 0x16
   MCSM1    = 0x17
   MCSM0    = 0x18
   FOCCFG   = 0x19
   BSCFG    = 0x1A
   AGCCTRL2 = 0x1B
   AGCCTRL1 = 0x1C
   AGCCTRL0 = 0x1D
   WOREVT1  = 0x1E
   WOREVT0  = 0x1F
   WORCTRL  = 0x20
   FREND1   = 0x21
   FREND0   = 0x22
   FSCAL3   = 0x23
   FSCAL2   = 0x24
   FSCAL1   = 0x25
   FSCAL0   = 0x26
   RCCTRL1  = 0x27
   RCCTRL0  = 0x28
   FSTEST   = 0x29
   PTEST    = 0x2A
   AGCTEST  = 0x2B
   TEST2    = 0x2C
   TEST1    = 0x2D
   TEST0    = 0x2E
   PATABLE  = 0x3E

   _X_OSC   = 26000000
   _F_DIV   = _X_OSC/pow(2,16)
   _D_DIV   = _X_OSC/pow(2,17)
   _S_DIV   = _X_OSC/pow(2,18)

   _MHZ     = pow(10, 6)
   _KHZ     = pow(10, 3)

   cfg_init = {}

   cfg_init[IOCFG2]   = 0x01    # 1 rx therlshold or end of packet E cs
   cfg_init[IOCFG0]   = 0x03    # assert when TX fifo == 64
   cfg_init[FIFOTHR]  = 0x4F    # rx fifo  7 = 32, F = 64

   # two below are partialy configured
   cfg_init[PKTCTRL0] = 0x00    # fixed packet length, no crc, no whitening

   cfg_init[FSCTRL1]  = 0x0C    # Frequency Synthesizer Control

   #cfg_init[MDMCFG2]  = 0x04    # no preambule, sync carrier sense above threshold

   cfg_init[MCSM1]    = (0x00 << 4) | (0x03 << 2) # cca mode = always, rxoff mode = stay_in_rx

   cfg_init[MCSM0]    = 0x18    # Main Radio Control State Machine Configuration

   cfg_init[FOCCFG]   = 0x1D    # Frequency Offset Compensation Configuration

   cfg_init[BSCFG]    = 0x1C    # Bit Synchronization Configuration

   #cfg_init[AGCCTRL2] = 0xC0    # TODO add LNA and DVGA gain settings
   cfg_init[AGCCTRL2] = 0x00    # maximum LNA and DVGA (used in absolute mode)
   cfg_init[AGCCTRL1] = 0x40    # AGC lna priority (default)
   cfg_init[AGCCTRL0] = 0xB0    # filter length settings

   cfg_init[WORCTRL]  = 0xFB    # Wake On Radio Control

   cfg_init[FREND1]   = 0x56    # Front End RX Configuration
   cfg_init[FREND0]   = 0x11    # 0x11 ASK 0x10 FSK no PA ramping

   cfg_init[FSCAL3]   = 0xEA
   cfg_init[FSCAL2]   = 0x2A
   cfg_init[FSCAL1]   = 0x00
   cfg_init[FSCAL0]   = 0x1F

   cfg_init[TEST2]    = 0x81
   cfg_init[TEST1]    = 0x35
   cfg_init[TEST0]    = 0x09

   debug = True

   def __init__(self, debug=True):
      self.debug = debug
      self.cfg_frequency = {}
      self.cfg_deviation = {}
      self.cfg_channel_spacing = {}
      self.cfg_channel_bandwidth = {}
      self.cfg_modulation = {}
      self.cfg_sensivity = {} 
      self.cfg_manchaster = {}
      self.cfg_channel = {}
      self.cfg_address = {}
      self.cfg_sync_word = {}
      self.cfg_packet_len = {}
      self.cfg_data_rate = {}
      self.cfg_pa_table = {}
      self.cfg_crc = {}
      self.cfg_append_status = {}
      self.cfg_preamble = {}

   def join_config(self, *partial_cfg):
      cfg_f = {}
      for cfg in partial_cfg:
         for key in cfg:
            if key in cfg_f:
               cfg_f[key] |= cfg[key]
            else:
               cfg_f[key] = cfg[key]
      return cfg_f

   def getConfig(self):
      return self.join_config(
               self.cfg_init,
               self.cfg_frequency,
               self.cfg_deviation,
               self.cfg_channel_spacing,
               self.cfg_channel_bandwidth,
               self.cfg_modulation,
               self.cfg_sensivity,
               self.cfg_manchaster,
               self.cfg_channel,
               self.cfg_address,
               self.cfg_sync_word,
               self.cfg_packet_len,
               self.cfg_data_rate,
               self.cfg_manchaster,
               self.cfg_pa_table,
               self.cfg_crc,
               self.cfg_append_status,
               self.cfg_preamble
      )

   def setFrequency(self, freq):
      f_div = int(floor(freq  * self._MHZ) / self._F_DIV)

      self.cfg_frequency[self.FREQ2] = f_div >> 16
      self.cfg_frequency[self.FREQ1] = f_div >> 8 & 0xFF
      self.cfg_frequency[self.FREQ0] = f_div & 0xFF

      if(self.debug):
         print "Frequency {} Hz".format(int(self._F_DIV * ceil(f_div)))

   def setDeviation(self, deviation):
      f_div = int(floor((deviation * self._KHZ) / self._D_DIV))

      y = 0
      if f_div < 8:
         x = 0
      else:
         while(1):
            x = floor(f_div / pow(2, y) - 8)
            if (x > 0x7):
               y = y + 1
               if (y >= 0x7):
                  x = 0x7
                  y = 0x7
                  break
            else:
               break

      self.cfg_deviation[self.DEVIATN] = int(x) | y << 4

      if(self.debug):
         print "Deviation {} Hz".format(self._D_DIV * (8 + x) * pow(2, y))

   def setChannelSpacing(self, spacing):
      f_div = int(floor((spacing * self._KHZ) / self._S_DIV))

      y = 0
      if f_div < 256:
         x = 0
      else:
         while(1):
            x = floor(f_div / pow(2, y) - 256)
            if (x > 0xFF):
               y = y + 1
               if (y > 0x3):
                  x = 0xFF
                  y = 0x3
                  break
            else:
               break

      y = int(y)
      x = int(x)

      self.cfg_channel_spacing[self.MDMCFG1] = y # no preambule
      self.cfg_channel_spacing[self.MDMCFG0] = x

      if(self.debug):
         print "Channel spacing {} Hz".format(self._S_DIV * (256 + x) * pow(2, y))

   def setChannelBandwidth(self, bandwidth):
      y = 0
      if (bandwidth == 0):
         x = 0x3
         y = 0x3
      else:
         while(1):
            x = int(floor((self._X_OSC / (bandwidth * self._KHZ) / 8 / pow(2, y)) - 4)) 
            if (x <= -4):
               x = 0
               y = 0
               break
            if (x > 0x3):
               y = y + 1
               if (y > 0x3):
                  x = 0x3
                  y = 0x3
                  break
            else:
               break

      self.cfg_channel_bandwidth[self.MDMCFG4] = y << 6 | x << 4

      if(self.debug):
         print "Bandwidth {} Hz".format(self._X_OSC / (8 * (4 + x) * pow(2, y)))

   def setDataRate(self, data_rate):
      y = 0
      while(1):
         x = int(floor((data_rate * 1.0 / self._X_OSC * pow(2, 28)) / pow(2, y) - 256)) 
         if (x > 0xFF):
            y = y + 1
            if (y > 0xF):
               x = 0xFF
               y = 0xF
               break
         else:
            break

      if (x < 0):
         x = 0
         y = 0

      self.cfg_data_rate[self.MDMCFG4] = y
      self.cfg_data_rate[self.MDMCFG3] = x

      if(self.debug):
         print "Baudrate {} baud".format((256 + x) * pow(2, y) * self._X_OSC / pow(2, 28))

   def setModulation(self, modulation):
      mod = {}

      mod['2-FSK']   = (0x00 << 4)
      mod['GFSK']    = (0x01 << 4)
      mod['ASK/OOK'] = (0x03 << 4)
      mod['4-FSK']   = (0x04 << 4)
      mod['MSK']     = (0x07 << 4)

      if modulation in mod:
         self.cfg_modulation[self.MDMCFG2] = mod[modulation]
      else:
         print "Wrong modulation, supprted are: {}".format(mod.keys())
         raise RuntimeError

      if(self.debug):
         print "Modulation {}".format(modulation)

   def setSensivity(self, sensivity, additional_adjust = "0 dB"):
      absolute = {}
      absolute["24 dB"] = 0
      absolute["27 dB"] = 1
      absolute["30 dB"] = 2
      absolute["33 dB"] = 3
      absolute["36 dB"] = 4
      absolute["38 dB"] = 5
      absolute["40 dB"] = 6
      absolute["42 dB"] = 7

      adjust = {}
      adjust["disabled"] = 8
      adjust["-7 dB"]    = 9
      adjust["-6 dB"]    = 10 
      adjust["-5 dB"]    = 11
      adjust["-4 dB"]    = 12
      adjust["-3 dB"]    = 13
      adjust["-2 dB"]    = 14
      adjust["-1 dB"]    = 15
      adjust["0 dB"]     = 0
      adjust["+1 dB"]    = 1
      adjust["+2 dB"]    = 2
      adjust["+3 dB"]    = 3
      adjust["+4 dB"]    = 4
      adjust["+5 dB"]    = 5
      adjust["+6 dB"]    = 6
      adjust["+7 dB"]    = 7

      relative = {}
      relative["+6 dB"]  = 1
      relative["+10 dB"] = 2
      relative["+14 dB"] = 3

      if (sensivity in absolute) and (additional_adjust in adjust):
         self.cfg_sensivity[self.AGCCTRL1] = adjust[additional_adjust]
         self.cfg_sensivity[self.AGCCTRL2] = absolute[sensivity]

         if(self.debug):
            print "Sensivity absolute {0} with adjust {1}".format(sensivity, additional_adjust)
      elif sensivity in relative:
         self.cfg_sensivity[self.AGCCTRL1] = relative[sensivity] << 4 | adjust["disabled"]

         if(self.debug):
            print "Sensivity relative {}".format(sensivity)
      else:
         print "Wrong sensivity, absolute supprted are: {0}, adjusts {1}".format(absolute.keys(), adjust.keys())
         print "Relative supprted are: {0}".format(relative.keys())

         raise RuntimeError

   def setManchaster(self, on):
      if on:
         self.cfg_manchaster[self.MDMCFG2] = (1<<3)

         if(self.debug):
            print "Manchaster on"
      else:
         if(self.debug):
            print "Manchaster off"

   def setChannel(self, num):
      self.cfg_channel[self.CHANNR] = num

      if(self.debug):
         print "Channel {}".format(num)

   def setAddress(self, addr, check="no"):
      self.cfg_address[self.ADDR] = addr

      address_check = {}
      address_check["no"]                   = 0x00
      address_check["check, no bc"]         = 0x01 # no broadcast check
      address_check["check, 0x00 "]         = 0x10
      address_check["check, 0x00 and 0xFF"] = 0x11

      if check in address_check:
         self.cfg_init[self.PKTCTRL1] = address_check[check] # TODO ERRROR !!!
      else:
         print "Wrong address check setting, supprted are: {}".format(address_check.keys())
         raise RuntimeError
      
      if(self.debug):
         print "Address {0}, check {1}".format(hex(addr), check)

   def setSyncWord(self, sync_word, sync="none + cs", preamble=2):
      self.cfg_sync_word[self.SYNC1] = sync_word >> 8
      self.cfg_sync_word[self.SYNC0] = sync_word & 0xFF

      sync_mode = {}
      sync_mode["none"]       =  0 
      sync_mode["15/16"]      =  1 
      sync_mode["16/16"]      =  2 
      sync_mode["30/32"]      =  3 
      sync_mode["none + cs"]  =  4 
      sync_mode["15/16 + cs"] =  5 
      sync_mode["16/16 + cs"] =  6 
      sync_mode["30/32 + cs"] =  7 

      preamble_table = {}
      preamble_table[2]  = 0
      preamble_table[3]  = 1
      preamble_table[4]  = 2
      preamble_table[6]  = 3
      preamble_table[8]  = 4
      preamble_table[12] = 5
      preamble_table[16] = 6
      preamble_table[24] = 7

      if preamble in preamble_table:
         self.cfg_preamble[self.MDMCFG1] = preamble_table[preamble] << 2 
      else:
         print "Wrong preamble, supprted are: {}".format(premable_table.keys())
         raise RuntimeError

      if sync in sync_mode:
         self.cfg_sync_word[self.MDMCFG2] = sync_mode[sync]
      else:
         print "Wrong sync mode, supprted are: {}".format(sync_mode.keys())
         raise RuntimeError

      if(self.debug):
         print "Sync workd {0}, mode {1}, preamble {2}".format(hex(sync_word), sync, preamble)

   def setPacketLen(self, l):
      if (l < 0 or l > 255):
         print "Wrong packet len"
         raise RuntimeError
      else:
         self.cfg_packet_len[self.PKTLEN] = l

      if(self.debug):
         print "Packet len {}".format(l)

   def setPaTable(self, power):
      pa_table = {}
      pa_table["none"]        = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
      pa_table["ultra low"]   = [0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
      pa_table["low"]         = [0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
      pa_table["normal"]      = [0x00, 0x12, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
      pa_table["moderate"]    = [0x00, 0x50, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
      pa_table["high"]        = [0x00, 0xCD, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
      pa_table["ultra high"]  = [0x00, 0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

      if power in pa_table:
         self.cfg_pa_table[self.PATABLE] = pa_table[power]
      else:
         print "Wrong power setting, supprted are: {}".format(pa_table.keys())
         raise RuntimeError

      if(self.debug):
         print "Power table [{}]".format(' '.join('0x%02x'%p for p in pa_table[power]))

   def setCRC(self, on):
      if on:
         self.cfg_manchaster[self.PKTCTRL0] = (1<<2)
         if(self.debug):
            print "CRC on"
      else:
         self.cfg_manchaster[self.PKTCTRL0] = (0<<2)
         if(self.debug):
            print "CRC off"

   def setAppendStatus(self, on):
      """ this is not working, probbably needs change in firmware ? """
      if on:
         self.cfg_append_status[self.PKTCTRL1] = (1<<2)
         if(self.debug):
            print "Append RSSI and CRC status on"
      else:
         self.cfg_append_status[self.PKTCTRL1] = (0<<2)
         if(self.debug):
            print "Append RSSI and CRC status off"



   def setProfile_443_OOK(self):
      self.setFrequency(433.92)
      self.setDeviation(0)
      self.setChannelSpacing(0)
      self.setChannelBandwidth(0)
      self.setDataRate(4800)
      self.setModulation("ASK/OOK")
      self.setSensivity("+6 dB")
      self.setManchaster(False)
      self.setChannel(0)
      self.setAddress(0)
      self.setSyncWord(0)
      self.setPacketLen(255)
      self.setPaTable("ultra low")
      self.setCRC(False)
      self.setAppendStatus(False)


   def setProfile_443_FSK(self):
      self.setFrequency(433.92)
      self.setDeviation(5)
      self.setChannelSpacing(0)
      self.setChannelBandwidth(0)
      self.setDataRate(4800)
      self.setModulation("2-FSK")
      self.setSensivity("+6 dB")
      self.setManchaster(False)
      self.setChannel(0)
      self.setAddress(0)
      self.setSyncWord(0)
      self.setPacketLen(255)
      self.setPaTable("ultra low")
      self.setCRC(False)
      self.setAppendStatus(False)

class Device():
   path = ""
   timeout = 0
   serial = None

   def __init__(self, device_path, timeout=1):
      self.path = device_path
      self.timeout = timeout

   def open(self):
      self.serial = serial.Serial(
         port = self.path,
         baudrate = 4000000,
         timeout = self.timeout
      )

   def configure(self, config):
      sleep(0.02)
      # begin of config
      self.serial.setDTR(0)
      self.serial.setDTR(1)

      for reg, value in config.iteritems():
         if isinstance(value, list):
            for v in value:
               self.serial.write(bytearray([reg, v]))
               #print "cfg({0}, {1});".format(reg, v)
         else:
            self.serial.write(bytearray([reg, value]))
            #print "cfg({0}, {1});".format(reg, value)

      # end of config
      self.serial.write(bytearray([0xff]))
      sleep(0.01)

   def write(self, data):
      if isinstance(data, list):
         self.serial.write(bytearray(data))
      else:
         self.serial.write(chr(data))

   def read(self, size):
      arr = bytearray(size)
      return (self.serial.readinto(arr), arr)

   def close(self):
      self.serial.close()



class Manager:
   config = None
   device = None

   def __init__(self, config, device):
      self.config = config
      self.device = device

   def configure(self, config=None):
      if (config == None):
         self.device.configure(self.config.getConfig())
      else:
         self.device.configure(config)

   def open(self):
      self.device.open()

   def close(self):
      self.device.close()

   def sendOOKStatic(self, bin_str, 
                      one  = "1110",
                      zero = "1000",
                      repeat = 1,
                      suffix_zero_bytes = 1,
                      prefix_zero_bytes = 1):
      self.sendBinStr(bin_str, one, zero, repeat, suffix_zero_bytes, prefix_zero_bytes)

   def sendOOKVariable(self, bin_str,
                      one  = "1111100000000000000000000",
                      zero = "111110000000000",
                      repeat = 1,
                      suffix_zero_bytes = 0,
                      prefix_zero_bytes = 0):
      self.sendBinStr(bin_str, one, zero, repeat, suffix_zero_bytes, prefix_zero_bytes)

   def sendBinStr(self, bin_str, one, zero, repeat = 1, suffix_zero_bytes=0, prefix_zero_bytes=0):
      code = ""
      # expand 1:1 for 2.4kbps
      for c in bin_str:
         if c == '1':
            code = code + one
         else:
            code = code + zero

      # split string into array
      bin_string_array = findall('.{1,8}', code)

      # if we end with shorter data than 8 bits, adjust last byte
      if (len(bin_string_array[-1]) < 8):
         bin_string_array[-1] += "0" * (8 - len(bin_string_array[-1]))

      data = [int(n, 2) for n in bin_string_array]

      # append prefix for OOK or address byte
      #data.insert(0, self.config.cfg_address[self.config.ADDR])
      for _ in xrange(0, prefix_zero_bytes):
         data.insert(0, 0)

      for _ in xrange(0, suffix_zero_bytes):
         data.append(0)

      self.config.setPacketLen(len(data))
      self.configure(self.config.cfg_packet_len)

      for _ in xrange(0, repeat):
         self.device.write(data)

   def readerLoop(self, keep_running, packet_len, func):
      while(keep_running()):
         try:
            (read_bytes, data) = self.device.read(packet_len)
         except Exception, e:
            print "readerLoop: {}".format(e)
            break
         if (read_bytes > 0):
            func(data)

