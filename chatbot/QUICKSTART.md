# Bike Repair Chatbot - Quick Start Guide

This guide will help you get the bike repair chatbot up and running quickly.

## 🚀 60-Second Setup

Follow these steps to start the chatbot in development mode:

1. **Install dependencies**:
   ```bash
   cd repairmybike/chatbot
   pip install -r requirements-rasa.txt
   ```

2. **Run the setup script**:
   ```bash
   python setup_chatbot.py
   ```

3. **Start the Rasa server**:
   ```bash
   rasa run --enable-api --cors "*" --debug
   ```

4. **In a new terminal, start Django**:
   ```bash
   cd repairmybike
   python manage.py runserver
   ```

5. **In a third terminal, start the React frontend**:
   ```bash
   cd bike_mechanic
   npm start
   ```

The chatbot should now be available in your browser at http://localhost:3000

## 🔍 Key Features

- Natural language understanding for bike-specific conversations
- Dynamic responses based on bike type, components, and issues
- Appointment scheduling and management
- Maintenance tips and service recommendations
- Rich, interactive user interface

## 🛠️ Development Workflow

### Modifying the Chatbot's Responses

1. Edit `domain.yml` to change the chatbot's responses
2. Edit `data/nlu.yml` to add new training examples
3. Run `rasa train` to update the model
4. Restart the Rasa server

### Custom Actions

The chatbot uses custom actions for dynamic responses. These are defined in `actions.py`.

To modify custom actions:

1. Edit `actions.py`
2. Start the action server:
   ```bash
   rasa run actions
   ```

### Testing Changes

Test your changes using one of these methods:

1. **Rasa Shell** - Direct CLI testing:
   ```bash
   rasa shell
   ```

2. **Interactive Learning** - Improve your model iteratively:
   ```bash
   rasa interactive
   ```

3. **Web Chat** - Test through the web interface

## 📊 Conversation Testing

Here are some example conversations to test:

### Basic Service Inquiry
```
User: Hi there
Bot: [Greeting]
User: What kind of services do you offer?
Bot: [Services information]
User: How much is a tune-up?
Bot: [Price information]
```

### Bike Problem
```
User: My brakes are squeaking badly
Bot: [Problem response]
User: How long would it take to fix?
Bot: [Repair time information]
User: Can I book an appointment?
Bot: [Booking information]
```

### Advanced Inquiry
```
User: Do your mechanics have experience with carbon frames?
Bot: [Expertise information]
User: What's your warranty policy?
Bot: [Warranty information]
User: What maintenance should I do between services?
Bot: [Maintenance tips]
```

## 🔧 Troubleshooting

### Common Issues

- **"Cannot connect to Rasa server"**: Ensure Rasa is running with the `--enable-api` flag
- **CORS errors**: Make sure Rasa is running with `--cors "*"`
- **Django import errors**: Check your Python path and Django settings
- **Model loading errors**: Try rebuilding the model with `rasa train`

### Getting Help

If you encounter issues:

1. Check the Rasa server logs
2. Look at the Django server console output
3. Check the browser developer console
4. Refer to the full documentation in `README.md`

## 📚 Key Files

- `domain.yml` - Main chatbot configuration
- `data/nlu.yml` - Training examples
- `data/stories.yml` - Conversation flows
- `data/rules.yml` - Conversation rules
- `actions.py` - Custom action code
- `config.yml` - NLU and policy configuration

## 📱 Mobile Testing

To test on mobile devices:

1. Find your computer's local IP address
2. Replace `localhost` with this IP in your browser
3. Make sure your mobile device is on the same network

## 🚴‍♂️ Happy coding and happy cycling! 