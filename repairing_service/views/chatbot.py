from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json
import uuid
from django.conf import settings
from django.utils import timezone

# Import the Rasa API - fix the import to ensure it works
import sys
import os
# Add the project root to the path to ensure chatbot module is found
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from chatbot.api import RasaAPI

# Initialize Rasa API
rasa_api = RasaAPI()

# Create a session store for conversation IDs
# In production, use a more permanent storage like Redis or database
conversation_sessions = {}

@csrf_exempt
@require_http_methods(["POST"])
def chatbot_webhook(request):
    """
    Endpoint for chatbot interactions.
    
    Request format:
    {
        "message": "User message here",
        "session_id": "optional-existing-session-id"
    }
    
    Response format:
    {
        "responses": [
            {
                "text": "Bot response text",
                "buttons": [] // Optional buttons if any
            }
        ],
        "session_id": "conversation-session-id"
    }
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        session_id = data.get('session_id', '')
        
        # Create or retrieve session ID
        if not session_id:
            session_id = str(uuid.uuid4())
            conversation_sessions[session_id] = {
                'user_id': request.user.id if request.user.is_authenticated else None,
                'created_at': str(timezone.now())
            }
        
        # Send message to Rasa
        responses = rasa_api.send_message(message, session_id)
        
        return JsonResponse({
            'responses': responses,
            'session_id': session_id
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Failed to process the chatbot request.'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def analyze_intent(request):
    """
    Endpoint to analyze the intent of a message without generating a response.
    
    Request format:
    {
        "message": "User message here"
    }
    
    Response format:
    {
        "intent": {
            "name": "intent_name",
            "confidence": 0.95
        },
        "entities": [
            {
                "entity": "entity_name",
                "value": "entity_value"
            }
        ]
    }
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        
        # Get intent from Rasa
        intent_data = rasa_api.get_intent(message)
        
        return JsonResponse(intent_data)
    
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Failed to analyze intent.'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_chat_history(request):
    """
    Get the user's chat history (for authenticated users).
    This is a placeholder - actual implementation would need a proper database storage.
    """
    # This is just a placeholder. In a real implementation, you would retrieve
    # chat history from a database or other storage.
    return JsonResponse({
        'message': 'Chat history feature not implemented yet.',
        'history': []
    }) 