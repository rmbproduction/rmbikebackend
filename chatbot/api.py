import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RasaAPI:
    """
    A class to handle communication with the Rasa server.
    """
    
    def __init__(self):
        # Default to localhost if not specified in environment variables
        self.rasa_url = os.getenv('RASA_URL', 'http://localhost:5005')
        self.model_name = os.getenv('RASA_MODEL', 'default')
        
    def send_message(self, message, sender_id):
        """
        Send a message to the Rasa server and get a response.
        
        Args:
            message (str): The user's message
            sender_id (str): A unique ID for the conversation
            
        Returns:
            dict: The response from Rasa
        """
        try:
            endpoint = f"{self.rasa_url}/webhooks/rest/webhook"
            data = {
                "sender": sender_id,
                "message": message
            }
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(endpoint, data=json.dumps(data), headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                return [{"text": "Sorry, I'm having trouble connecting to my brain right now. Please try again later."}]
                
        except Exception as e:
            print(f"Error communicating with Rasa: {str(e)}")
            return [{"text": "I'm sorry, but I'm unable to process your request at the moment."}]
            
    def get_intent(self, message):
        """
        Get the intent of a message using Rasa's NLU engine.
        
        Args:
            message (str): The user's message
            
        Returns:
            dict: The parsed intent information
        """
        try:
            endpoint = f"{self.rasa_url}/model/parse"
            data = {"text": message}
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(endpoint, data=json.dumps(data), headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"intent": {"name": "out_of_scope", "confidence": 1.0}}
                
        except Exception as e:
            print(f"Error getting intent from Rasa: {str(e)}")
            return {"intent": {"name": "out_of_scope", "confidence": 1.0}}

# Usage example:
# rasa_api = RasaAPI()
# response = rasa_api.send_message("Hello, I need help with my bike", "user123")
# print(response) 