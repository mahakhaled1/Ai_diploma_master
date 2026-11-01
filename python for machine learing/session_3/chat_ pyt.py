import random
 
# Predefined responses
responses = {
    "hello": ["Hello!", "Hi there!", "Greetings!"],
    "how are you": ["I'm doing well, thank you!", "I'm fine, how about you?"],
    "goodbye": ["Goodbye!", "See you later!", "Farewell!"],
    "default": ["I'm sorry, I didn't understand.", "Could you please rephrase that?"]
}
 
# Function to get a response based on user input
def get_response(user_input):
    for key in responses:
        if key in user_input:
            return random.choice(responses[key])
   
    return random.choice(responses["default"])
 
# Chatbot function
def chatbot():
    print("Chatbot: Hi! How can I assist you today?")
   
    while True:
        user_input = input("User: ").lower()
        response = get_response(user_input)
        print("Chatbot:", response)
       
        if user_input == "goodbye":
            break
 
# Run the chatbot
chatbot()
 
 