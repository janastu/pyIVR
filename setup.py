import os            ### for playing the wav files
import signal        ### for the alarm to implement tiemout
import time            ### for delay


''' Global IVR Variables '''
audio_file = []
level = []
valid_input = []
action = []
timeout = []    
timeout_action = []

''' Getting the path for audio files mainly '''
projectpath =  os.path.split(os.path.realpath(__file__))[0]
audiopath = projectpath + "/../audios/"

''' Files used '''
ivr_flow_file = projectpath + '/../docs/' + 'wodaabe_bcp_skeleton.csv'
calls_progress_record = projectpath + '/../bcp_output/'+ 'call_log.csv'
no_clan_list = projectpath + '/../bcp_output/' + 'clan_not_listed.txt'


''' Alarm handling function = If timeout occurs, what to do '''
def timeout_handler(signum, frame):
    raise Exception('Timeout')
    
''' 
    Prepare the flow sequence of IVR using a CSV file "ivr_flow_file"
    This function parses through CSV file and creates a linked list of sorts
    for the call to navigate and execute the desire flow sequence. 
'''
def prepare_ivr_flow():

    global audio_file
    global level
    global valid_input
    global action
    global timeout
    global timeout_action
    
    f = open(ivr_flow_file,'r')
    flow = f.readlines()
    f.close()

    ### Remove unnecessary lines
    flow = flow[:7]

    ### Remove newline, carriage return, and double quotation mark that 
    ###  spreadsheet software might introduce
    flow = [w.replace('\n', '').replace('"','').replace('\r','') for w in flow]

    level = flow[0].split(',')[1:]
    #level = [int(i) if i else 0 for i in level]
    print level    

    audio_file = flow[1].split(',')[1:]
    print audio_file

    valid_input = flow[2].split(',')[1:]
    print valid_input

    action = flow[3].split(',')[1:]
    print action

    timeout = flow[4].split(',')[1:]
    timeout = [int(i) if i else 0 for i in timeout]
    print timeout

    timeout_action = flow[5].split(',')[1:]
    timeout_action = [int(i) if i else '' for i in timeout_action]
    print timeout_action

    # TODO prepare the log file to save call progress
    

''' 
    Get the call progress record for a given phone number 
    Each line in the record corresponds to a phone number
'''
def fetch_record(number):

    with open(calls_progress_record,'r') as f:
        log = f.readlines() 
    
    ### First two lines are headings, so ignore those and go through other lines
    for line in log[2:]:
        record = line.split(',')

        ### If record for the number exists, then shift the record to the last
        ###  for ease of updation
        if number == record[0]:
            log.remove(line)
            log.append(line)
            log = ''.join(log)
            with open(calls_progress_record,'w') as f:
                f.truncate(0)
                f.write(log)
                f.flush()
            record = [w.replace('\n', '') for w in record]
            return record
    
    ### if no record found, send an empty record that the number can later use
    return ['']*(len(level)+1)

'''
    Create a new record for the first time. 
    Reads the entire file, and appends the new record and writes to the file 
     again.
'''
def create_record(record):
    line = ','.join(record) + '\n'
    with open(calls_progress_record,'r') as f:
        log = f.readlines()
        log.append(line)
        log = ''.join(log)
    with open(calls_progress_record,'w') as f:
        f.truncate(0)
        f.write(log)
        f.flush()
        #print log

'''
    Update record - pops the last record in file, updates it and stores it back
    When a record is fetched using fetch_record, it is moved to the last so that
     updation here becomes easy. We need not waste time searching through 
     the file for the number again and again.
'''
def update_record(record):
    line = ','.join(record) + '\n'
    with open(calls_progress_record,'r') as f:
        log = f.readlines()
        log[-1] = line
        log = ''.join(log)
    with open(calls_progress_record,'w') as f:
        f.truncate(0)
        f.write(log)
        f.flush()

'''
    To get the valid input of a level.
    If a level has many valid inputs, they will be separated by semicolon ;
'''
def fetch_valid_input(levl):
    if len(valid_input[levl]) > 1:
        return valid_input[levl].split(';')
    else:
        return valid_input[levl]

'''
    To get the next action of a level.
    If a level has multiple next actions, they will be separated by semicolon ;
'''
def fetch_action(levl):
    if len(action[levl]) > 1:
        return action[levl].split(';')
    else:
        return action[levl]

'''
    Get DTMF value entered by user from GSM modem
     Within the timeout limit for that particular level
     Also monitor if call is hung or disconnected while getting the DTMF
     Check whether DTMF entered is valid or not
'''
def fetch_dtmf(levl):

    ### if a level is not expecting an input then return '-'
    if not valid_input[levl]:
        return '-'            

    ### try to get the DTMF within the timeout
    try:
        dtmf = ''            
        signal.alarm(timeout[levl])                
        while not dtmf: dtmf = mygsm.read_dtmf() 
        #raw_input('Enter choice: ')

    ### Error can be Timeout or Call Disconnect
    except Exception as error:
        print 'Error is ', error
        if 'Timeout' in error:    dtmf = 't' 
        else: dtmf = 'exit'
        signal.alarm(0)
        return dtmf

    ### Reset alarm/timeout
    signal.alarm(0)

    print 'dtmf @ fetch is', dtmf
    
    ### Check whether the entered DTMF is listed in valid inputs for that level
    try:
        print 'Level is ', levl
        print 'Valid inputs are: ', fetch_valid_input(levl)
        print 'Validity: ', fetch_valid_input(levl).index(str(dtmf))
    except: dtmf = 'invalid'
    return dtmf

'''
    This is where the IVR flow is executed
'''
def execute_ivr(record, start_level):
    timeout_cnt = 0
    invalid_cnt = 0
    zero_cnt = 0
    now_level = 2
    
    ### Treat user as new user if training not completed the first time
    if start_level < 9:    start_level = 2
     #elif start_level == 6:     start_level = 7
    
    ### To go to next level after intentional break, when call is resumed
    elif start_level == 83 or start_level == 84: start_level = 85

    ### If call is disconnected when going through clan list, then resume @
    ###  Level 6.4 if user had selected a clan
    ###  Whatever was the last clan played if clan was not selected yet
    #elif (start_level in range(15,20)) or (start_level in range(21,26)):
    #    from_level = start_level - 1
    #    if record[start_level-1] == '1': start_level = 27

    ### Start the flow
    while True:
        
        ### Terminate the call when level 40 is reached
        if now_level == 0: 
            print mygsm.disconnect_call()
            return
        
        ### Play the audio file of the current level 
        print "Level = ", now_level
        print "Valid Inputs = ", valid_input[now_level]
        print "Next Actions = ", action[now_level]
        print "playing ",audio_file[now_level]
        os.system("cvlc --no-loop --play-and-exit "+audiopath+audio_file[now_level]+".mp3 ")        

        ### Turn on DTMF to read the input and then turn it off to avoid stray
        ###  button press
        if mygsm.dtmf_detection('ON'):
            dtmf = fetch_dtmf(now_level)
            mygsm.dtmf_detection('OFF')
        else: dtmf = 'exit'
        print 'DTMF is ', dtmf

        ### Prepare next action based on DTMF value ###

        ### If call terminated, then exit IVR
        if dtmf == 'exit': return

        ### If timeout, usually repeat the level with a message and keep a count
        ###  If there is a different level to execute on timeout, then execute it
        elif dtmf == 't': 
            if not timeout_action[now_level] == now_level: 
                next_level = timeout_action[now_level]
                print 'Next on Timeout: ', next_level
                print 'Now where Timeout: ', now_level
                now_level = next_level
                continue
            else:
                if timeout_cnt < 1:
                    #os.system("aplay "+audiopath+"provideinput.wav")
                    timeout_cnt += 1
                    continue
                else:
                    now_level = 1
                    continue

        ### If invalid input, then play message and keep a count. 
        ### Exit when limit exceeds
        elif dtmf == 'invalid':
            if invalid_cnt < 1: 
                #os.system("cvlc --no-loop --play-and-exit "+audiopath+"invalidinput.mp3")
                invalid_cnt += 1
                continue
            else: 
                now_level = 1
                continue

        ### If DTMF is a valid input, get the corresponding next action
        else:
            timeout_cnt = 0
            invalid_cnt = 0
            
            ### If the level didn't expect any input            
            if dtmf == '-': i = 0
            
            ### Get the location of DTMF in the valid input list
            else: i = fetch_valid_input(now_level).index(dtmf)
            print 'i is ', i
            
            ### Get the corresponding action for that valid input
            #print 'Valid actions are: ', action[now_level]
            next_level = fetch_action(now_level)[i]
            print 'Next level is ', next_level

            ### Check if the next level has some conditions to execute
            try: next_level = int(next_level)
            except: 
                if next_level == 'A':
                    if start_level == 2: next_level = 3
                    else: next_level = start_level
                #elif next_level == 'B':
                #    next_level = start_level
                #elif next_level == 'C':
                #    if record[14] == '1': next_level = 15
                #    else: next_level = 21 
                #elif next_level == 'D':
                #    if start_level: next_level = start_level
                #    else: next_level = 7
                #elif next_level == 'E':
                #    next_level = from_level

        ### Update records with DTMF and not save DTMF if zero after training            
        if not dtmf == '-' and not (dtmf == '0' and now_level >= 7):
            record[now_level+1] = dtmf
            update_record(record)    
            
            ### Keep a track of from level for the sake of clan lists
            if now_level >= 7: from_level = now_level
            
            ### Note down the mobile number in a different file whose clan was not
            ###  mentioned in the list
            if now_level == 26 and dtmf == '3':
                with open(no_clan_list,'a+') as f:
                    f.write(phone_number)
        
        ### iterate to next level
        if next_level < now_level and not now_level==26: zero_cnt += 1
        elif next_level == now_level and now_level == 7: zero_cnt += 1
        else: zero_cnt = 0
        if zero_cnt > 1: now_level = 6
        else: now_level = next_level


if __name__ == '__main__':

    while not mygsm.modem_connect(): time.sleep(3)
    print 'Echo OFF: ', mygsm.command_echo('OFF')
    chk = mygsm.call_ready()
    print 'Call Ready: ', chk
    if not chk: 
        mygsm.phone_functionality('RESTART')
    print 'Alert on change in call status: ', mygsm.current_calls_report('ON')
    print 'Caller ID disabled during incoming call: ', mygsm.clip('OFF')
    print 'Call Waiting enabled: ', mygsm.call_wait_control('ON')
    print 'Outgoing call status indication: ', mygsm.outgoing_call_status('OFF')


    
    ### Get the flow sequence of the ivr
    prepare_ivr_flow()

    ### Alarm initialization for enabling timeout feature
    signal.signal(signal.SIGALRM, timeout_handler)

    while True:
        
        ### Keep reading the serial port to check for incoming call
        try:
            mygsm.readline()
        except Exception as error: 
            print error 
            pass
        
        ### if there was an incoming call logged
        if mygsm.call_state == '6':
            
            phone_number = pyGSM.get_number()     
            if not phone_number: continue
            print 'Going to call: ', phone_number
            record = fetch_record(phone_number)
            
            ### if a record for the phone number already exists
            if record[0]:
                ### Get the last unsaved level                
                from_level = len(record) - 1
                while not record[from_level]: from_level -= 1
                print 'User record exists for ', phone_number

                ### if the record has completed all levels then don't call back
                if from_level == 114: 
                    print phone_number, ' has already completed the survey'                    
                    pyGSM.update_call_list(phone_number)
                    continue

            ### create new record for new caller
            else:
                from_level = 2
                record[0] = phone_number
                record[1] = '-'
                record[2] = '-'
                create_record(record)
                print 'Creating new record for ', phone_number
        
            ### call the number
            status = mygsm.dial_number(phone_number)
            print 'Call dial status... ', status
            
            ### if call gets picked up, execute ivr and remove number from list
            if 'Busy' in status: continue
            elif 'Established' in status:
                pyGSM.update_call_list(phone_number)
                execute_ivr(record,from_level)
            
            ### if the call is not picked up, still remove from the list 
            elif 'Not Answered' in status:
                pyGSM.update_call_list(phone_number)
            else:
                print 'Hanging Up: ', mygsm.disconnect_call()
                
#def zero_back(zero_count):
#    pid = commands.getoutput('ps -a | grep aplay')
#    while pid:
#        if zero_count < 1:
#            dtmf = raw_input()
#            if dtmf == '0':
#                os.system("killall aplay")                    
#                return True            
#        pid = commands.getoutput('ps -a | grep aplay')    
#    return False
    
