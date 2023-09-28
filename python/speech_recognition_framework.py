from social_interaction_cloud.action import ActionRunner
from social_interaction_cloud.basic_connector import BasicSICConnector
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import json
import time
import sys
nltk.download('vader_lexicon')

class Example:
    """Example that uses speech recognition. Prerequisites are the availability of a dialogflow_key_file,
    a dialogflow_agent_id, and a running Dialogflow service. For help meeting these Prerequisites see
    https://socialrobotics.atlassian.net/wiki/spaces/CBSR/pages/260276225/The+Social+Interaction+Cloud+Manual"""

    def __init__(self,conversation_files: list, server_ip: str, dialogflow_key_file: str, dialogflow_agent_id: str):
        self.sic = BasicSICConnector(server_ip, 'en-US', dialogflow_key_file, dialogflow_agent_id)
        self.action_runner = ActionRunner(self.sic)
        self.conversation_files = conversation_files
        self.user_model = {}
        self.variable_of_interest = None
        self.default_attempt = 3
        self.detection_text = ''
        self.dfid = None


    def run(self) -> None:
        # init
        self.sic.start()
        self.action_runner.load_waiting_action('set_language', 'en-US')
        self.action_runner.load_waiting_action('wake_up')
        self.action_runner.run_loaded_actions()
        self.attempt_manager = None

        self.action_runner.run_waiting_action('say', 'nao activated')
        
        # dialogue flow one
        # loop over different conversation_files
        for i in range(len(self.conversation_files)):
            conv_obj = load_conversation(self.conversation_files[i])
            self.action_dialogueflow(conv_obj)

        # stop
        self.action_runner.run_waiting_action('rest')
        self.sic.stop()

    def on_intent(self, detection_result: dict) -> None:
        # callback function.get detection_result from dialogue flow and store the result to user_model
        print('in dfid execution, detection result:', detection_result)
        print('var of interest', self.variable_of_interest)
        if detection_result:

            if self.dfid != 'sentiment':
                try:
                    if detection_result and len(detection_result['parameters']) > 0:

                        self.user_model[self.variable_of_interest] = detection_result['parameters'][self.variable_of_interest]
                        self.attempt_manager.success = True
                    else:
                        self.attempt_manager.attempt_num += 1
                        # get detection_text
                        self.detection_text = detection_result['text']
                except Exception as e:
                    print(F'ERROR IN  DFID: {e}')
                    self.attempt_manager.attempt_num += 1
            else:
                # sentiment
                try:
                    score = get_score(detection_result['text'])
                    self.user_model[self.variable_of_interest] = score
                    self.attempt_manager.success = True
                except Exception as e:
                    print(F'ERROR IN SENTIMENT DFID: {e}')
                    self.attempt_manager.attempt_num += 1

        else:
            # if didn't get response, try again.
            self.attempt_manager.attempt_num += 1

    def action_dialogueflow(self,conv_object) -> None:
        # start from id 1
        id_count = 1
        # go through all sentences
        while True: 
            print('SPEECH', id_count)
            # For each speech bubble in conv object, reset variable_of_interest,dfid and attempt_manager
            self.variable_of_interest = None
            self.attempt_manager = AttemptManager()
            self.dfid = None
            print(id_count)

            # Exit current conv if id < 0
            if int(id_count) < 0:
                break

            # get speech bubble
            conv_frag = conv_object[str(id_count)]
            print(conv_frag)

            # get nao speech
            speech = conv_frag.get('nao', '')

            #get expected response
            expected_answer = conv_frag.get('expected_response', None)
           # if expected respone is not none, get variable of interest, else var stays none
            if expected_answer:
                self.variable_of_interest = [i.strip('$') for i in expected_answer.split(' ') if i.startswith("$")][0]
            else:
                pass

            # get default intent
            self.dfid = conv_frag.get('dfid', '')
            _sleep = conv_frag.get('sleep_time', 1.5)
            # get id for skip, skip if no response is gotten
            default = conv_frag.get('default', '')

            # get next for conv, next is either id, or dict
            _next = conv_frag.get('next', "-1")
            _skip = conv_frag.get('skip', _next)
            # get number of attempts allowed for current speech
            attempts = int(conv_frag.get('attempt', self.default_attempt))

            # parse_nao_speech
            nao_speech = self.parse_nao_speech(speech)
            # parse_action
            nao_action = conv_frag.get('action', '')
            nao_action_after = conv_frag.get('action_after', '')

            # run
            if nao_action:
                self.do_action_sametime(nao_action)
            while not self.attempt_manager.success and self.attempt_manager.attempt_num < attempts:
                self.action_runner.run_waiting_action('say_animated', nao_speech)

                # time.sleep(_sleep)


                if self.variable_of_interest:
                    self.action_runner.run_waiting_action('speech_recognition', self.dfid, 3,
                                                      additional_callback=self.on_intent)
                else:
                    self.attempt_manager.success = True

                print('intent run', self.attempt_manager.attempt_num, self.attempt_manager.success)

            if nao_action_after:
                self.do_action(nao_action_after)
                # self.action_runner.run_waiting_action("do_gesture", nao_action_after)

            # if variable of interest not succesfully retrieved, put in default value
            if not self.attempt_manager.success and self.variable_of_interest:
                self.user_model[self.variable_of_interest]= conv_frag['default']

            # get next speech bubble id based on condition and answer
            _next = parse_next_id(_next, self.variable_of_interest, self.user_model, default = default)
    

            print(self.user_model)
            prev = id_count
            if self.attempt_manager.success:
                id_count = int(_next)
            else:
                id_count = int(_skip)
            if prev == id_count:
                id_count = -1
                print('NEXT CONV POINTS TO CURRENT CONV')

    def do_action_sametime(self, action):
        # do some action when he said something
        self.action_runner.run_action("do_gesture", action + '/behavior_1')

    def do_action(self, action):
        # do some action after the speech, input action is str or list from choregraph,
        # else part is just for change eye color
        print(action,type(action))
        if type(action) is str:
            # action is application id
            self.action_runner.run_waiting_action("do_gesture", action+'/behavior_1')
        elif type(action) is list:
            for each_action in action:
                self.action_runner.run_waiting_action("do_gesture", each_action + '/behavior_1')
                time.sleep(0.5)
        elif type(action) is dict:
            color = self.user_model.get('color', None)
            if not color:
                self.action_runner.run_waiting_action('say', "its ok, i will choose my favorite color rainbow")
                color = 'rainbow'
            # noao says "let me do a magic trick"
            self.action_runner.run_waiting_action('say',"let me do a magic trick")
            self.action_runner.run_waiting_action("do_gesture", action['application_id_1']+'/behavior_1')
            self.action_runner.run_waiting_action(action['action'], color)
            self.action_runner.run_waiting_action("do_gesture", action['application_id_2'] + '/behavior_1')

    def parse_nao_speech(self, speech):
        # parse_nao_speech_and_varible_of_interest
        if '$' in speech:
            sub_strings = speech.split('$')

            final_string = [sub_strings[0]]
            sub_strings = sub_strings[1:]
            for sub in sub_strings:
                t = sub.split(' ')
                print(self.user_model, 'in nao parse')
                t[0] = t[0].strip(r',.!?!@#$%^&*()')
                print(t[0])
                t[0] = self.user_model.get(t[0], 'CANNOT GET' + ' ' + t[0])
                final_string += t

            nao_speech = ' '.join(final_string)
        else:
            nao_speech = speech

        return nao_speech


def parse_next_id(_next, variable_of_interest, user_model, default):
    if type(_next) is dict:
        _dict = _next
        try:
            answers = list(_dict.keys())
            for answer in answers:
                if user_model[variable_of_interest] == answer:
                    _next = _dict[answer]
                    break

            # if no answer is found, _next will still be a dict, so chose default answer
            if type(_next) is dict:
                _next = _dict[default]
        except:
            _next = _dict[default]
    else:
        _next = _next
    return _next

def load_conversation(file):
    with open(file, 'r') as f:
        return json.load(f)


def get_score(text):
    sid = SentimentIntensityAnalyzer()
    score = sid.polarity_scores(text).get('compound')
    print('SENT ANALYSIS', sid.polarity_scores(text))
    if score < 0:
        return "-1"
    if score >= 0:
        return "1"
     
class AttemptManager:
    def __init__(self):
        self.success=False
        self.attempt_num = 0
        self.reset()

    def reset(self):
        self.success = False
        self.attempt_num = 0


# example = Example(['/Users/byy/Desktop/vu/sir/TA-14.git/connectors/python/conversation/happy_flow.json'],
# '127.0.0.1',
# 'nao-14-fknn-6c9def0d6d58.json',
# 'nao-14-fknn')
# example.run()

example = Example(['/Users/byy/Desktop/vu/sir/TA-14.git/connectors/python/conversation/intro_conv.json'],
'127.0.0.1',
'nao-14-fknn-6c9def0d6d58.json',
'nao-14-fknn')
example.run()



def run_nao(json_path):
    # example = Example([ '/Users/byy/Desktop/vu/sir
    example = Example([json_path],
                      '127.0.0.1',
                      'nao-14-fknn-6c9def0d6d58.json',
                      'nao-14-fknn')
    example.run()



