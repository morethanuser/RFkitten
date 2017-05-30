from re import compile,sub,subn,findall

# regexp for data rates
ook_one={}
ook_one[1] = compile("1{3}0")
ook_one[2] = compile("1{6}0")
ook_one[4] = compile("1{12}0")
ook_one[8] = compile("1{24}0")

ook_zero={}
ook_zero[1]  = compile("10{3,}")
ook_zero[2]  = compile("10{6,}")
ook_zero[4]  = compile("10{12,}")
ook_zero[8]  = compile("10{24,}")

# list of know keys
know_keys = [
   ('doorbell_button_1_first',  "10001011111110100000010"),
   ('doorbell_button_1',       "110001011111110101010010"),
   ('doorbell_button_2_first',  "10001011111110100000000"),
   ('doorbell_button_2',       "110001011111110101010000"),
]

def analyze_ook(data, baud, bin_input=False, show_original=True):
   bin_str = ""

   # if input is already a "bin string" e.g. "11110001001010101", do nothing
   # else convert raw data to above string
   if (not bin_input): 
      bin_str = ''.join(format(ord(byte), '08b') for byte in data)
   else:
      bin_str = data

   # determine speed of data by checking every speed regexp
   # then sort tupple and return ook_one with biggest match
   speed = sorted(ook_one, key=lambda obj:ook_one[obj].subn('', bin_str))[0]

   # use matched regex to normalize data into _ZERO_ and _ONE_, remove every
   # tramsnission glitch at the end by removing 1 and 0 orphans
   normalized_bin_str = sub('[1,0]', '', ook_one[speed].sub('_ONE_', ook_zero[speed].sub('_ZERO_', bin_str)))

   # change back normalized string with '_ZERO_', '_ONE_' to '1' and '0'
   decoded = sub('_ONE_', '1', sub('_ZERO_', '0', normalized_bin_str))
  
   # only show logner ook_ones
   if (len(decoded) < 4):
      return
   # search key in know keys
   found_key = [key[0] for key in know_keys if decoded == key[1]]

   if found_key == []:
      found_key = "unknown"
   else:
      found_key = found_key[0]

   # present data
   print "Packet len: {} speed: {} OOK decoded: {} key: {}".format(len(bin_str) / 8, baud / speed, decoded, found_key)
   if (show_original):
      print "Original: {}".format(bin_str)
      print

