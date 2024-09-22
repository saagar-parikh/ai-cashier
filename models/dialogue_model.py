class DialogueModel:
    def __init__(self):
        # Initialize with predefined responses or use a trained/fine-tuned model
        self.responses = {
            "size": "Large or small?",
            "to-go": "To-go or for here?",
            "milk": "Non-dairy options available: oat, almond, soy. Which one?",
        }

    def get_response(self, user_input):
        # Simplified matching (could use NLP or GPT for more advanced handling)
        user_input = user_input.lower()
        if "size" in user_input:
            return self.responses["size"]
        elif "to-go" in user_input:
            return self.responses["to-go"]
        elif "milk" in user_input:
            return self.responses["milk"]
        else:
            return "I'm sorry, could you repeat that?"
