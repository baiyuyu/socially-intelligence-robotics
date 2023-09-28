from social_interaction_cloud.action import ActionRunner
from social_interaction_cloud.basic_connector import BasicSICConnector
# import nltk
# from nltk.sentiment.vader import SentimentIntensityAnalyzer
import json
import sys

server_ip = '127.0.0.1'
dialogflow_key_file = 'nao-14-fknn-6c9def0d6d58.json'
dialogflow_agent_id='nao-14-fknn'
sic = BasicSICConnector(server_ip, 'en-US', dialogflow_key_file, dialogflow_agent_id)
action_runner = ActionRunner(sic)
action_runner.load_waiting_action('set_language', 'en-US')
action_runner.load_waiting_action('wake_up')
action_runner.run_loaded_actions()
attempt_manager = None
action_runner.run_waiting_action('say', 'nao activated')
action_runner.run_waiting_action("do_gesture","test-f34dfd/behavior_1")
action_runner.run_waiting_action('rest')
sic.stop()