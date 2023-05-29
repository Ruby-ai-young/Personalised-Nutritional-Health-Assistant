# This files contains custom actions which can be used to run custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

# Importing packages
from gc import collect
from typing import Text, List, Any, Dict
from rasa_sdk.events import UserUtteranceReverted
from rasa_sdk import Tracker, FormValidationAction, Action
from rasa_sdk.events import EventType,SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
import os
import requests

# Open AI:
path = os.getcwd()
url =  "https://api.openai.com/v1/completions"
# OpenAI API Key
key = "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"
# Authorizing the connection
headers = {"Authorization": f"Bearer {key}"}

class ActionOpenAPIClass(Action):
    # The name of the custom action
    def name(self):
        return "action_call_openai"

    def run(self, dispatcher, tracker, domain):
        # Holding the user's last message
        context = tracker.latest_message['text']
        
        if context:
            # The GPT-3 model chosen
            model = 'text-davinci-003'
            # The prompt passed into the chatbot is the user's last message
            prompt = "As an AI specialising in coeliac disease, " + context
            # The data going into the OpenAI API
            data = {'model':model, 'prompt': prompt, 'temperature':0.4, 'max_tokens':256, 'stop':[" Human:", " AI:"]}

            # Getting the chatbot's response
            try:
                response=requests.post(url, headers=headers, json=data)
                response.raise_for_status()
            except requests.exceptions.RequestException as err:
                dispatcher.utter_message(f'Error: {err}')
                return []

            try:
                msg=response.json()['choices'][0]['text']
            except (KeyError, IndexError) as err:
                dispatcher.utter_message(f'Error: Invalid response structure, missing key: {err}')
                return []
        else:
            # If nothing was found, it will ask the user to retry
            dispatcher.utter_message('Kindly retry asking a question.')
            return []

        # Displaying a Disclaimer before listing products
        display_lines = "------------------------"
        disclaimer_1 = "Disclaimer: Kindly note that this chatbot may produce inaccurate information about people, places, or facts."
        disclaimer_2 = "Thus, please exercise caution whilst using this information and seek out professional help regarding medical advice."
        display_lines_2 = "------------------------"
        
        dispatcher.utter_message(display_lines)
        dispatcher.utter_message(disclaimer_1)
        dispatcher.utter_message(disclaimer_2)
        dispatcher.utter_message(display_lines_2)

        # Uttering the chatbot's text
        dispatcher.utter_message(text=str(msg))        
        return []

food_facts_url = "https://world.openfoodfacts.org/cgi/search.pl"
params = {
    "json": 1,
    "tagtype_0": "allergens",
    "tag_contains_0": "does_not_contain",
    "tag_0": "gluten",
    "fields": "product_name,brands,countries,allergens,nutrition_grade_fr,_id",
    "sort_by": "popularity"
}

# Food Facts:
class ActionFoodFactsClass(Action):
    def name(self) -> Text: 
        return "action_call_food_facts"

    def run(self, dispatcher, tracker, domain):
            product_name = tracker.latest_message['text']
            
            params["search_terms"] = product_name

            response = requests.get(food_facts_url, params=params)
            data = response.json()

            if "products" in data:
                products = data["products"]

                # If a product is found
                if len(products) > 0:
                    # Storing unique products
                    unique_products = set()

                    # Processing the retrieved products
                    # Getting the product name, brand/s, nutrition grade and allergens
                    for product in products:
                        product_name = product.get("product_name", "N/A")
                        brand = product.get("brands", "N/A")
                        allergens = product.get("allergens", "N/A")
                        nutrition_grade = product.get("nutrition_grade_fr", "N/A")
                        barcode = product.get("_id", "N/A")

                        # Generating a unique identifier for each product based on the product name and brand
                        product_identifier = f"{product_name}"
                        unique_products.add(product_identifier)

                    # If the product is unique
                    if unique_products:
                        # Displaying a Disclaimer before listing products
                        display_lines = "------------------------"
                        disclaimer_1 = "Disclaimer: The information provided for the following products may not be complete."
                        disclaimer_2 = "Thus, please exercise caution whilst using this information."
                        disclaimer_3 = "It is important to note that the presence of allergens is subject to change, and there may be a risk of cross-contamination."
                        disclaimer_4 = "Always refer to the product packaging and manufacturer for the most accurate and up-to-date allergen information."
                        display_lines_2 = "------------------------"

                        dispatcher.utter_message(display_lines)
                        dispatcher.utter_message(disclaimer_1)
                        dispatcher.utter_message(disclaimer_2)
                        dispatcher.utter_message(disclaimer_3)
                        dispatcher.utter_message(disclaimer_4)
                        dispatcher.utter_message(display_lines_2)

                        # Displaying the URL
                        url_food_facts_barcode_entered = "To view this product kindly go to the following website: "
                        url_food_facts_barcode = (f"https://world.openfoodfacts.org/product/{barcode}/")
                        dispatcher.utter_message(url_food_facts_barcode_entered)
                        dispatcher.utter_message(url_food_facts_barcode)

                        # Sending the retrieved information back to the user
                        dispatcher.utter_template("utter_product",tracker,product_name=product_name, brand=brand, allergens=allergens, nutrition_grade=nutrition_grade, barcode=barcode)
                else:
                    # If not found
                    dispatcher.utter_message(text="Product not found.")
            else:
                # For testing
                dispatcher.utter_message(text="An error occurred while retrieving product information.")
                # Printing the API response for further investigation
                dispatcher.utter_message(data)

            return []

class ActionBarcodeLookupClass(Action):
    def name(self) -> Text:
        return "action_barcode_lookup_food_facts"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Get the barcode from user input
        barcode = tracker.latest_message.get('text')

        # Call OpenFoodFacts API to retrieve product information
        response = requests.get(f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json")

        if response.status_code == 200:
            product_data = response.json()

            if "product" in product_data:
                product_name = product_data['product']['product_name']
                brand = product_data['product']['brands']
                allergens = product_data['product']['allergens']
                nutrition_grade = product_data['product']['nutrition_grade_fr']

                # Displaying a Disclaimer before listing products
                display_lines = "------------------------"
                disclaimer_1 = "Disclaimer: The information provided for the following products may not be complete."
                disclaimer_2 = "Thus, please exercise caution whilst using this information."
                disclaimer_3 = "It is important to note that the presence of allergens is subject to change, and there may be a risk of cross-contamination."
                disclaimer_4 = "Always refer to the product packaging and manufacturer for the most accurate and up-to-date allergen information."
                display_lines_2 = "------------------------"
                
                dispatcher.utter_message(display_lines)
                dispatcher.utter_message(disclaimer_1)
                dispatcher.utter_message(disclaimer_2)
                dispatcher.utter_message(disclaimer_3)
                dispatcher.utter_message(disclaimer_4)
                dispatcher.utter_message(display_lines_2)

                # Displaying the URL
                url_food_facts_barcode_entered = "To view this product kindly go to the following website: "
                url_food_facts_barcode = (f"https://world.openfoodfacts.org/product/{barcode}/")
                dispatcher.utter_message(url_food_facts_barcode_entered)
                dispatcher.utter_message(url_food_facts_barcode)

                # Sending the retrieved information back to the user
                dispatcher.utter_template("utter_product",tracker,product_name=product_name, brand=brand, allergens=allergens, nutrition_grade=nutrition_grade, barcode=barcode)
            else:
                # If not found
                dispatcher.utter_message(text="Product not found.")
        else:
            dispatcher.utter_message(text="An error occurred while retrieving product information.")

        return []

# Action to Save the Conversation
class ActionSaveConversation(Action):
    def name(self) -> Text:
        return "action_save_conversation"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        events = tracker.events
        user_bot_conversation = []
        
        for event in events:
            if event.get('event') == 'user':
                user_bot_conversation.append(f'user: {event["text"]}')
            elif event.get('event') == 'bot':
                user_bot_conversation.append(f'bot: {event["text"]}')

        with open('conversation.txt', 'w') as f:
            for line in user_bot_conversation:
                f.write(f"{line}\n")

        dispatcher.utter_message(text="This chat including your feedback has been saved.")

        return []
