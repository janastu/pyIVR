class Form(object):
    def __init__(self):
        self.audio_file_name = ""
        self.valid_input = []
        self.goto_next = []

        self.timeout = 0
        self.noinput_prompt = ""
        self.noinput_goto = ""
        self.noinput_limit = 0

        self.nomatch_prompt = ""
        self.nomatch_goto = ""
        self.nomatch_limit = 0
