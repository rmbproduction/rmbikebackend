# Bike Repair Service Chatbot

This directory contains a Rasa-based chatbot for our Bike Repair Service application. The chatbot can handle customer inquiries about services, pricing, booking appointments, and more.

## Requirements

- Python 3.8+ (recommended)
- Rasa 3.6.17
- Django integration for API access

## Installation

1. **Create a virtual environment** (optional but recommended):
   ```bash
   python -m venv rasa_env
   # On Windows
   rasa_env\Scripts\activate
   # On macOS/Linux
   source rasa_env/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements-rasa.txt
   ```

3. **Initialize Rasa** (only needed for new installations):
   ```bash
   cd chatbot
   rasa init
   ```
   Note: Skip this step if you're using our pre-configured files.

## Directory Structure

```
chatbot/
├── data/                # Training data for the chatbot
│   ├── nlu.yml          # Natural language understanding data
│   ├── rules.yml        # Rules for conversation handling
│   └── stories.yml      # Conversation flows
├── domain.yml           # Domain definition for the chatbot
├── config.yml           # NLU and policy configuration
├── api.py               # Django API integration
├── requirements-rasa.txt  # Required Python packages
└── README.md            # This file
```

## Training the Model

To train the chatbot model:

```bash
cd chatbot
rasa train
```

This will create a trained model in the `models/` directory.

## Running the Chatbot

1. **Start the Rasa server**:
   ```bash
   rasa run --enable-api --cors "*" --debug
   ```

2. **Start the action server** (if needed for custom actions):
   ```bash
   rasa run actions
   ```

3. **Testing the chatbot**:
   ```bash
   rasa shell
   ```

## Integration with Django

The chatbot is integrated with the Django backend through the `api.py` file, which provides:

- Message handling
- Intent detection
- Session management

The frontend React application communicates with the chatbot through Django API endpoints:

- `/api/repairing-service/chatbot/message/` - Send/receive chat messages
- `/api/repairing-service/chatbot/intent/` - Analyze intent of a message
- `/api/repairing-service/chatbot/history/` - Retrieve chat history (for authenticated users)

## Environment Variables

The chatbot API uses the following environment variables, which can be set in a `.env` file:

```
RASA_URL=http://localhost:5005
RASA_MODEL=default
```

## Customizing the Chatbot

To customize the chatbot:

1. **Modify intents and responses** in `domain.yml`
2. **Add training examples** in `data/nlu.yml`
3. **Define conversation flows** in `data/stories.yml`
4. **Set strict rules** in `data/rules.yml`
5. **Retrain the model** using `rasa train`

## Troubleshooting

- If the chatbot server fails to start, check port conflicts (default port is 5005)
- For Django integration issues, check console logs for API errors
- Make sure CORS settings are properly configured for cross-origin requests 