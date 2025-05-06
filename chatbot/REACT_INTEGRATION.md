# Integrating the Bike Repair Chatbot with React

This guide explains how to integrate the Rasa-powered bike repair chatbot with your React frontend. The integration is already set up in the codebase, but this document provides additional context and customization options.

## Overview

The chatbot integration consists of three main components:

1. **Backend API** - Django endpoints that communicate with the Rasa server
2. **React Component** - A ChatBot component that provides the user interface
3. **Rasa Server** - The NLU and dialogue management engine (runs separately)

## Prerequisites

- Working Django backend with the chatbot API endpoints
- Working Rasa server with trained model
- React frontend with the ChatBot component

## Communication Flow

1. User types a message in the React ChatBot component
2. React sends an API request to the Django backend
3. Django forwards the request to the Rasa server
4. Rasa processes the message and generates a response
5. The response is sent back through Django to the React component
6. React displays the response to the user

## Running the Chatbot

1. **Start the Rasa server**:
   ```bash
   cd repairmybike/chatbot
   rasa run --enable-api --cors "*" --port 5005
   ```

2. **Start the Django server**:
   ```bash
   cd repairmybike
   python manage.py runserver
   ```

3. **Start the React development server**:
   ```bash
   cd bike_mechanic
   npm start
   ```

## Customizing the ChatBot Component

The ChatBot component (`bike_mechanic/src/components/ChatBot.tsx`) is designed to be customizable. You can modify the following props:

```tsx
<ChatBot
  initialMessage="Custom initial greeting message"
  position="bottom-right" // or "bottom-left"
  theme={{
    primaryColor: '#ff6b6b',   // Main color for header and buttons
    secondaryColor: '#f0f0f0', // Secondary UI elements
    fontColor: '#333',         // Text color
    backgroundColor: '#fff',   // Background color
  }}
/>
```

### Styling

The component uses Tailwind CSS classes for styling. You can customize the appearance by modifying the CSS classes in the component.

### Chat History

Chat history is stored in the user's localStorage by default, allowing conversations to persist between page reloads. For a more robust solution, you can implement server-side storage of chat history for authenticated users.

## Advanced Customization

### Adding Quick Reply Buttons

The component supports quick reply buttons that Rasa can send. In your Rasa domain file, you can define button responses like this:

```yaml
responses:
  utter_ask_service_type:
    - text: "What type of service are you interested in?"
      buttons:
      - title: "Basic Tune-up"
        payload: "/service_inquiry{\"service_type\": \"basic tune-up\"}"
      - title: "Full Overhaul"
        payload: "/service_inquiry{\"service_type\": \"full overhaul\"}"
```

### Adding Attachments

To support images or other attachments in responses, modify the ChatMessage interface in the React component and update the message rendering logic.

## Troubleshooting

### CORS Issues

If you encounter CORS errors:

1. Ensure Rasa is running with `--cors "*"` flag
2. Check that Django's CORS settings allow requests from your frontend
3. Verify API endpoint URLs in the React component

### Connection Errors

If the chatbot fails to connect to the backend:

1. Check that all servers are running
2. Verify endpoint URLs in the React component
3. Check browser console for error messages
4. Ensure the Django chatbot API is properly configured

### Response Issues

If responses are not as expected:

1. Test the Rasa model directly using `rasa shell` to verify it works correctly
2. Check that entities and intents are being correctly extracted
3. Verify that the Django API is correctly forwarding messages to Rasa
4. Inspect network requests in browser developer tools

## Best Practices

- **Progressive Enhancement**: Make sure your site works without the chatbot in case of connectivity issues
- **Error Handling**: Implement robust error handling in the React component
- **Performance**: Consider lazy loading the chatbot component to improve initial page load times
- **Accessibility**: Ensure the chatbot interface is keyboard navigable and screen reader friendly
- **Mobile Optimization**: Test the chatbot interface on various screen sizes

## Future Enhancements

Consider these potential enhancements:

- **User Authentication**: Link chatbot sessions to user accounts
- **Multi-language Support**: Add language detection and translation
- **Voice Interface**: Add speech recognition and text-to-speech
- **Analytics**: Track common queries and chatbot performance
- **Proactive Messages**: Trigger chatbot messages based on user behavior
- **Chat Transfer**: Allow handoff to human agents for complex issues

## Resources

- [Rasa Documentation](https://rasa.com/docs/)
- [React Documentation](https://reactjs.org/docs/getting-started.html)
- [Django REST Framework](https://www.django-rest-framework.org/) 