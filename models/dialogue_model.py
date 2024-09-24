from openai import OpenAI
import re
import time
from pydantic import BaseModel
from langchain.agents import Tool, AgentExecutor, ConversationalChatAgent
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain.prompts import SystemMessagePromptTemplate
from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv()


SYS_PROMPT = """
You are a friendly AI cashier at a café. Your job is to take orders from customers.
Only provide information from the menu when asked. Use the MenuPriceAllergenBasic
tool for questions about prices and allergens. Only use the MenuDescription
tool when customers specifically ask for item descriptions or more details. 
Examples:
- user input: 'How much is the Latte?' Choose tool: MenuPriceAllergenBasic.
- user input: 'What's in the Mocha?' Choose tool: MenuDescription.
- user input: 'Can I get a large size?' Choose tool: MenuPriceAllergenBasic.
- user input: 'Can I get a Ceaser Salad?' Choose tool: MenuPriceAllergenBasic.
- user input: 'How long will my Cappuccino take?' Choose tool: MenuPriceAllergenBasic.
You should: 
- Engage in a human-like conversation, simulating the experience of ordering at a café. 
- Respond with short, concise sentences that mimic how a human cashier would communicate. 
- Be prepared for common questions like 'How much time will my drink take?' and 'Do you have non-dairy milk?' 
- Proactively ask relevant questions like 'What size?', 'For here or to-go?', and 'Cash or card?'. 
- Avoid long, verbose responses. Keep your answers friendly and straightforward.
- When asked a question about the menu, do not provide the description unless explicitly asked.
- Add humorous short responses to make the conversation more engaging.
Examples: 
- user input: 'How much is the Latte?' AI response: '$4.50'.
- user input: 'What's in the Mocha?' AI response: 'Espresso, steamed milk, chocolate syrup'.
- user input: 'Can I get a large size?' AI response: 'Sure!'.
- user input: 'Can I get a Ceaser Salad?' AI response: 'Yes, it's $8.50'.
- user input: "How long will my Cappuccino take?" AI response: "About 5 minutes."
- user input: "Can I get almond milk?" AI response: "Sure, we have that!"
- user input: "Can I make my order to-go?" AI response: "Of course, to-go it is!"
- user input: "What's the price of the Iced Coffee?" AI response: "$3.50."
- user input: "What size can I get the Latte in?" AI response: "Small, medium, or large?"
- user input: "What's in the Turkey Sandwich?" AI response: "Turkey, lettuce, tomato, mayo."
- user input: "Do you have oat milk?" AI response: "Yep, we do!"
- user input: "Can I pay with cash?" AI response: "Sure, cash works."
- user input: "Do you have gluten-free options?" AI response: "Yes, we do!"
- user input: "What's the total for a large latte and a muffin?" AI response: "That'll be $8.25."
- user_input: 'Do you have soy milk?' AI response: 'Yes, we have soy milk as a substitute.'
- user_input: 'I'm allergic to nuts. Is the almond croissant safe for me?' AI response: 'The almond croissant contains nuts.'
- user_input: 'Can you make the sandwich gluten-free?' AI response: 'We can substitute gluten-free bread for you.'
- user_input: 'Is the Caesar salad dressing dairy-free?' AI response: 'The dressing contains dairy.'
- user_input: 'Can I get extra syrup in my drink?' AI response: 'Yes, we can add extra syrup for $0.50.'
- user_input: 'Does the muffin have any eggs in it?' AI response: 'Yes, the muffin contains eggs.'
- user_input: 'Can I swap bacon for avocado in my sandwich?' AI response: 'We can do that for an additional $1.'
- user_input: 'I'm vegan. Is the soup vegan-friendly?' AI response: 'The soup isn't vegan. Let me call the manager to assist with other choices.'
- user_input: 'Does the iced tea have caffeine?' AI response: 'Yes, it has a mild amount of caffeine.'
- user_input: 'Can you make the salad without croutons?' AI response: 'Yes, we can remove the croutons for you.'"
"""
system_message = SystemMessagePromptTemplate.from_template(SYS_PROMPT)

class OrderEntry(BaseModel):
    customer_name: str
    items: str
    customizations: str
    price_per_item: float
    order_total: float


class MenuTool:
    def __init__(self, menu_df, include_description=False):
        self.menu_df = menu_df
        self.include_description = include_description

    def get_item_info(self, item_name):
        if self.menu_df.empty:
            return "No menu available."
        if item_name.lower() not in self.menu_df['item'].str.lower().values:
            if self.include_description:
                return self.menu_df.to_string(index=False)
            else:
                return self.menu_df[['item', 'price', 'allergens']].to_string(index=False)
        item = self.menu_df[self.menu_df['item'].str.lower() == item_name.lower()]
        if self.include_description:
            return item.to_string(index=False)
        else:
            return f"{item['item'].values[0]}: ${item['price'].values[0]}. Allergens: {item['allergens'].values[0]}"
        

class DialogueModel:
    def __init__(self, menu_df=pd.DataFrame()):
        """
        Initialize the DialogueModel with the menu dataframe.
        """
        self.menu_df = menu_df
        self.conversation_history = []
        self.initialize_agent()


    def initialize_agent(self):
        self.menu_tool_basic_ = MenuTool(self.menu_df, include_description=False)
        self.menu_tool_with_description_ = MenuTool(self.menu_df, include_description=True)

        # Define the menu retrieval tools
        self.menu_tool_basic = Tool(
            name="MenuPriceAllergenBasic",
            func=self.menu_tool_basic_.get_item_info,
            description="Useful for answering questions about menu prices or allergens without descriptions."
        )
        self.menu_tool_with_description = Tool(
            name="MenuDescription",
            func=self.menu_tool_with_description_.get_item_info,
            description="Useful for describing menu items."
        )

        # Initialize the conversational agent
        self.agent = ConversationalChatAgent.from_llm_and_tools(
            llm=ChatOpenAI(temperature=0.7, model_name="gpt-4o",#"gpt-3.5-turbo", 
                           openai_api_key=os.getenv("OPENAI_API_KEY")),
            tools=[self.menu_tool_basic, self.menu_tool_with_description],
            system_message=system_message.prompt.template,
            verbose=True
        )

        # Set up the conversation memory
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

        # Create the agent executor
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent,
            tools=[self.menu_tool_basic, self.menu_tool_with_description],
            memory=self.memory,
            verbose=True
        )


    def reset_conversation(self):
        self.conversation_history = []

        print("conversation reset")


    def check_order_completion(self, user_input):
        # Regex pattern for detecting variations of "for here" or "to-go"
        completion_pattern = r"(for\s?here|dine\s?in|stay\s?here|to\s?go|to-go|take\s?away|take\s?out|carry\s?out|for-here|to-go)"
        
        # Check if the user input contains any of the completion phrases
        return re.search(completion_pattern, user_input, re.IGNORECASE)

    def set_menu(self, menu_df):
        """
        Set the menu dataframe for the dialogue model.
        """
        self.menu_df = menu_df
        self.initialize_agent()

    def get_menu_info(self, query):
        """
        Retrieve menu information. This is the function used by the tool.
        """
        return f"Here's our full menu:\n{self.menu_df.to_string(index=False)}"


    def get_response(self, user_input):
        """
        Engage in a conversation with the agent using the user input.
        """
        response = self.agent_executor.invoke(user_input)
        output = str(response['output'])

        self.conversation_history.append(("User", user_input))
        self.conversation_history.append(("AI", output))
        return output

    def place_order(self):
        """
        Generate an order summary using the LLM agent.
        """
        conversation_text = "\n".join([f"{speaker}: {message}" for speaker, message in self.conversation_history])

        summary_prompt =f"""
        Based on the following conversation history, generate an order summary in the specified format:

        {conversation_text}
        The output should be of the format:
        Customer Name: [Name]
        Items: [Comma-separated list of items]
        Customizations: [Comma-separated list of customizations]
        Price per Item: [Average price per item]
        Order Total: [Total price of the order]

        Only include information that was explicitly mentioned in the conversation.
        If any information is missing, leave it blank or use 0 for numerical values.
        """
        response = self.agent_executor.invoke(summary_prompt)

        # Parse the response into an OrderEntry object
        lines = response['output'].strip().split('\n')
        order_dict = {"customer_name": "", "items": "", "customizations": "", "price_per_item": 0, "order_total": 0}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                order_dict[key.strip().lower().replace(' ', '_')] = value.strip()

        # Convert price strings to floats
        try:
            order_dict['price_per_item'] = float(order_dict.get('price_per_item', '0').replace('$', '') or 0)
            order_dict['order_total'] = float(order_dict.get('order_total', '0').replace('$', '') or 0)
        except Exception as e:
            print("Error parsing price values. Setting to 0.")
            order_dict['price_per_item'] = 0
            order_dict['order_total'] = 0

        print("Order placed")
        self.reset_conversation()

        try:
            return OrderEntry(
                customer_name=order_dict.get('customer_name', ''),
                items=order_dict.get('items', ''),
                customizations=order_dict.get('customizations', ''),
                price_per_item=order_dict['price_per_item'],
                order_total=order_dict['order_total']
            )
        except Exception as e:
            print(f"Error creating OrderEntry: {e}")
            return None

# SYS_PROMPT = (
#                 "You are an AI cashier that helps customers with menu items, prices, and order questions in a friendly and human-like way. "
#                 "Keep the conversation casual and natural, as if the customer is ordering at a café. "
#                 "Always use short, direct, human-like sentences. For example, respond with 'What size?' instead of 'What size do you want for your Oat Milk Latte?'. "
#                 "If the user asks 'How much are the Coupa Fries?', respond with '$5.50' instead of 'The Coupa Fries are $5.50'. "
#                 "Proactively ask relevant questions like 'What size?', 'For here or to-go?', or 'Anything else with your drink?'. "
#                 "Be ready to handle real-life requests like 'Do you have non-dairy milk?' or 'Can I get my order to-go?'."
#                 "Only end an order when you have the following details confirmed: order, price, customizations."
#             )
    



# class DialogueModel:
#     def __init__(self, api_key):
#         self.client = OpenAI(api_key=api_key)
#         self.menu_text = ""
#         self.conversation_history = []  # Initialize conversation history
    
#     def reset_conversation(self):
#         self.conversation_history = []

#     def set_menu_text(self, menu_text):
#         self.menu_text = menu_text

#     def check_order_completion(self, user_input):
#         # Regex pattern for detecting variations of "for here" or "to-go"
#         completion_pattern = r"(for\s?here|dine\s?in|stay\s?here|to\s?go|to-go|take\s?away|take\s?out|carry\s?out|for-here|to-go)"
        
#         # Check if the user input contains any of the completion phrases
#         if re.search(completion_pattern, user_input, re.IGNORECASE):
#             return True
#         return False
    

#     def place_order(self):
#         summary_messages = [{"role": "system", "content": "Summarize the order details from the chat history and extract into an order entry."}]
#         summary_messages.extend(self.conversation_history)

#         response = self.client.beta.chat.completions.parse(
#             model="gpt-4o-mini-2024-07-18",
#             messages=summary_messages,
#             response_format=OrderEntry
#         )
        
#         order_summary = response.choices[0].message.parsed
#         self.conversation_history = []

#         return order_summary

        

#     def get_response(self, user_input):
#         # Append the user input to conversation history
#         self.conversation_history.append({"role": "user", "content": user_input})
        
#         # Prepare the full conversation including history and system message
#         messages = [
#             {"role": "system", "content": SYS_PROMPT},
#             {"role": "user", "content": f"Here is the café menu:\n{self.menu_text}."}
#         ]

#         # Add conversation history to messages
#         messages.extend(self.conversation_history)

#         # Call the LLM API
#         response = self.client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=messages
#         )

#         # Get the assistant's response
#         assistant_response = response.choices[0].message.content.strip()

#         # Append the assistant response to conversation history
#         self.conversation_history.append({"role": "assistant", "content": assistant_response})

#         return assistant_response
