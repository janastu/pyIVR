import os
import signal
from form import Form
import fcntl
import commands

''' Alarm handling function = If timeout occurs, what to do '''
def timeout_handler(signum, frame):
    raise Exception('Timeout')
    
def play_audio(speaker, audiofile):
    os.system("PULSE_SINK=" + speaker + " cvlc --no-loop --play-and-exit " + 
              audiofile)
    
def get_raw_input():
    return raw_input("___Enter Key___\n")
    #while not dtmf: dtmf = mygsm.read_dtmf() 
    #return dtmf


class IvrDialog(object):
    
    def __init__(self, 
                 csv_file = '../docs/call_flow.csv',
                 audiopath = '../audios',
                 datapath = '../data',
                 call_flow_record = "call_flow_record.txt",
                 input_handler = get_raw_input,
                 speaker = '1',
                 volume = '100'
                 ):

        self.default_timeout = 1
        self.csv_to_ivr(csv_file)
        
        self.audiopath = audiopath
        self.datapath = datapath

        self.call_flow_record = self.datapath + '/' + call_flow_record
        self.create_call_flow_record(csv_file)
        
        self.input_handler = input_handler
        
        self.speaker = speaker
        
        self.set_volume(speaker, volume)
        
        self.clean_datapath()
        
        #self.levels = 0
        
    def clean_datapath(self):
        numbers = commands.getoutput("ls " + self.datapath + " | grep temp ")
        if not numbers: return
        numbers = numbers.split("\n")
        
        for number in numbers:
            self.update_record(number.split("_")[1])
        
    def fetch_record(self, number):
        ''' Get the call progress record for a given phone number '''

        with open(self.call_flow_record,'r') as f:
            log = f.readlines() 
    
        ### First two lines are headings, so ignore and go through other lines
        for line in log[2:]:
            record = line.split(',')

            if number == record[0]:
                record = [w.replace('\n', '') for w in record]
                return record
    
        #print "levels = ", self.levels
        ### if no record found, send an empty record 
        record = ['']*(self.levels+1)
        record[0] = number
        return record

        
    def set_volume(self, speaker, volume):
        os.system("pactl set-sink-volume " + speaker + " " + volume + "%")
      

    def create_call_flow_record(self, csv_file):
    
        if os.path.isfile(self.call_flow_record):
            return 
        
        with open(csv_file,'r') as f:
            dialog = f.readlines()
            
        dialog = dialog[:2]
        
        with open(self.call_flow_record, 'w') as f:
            dialog = "".join(dialog)
            f.write(dialog)
            

    def csv_to_ivr(self, csv_file):

        with open(csv_file,'r') as f:
            dialog = f.readlines()
    

        ### Remove unnecessary lines
        dialog = dialog[:11]

        ### Remove newline, carriage return, and double quotation mark that 
        ###  spreadsheet software might introduce
        dialog = [w.replace('\n', '').replace('"','').replace('\r','') for w 
                  in dialog]
        #print dialog
        
        self.form_id = dialog[0].split(',')[1:]
        self.levels = len(self.form_id)
        print "no.of levels = ", self.levels
        #print form_id
        audio_file = dialog[1].split(',')[1:]
        #print audio_file
        valid_input = dialog[2].split(',')[1:]
        #print valid_input
        goto_next = dialog[3].split(',')[1:]
        #print "GOTO NEXT = ", goto_next
        timeout = dialog[4].split(',')[1:]
        timeout = [int(i) if i else self.default_timeout for i in timeout]
        #print timeout
        noinput_prompt = dialog[5].split(',')[1:]
        #print noinput_prompt
        noinput_goto = dialog[6].split(',')[1:]
        #print noinput_goto
        noinput_limit = dialog[7].split(',')[1:]
        noinput_limit = [int(i) if i else '' for i in noinput_limit]
        #print noinput_limit
        nomatch_prompt = dialog[8].split(',')[1:]
        #print nomatch_prompt
        nomatch_goto = dialog[9].split(',')[1:]
        #print nomatch_goto
        nomatch_limit = dialog[10].split(',')[1:]
        nomatch_limit = [int(i) if i else '' for i in nomatch_limit]
        #print nomatch_limit
        

        self.dialog = {}
        for i in range(self.levels):
            temp = Form()
            temp.audio_file_name = audio_file[i]
            
            if ';' in valid_input[i] : 
                temp.valid_input = valid_input[i].split(';') 
            else : temp.valid_input = [valid_input[i]]
            
            if ';' in goto_next[i] : temp.goto_next = goto_next[i].split(';') 
            else : temp.goto_next = [goto_next[i]]
            
            temp.timeout = timeout[i]
            temp.noinput_prompt = noinput_prompt[i]
            temp.noinput_goto = noinput_goto[i]
            temp.noinput_limit = noinput_limit[i]
    
            temp.nomatch_prompt = nomatch_prompt[i]
            temp.nomatch_goto = nomatch_goto[i]
            temp.nomatch_limit = nomatch_limit[i]
    
            self.dialog[self.form_id[i]] = temp
            

   
    def start(self, number):

        record = self.fetch_record(number)
        print record

        with open(self.datapath+'/temp_'+number,'w') as f:
            f.write(','.join(record) + '\n')
            f.flush()
            
        signal.signal(signal.SIGALRM, timeout_handler)
        self.noinput_ctr = 0
        self.nomatch_ctr = 0
        key = '0'
        
        while not key == '999':
        
            print "Form ID: #", key
            
            print "\tPlaying Audio File: ", self.dialog[key].audio_file_name
            play_audio(self.speaker, self.audiopath + '/' + 
                       self.dialog[key].audio_file_name + ".mp3")  
                       
            form_input = self.execute_grammar(key)
            print "\tInput is: ", form_input            
           
            
            oldkey = key                
            key,form_input = self.form_filled(key, form_input)
            #print 'Key from form_filled is = ', key
            
            if key == 'A': 
                key = (record[1] if record[1] else '3')
        
                if key in ['4','5','6','7','8']:
                    key = '4'


            if not ((form_input == 'noinput') or (form_input =='nomatch') or
                    (form_input == 'exit')):
                if not ((key == '998') or (key == '999')):
                    self.save_record(record, oldkey, form_input, key)
            
            print "\tGoingTo Form ID: #", key
            
        self.update_record(number)
            
            
    def get_key_index(self, key):
        return self.form_id.index(key)+1

    def save_record(self, record, oldkey, form_input, key):
        '''
            Create a new record for the first time. 
            Reads the entire file, and appends the new record and writes to the 
            file again.
        '''

        #print 'Record = ', record
        #print 'Oldkey = ', oldkey, '\tForm Input = ', form_input
        #print 'Key = ', key

        index = self.get_key_index(oldkey)
        record[index] = form_input
        record[1] = key

        line = ','.join(record) + '\n'

        #print line
        #print datapath+'/'+record[0]

        with open(self.datapath+'/temp_'+record[0],'w') as f:
            f.write(line)
            f.flush()
            #print log
                
    def update_record(self, phone_number):
        
        with open(self.datapath+'/temp_'+phone_number,'r') as f:
            line_to_record = f.readline()
        
        f = open(self.call_flow_record,'r+w')
        fcntl.flock(f, fcntl.LOCK_EX)
        log = f.readlines()
        #print 'Update Record ', log
        for line in log[2:]:
                record = line.split(',')

                if phone_number == record[0]:
                    log.remove(line)
                    break
            
        #print 'After removing old entry - ', log
        log.append(line_to_record)
        log = ''.join(log)
        #print 'after joining everything - ',log
        f.truncate(0)
        f.seek(0)
        f.write(log)
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()

        os.system('rm '+self.datapath+'/temp_'+phone_number)

     
    def execute_grammar(self, key):
     
        print "************ ", self.dialog[key].valid_input 
          
            
        ### try to get the Form Input within the timeout
        print "\tTimer Duration for Input (in s): ", self.dialog[key].timeout
        try:
            #form_input = ""        
            signal.alarm(self.dialog[key].timeout)
            #form_input = self.input_handler()
            
            ### if a Form is not expecting an input then return '-'
            #if self.dialog[key].valid_input == ['']: form_input = '-'    
            print "\tValid Input(s) are: ", self.dialog[key].valid_input
            
            ### Wait for input
            form_input = self.input_handler(self.dialog[key].valid_input)
            
        ### Error can be Timeout or Call Disconnect
        except Exception as error:
            #print "\tError while getting input is: ", error
            if "Timeout" in error:   form_input = "noinput" 
            #else: form_input = "exit"
            signal.alarm(0)
            
        ### Reset alarm/timeout
        signal.alarm(0)
        

        print "\tUser Entry is: ", form_input
        if form_input == '-' or form_input == 'exit' or form_input == 'noinput':
            return form_input
    
        ### Check whether the entered input has a match in the form
        try:    self.dialog[key].valid_input.index(form_input)
        except: form_input = "nomatch"
    
        return form_input



    def form_filled(self,key,form_input):

        if form_input == "exit": return "999", form_input
        
        elif form_input == "noinput": 
            return self.noinput_action(key, form_input)

        elif form_input == "nomatch":
            return self.nomatch_action(key), form_input
            
        
        ### If DTMF is a valid input, get the corresponding next action
        else:
            self.noinput_ctr = 0
            self.nomatch_ctr = 0
            
            ### If the level didn't expect any input            
            if form_input == '-': i = 0
            
            ### Get the location of DTMF in the valid input list
            else: 
                i = self.dialog[key].valid_input.index(form_input)
                print '\t Index of User Input in Valid Input List is ', i
            
            print "goto Next = ", self.dialog[key].goto_next
            return self.dialog[key].goto_next[i], form_input
    
    
    def nomatch_action(self, key):

        print ("\tNoMatch for Input provided after *** " + 
              self.dialog[key].audio_file_name + ".mp3 *** \t" + 
              " in form #" + key)
                  
        if not self.dialog[key].nomatch_goto == key: 
            return self.dialog[key].nomatch_goto
           
        else:
            if self.nomatch_ctr < self.dialog[key].nomatch_limit:
                        
                if not self.dialog[key].nomatch_prompt == '':
                    print ("\tPlaying NoMatch Prompt: " + 
                            self.dialog[key].nomatch_prompt)
                    
                    play_audio(self.speaker, self.audiopath + "/" + 
                               self.dialog[key].nomatch_prompt + ".mp3")
                
                self.nomatch_ctr += 1
                return key

            else:
                print ("NoMatch Limit of " + str(self.dialog[key].noinput_limit)
                       + " times EXCEEDED !!!")
                return '998'
    

            
    def noinput_action(self, key, form_input):
        print ("NoInput provided after *** " + 
               self.dialog[key].audio_file_name + ".mp3 *** \t" + 
               " in form #" + key)
                  
        if not self.dialog[key].noinput_goto == key: 
            return self.dialog[key].noinput_goto, '-'
            
        else:
            if self.noinput_ctr < self.dialog[key].noinput_limit:
                        
                if not self.dialog[key].noinput_prompt == '':
                    print ("Playing NoInput Prompt: " +
                           self.dialog[key].noinput_prompt)
                    play_audio(self.speaker, self.audiopath + "/" + 
                               self.dialog[key].noinput_prompt + ".mp3")
                self.noinput_ctr += 1
                return key, form_input

            else:
                print ("NoInput Limit of " + str(self.dialog[key].noinput_limit) 
                       + " times EXCEEDED !!!")
                return '998', form_input
            


if __name__ == '__main__':
       
    y = IvrDialog("../docs/wodaabe_bcp_skeleton.csv")
    number = raw_input("Enter mobile number - ")
    y.start(number)
    
