from openai import OpenAI
import re
import time
from pydantic import BaseModel

SYS_PROMPT = (
                "You are an AI cashier that helps customers with menu items, prices, and order questions in a friendly and human-like way. "
                "Keep the conversation casual and natural, as if the customer is ordering at a café. "
                "Always use short, direct, human-like sentences. For example, respond with 'What size?' instead of 'What size do you want for your Oat Milk Latte?'. "
                "If the user asks 'How much are the Coupa Fries?', respond with '$5.50' instead of 'The Coupa Fries are $5.50'. "
                "Proactively ask relevant questions like 'What size?', 'For here or to-go?', or 'Anything else with your drink?'. "
                "Be ready to handle real-life requests like 'Do you have non-dairy milk?' or 'Can I get my order to-go?'."
                "Only end an order when you have the following details confirmed: order, price, customizations."
            )

class OrderEntry(BaseModel):
    customer_name: str
    items: str
    customizations: str
    price_per_item: float
    order_total: float

class DialogueModel:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.menu_text = ""
        self.conversation_history = []  # Initialize conversation history
    
    def reset_conversation(self):
        self.conversation_history = []

    def set_menu_text(self, menu_text):
        self.menu_text = menu_text

    def check_order_completion(self, user_input):
        # Regex pattern for detecting variations of "for here" or "to-go"
        completion_pattern = r"(for\s?here|dine\s?in|stay\s?here|to\s?go|to-go|take\s?away|take\s?out|carry\s?out|for-here|to-go)"
        
        # Check if the user input contains any of the completion phrases
        if re.search(completion_pattern, user_input, re.IGNORECASE):
            return True
        return False
    

    def place_order(self):
        summary_messages = [{"role": "system", "content": "Summarize the order details from the chat history and extract into an order entry."}]
        summary_messages.extend(self.conversation_history)

        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini-2024-07-18",
            messages=summary_messages,
            response_format=OrderEntry
        )
        
        order_summary = response.choices[0].message.parsed
        self.conversation_history = []

        return order_summary

        

    def get_response(self, user_input):
        # Append the user input to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Prepare the full conversation including history and system message
        messages = [
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": f"Here is the café menu:\n{self.menu_text}."}
        ]

        # Add conversation history to messages
        messages.extend(self.conversation_history)

        # Call the LLM API
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )

        # Get the assistant's response
        assistant_response = response.choices[0].message.content.strip()

        # Append the assistant response to conversation history
        self.conversation_history.append({"role": "assistant", "content": assistant_response})

        return assistant_response
