import webapp2
import json
import urllib
import urllib2

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

# ============================================================

# VK secret data | https://vk.com/dev/callback_api
VKServerConfirmationToken = "f5d9d45e"
VKServerSecretToken = "aaQ13axAPQEcczQa"
VKGroupToken = "VK_GROUP_TOKEN"

# Facebook secret data | https://developers.facebook.com/docs/messenger-platform/getting-started
FBServerConfirmationToken = "f5d9d45e"
FBGroupToken = "FACEBOOK_PAGE_TOKEN"

# Telegram secret data | https://core.telegram.org/bots/api
TelegramToken = "TELEGRAM_BOT_TOKEN"

# System data
helpText = "Help ..."
aboutText = "About info ..."

# ============================================================

# Main function
def MessagesProcessing(text):
    if text.lower() in ["help", "/help", "помощь"]: # Help
        return helpText
    elif text.lower() in ["about", "/about", "информация"]: # About
        return aboutText
    elif text == "no_text_error" or text == "": # No text
        return "Please send text only"
    else:
        return text

# ============================================================

# Function for sending requests to VK
def VkRequest(method, arguments):
    # Add standart arguments
    arguments["access_token"] = VKGroupToken
    arguments["v"] = 5.65

    # Load request
    return urllib2.urlopen("https://api.vk.com/method/" + method, urllib.urlencode(arguments)).read()   

# Function for sending messages on Facebook
def FBSendMessage(text, userId):
    # Generate json from arguments
    arguments = {}

    recipient = {}
    recipient["id"] = userId
    arguments["recipient"] = recipient

    message = {}
    message["text"] = text
    arguments["message"] = message

    # Create message sending request
    request = urllib2.Request("https://graph.facebook.com/v2.6/me/messages?access_token=" + FBGroupToken)
    request.add_header('Content-Type', 'application/json')
    request.add_data(json.dumps(arguments))

    # Send message
    return urllib2.urlopen(request).read()

# Function for sending messages on Telegram
def TelegramSendMessage(text, userId):
    return urllib2.urlopen("https://api.telegram.org/bot" + TelegramToken + "/sendMessage", urllib.urlencode({
                "chat_id": str(userId),
                 "text": text,
                "disable_web_page_preview": "True"
            })).read() 

# ============================================================

# Callback class for answering to user messages from VK
class CallbackHandler(webapp2.RequestHandler):
    def post(self):
        # Answer to request
        self.response.out.write("OK") 

        # Get json data    
        data = json.loads(self.request.body)

        # Check if message was sent from VK server
        if data["secret"] != VKServerSecretToken:
            self.redirect('/')
    
        if data["type"] == "confirmation":
            # Return verification key to confirm server
            self.response.out.write(VKServerConfirmationToken)  
        elif data["type"] == "message_new":
            # Get user id
            user_id = data["object"]["user_id"]

            # Get message text
            text = data["object"]["body"]

            # Process message text
            messageText = MessagesProcessing(text)
            
            # Answer to user      
            resp = VkRequest("messages.send", {"user_id": str(user_id), "message": messageText}) 

            # If message was not sent
            if not resp.isdigit():
                # Error
                pass

# Webhook class for answering to user messages from Facebook
class FBWebhookHandler(webapp2.RequestHandler):
    def get(self):
        # Get request arguments   
        mode = str(self.request.get('hub.mode'))
        verify_token = str(self.request.get('hub.verify_token'))
        challenge = str(self.request.get('hub.challenge'))
     
        if mode == "subscribe" and verify_token == FBServerConfirmationToken:
            # Return received key to confirm server
            self.response.out.write(challenge)
    
    def post(self):
        # Answer to request
        self.response.out.write("OK") 

        # Get json data    
        data = json.loads(self.request.body)

        # Parse data and get message text
        if data["object"] == "page":
            # Facebook can return more then one notify at time
            for entry in data["entry"]:
                # One notify can contain more then one message
                for messaging in entry["messaging"]: 
                    # Get sender id
                    userId = messaging["sender"]["id"]

                    # Get message text
                    text = ""
                    try:                        
                        text = messaging["message"]["text"]                       
                    except:
                        text = "no_text_error" 

                    # Process message text
                    messageText = MessagesProcessing(text)

                    # Answer to user
                    resp = FBSendMessage(messageText, userId) 

class MeHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write(json.dumps(json.load(urllib2.urlopen("https://api.telegram.org/bot" + TelegramToken + "/getMe"))))

class GetUpdatesHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write(json.dumps(json.load(urllib2.urlopen("https://api.telegram.org/bot" + TelegramToken + "/getUpdates"))))

class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        url = self.request.get("url")
        if url:
            self.response.write(json.dumps(json.load(urllib2.urlopen("https://api.telegram.org/bot" + TelegramToken + "/setWebhook", urllib.urlencode({"url": url})))))

# Webhook class for answering to user messages from Telegram
class WebhookHandler(webapp2.RequestHandler):
    def post(self):
        # Get json data 
        body = json.loads(self.request.body)

        # Getting message
        try:
            message = body["message"]
        except:
            message = body["edited_message"]

        text = message.get("text")
        chatId = message["chat"]["id"]

        if not text:
            text = "no_text_error" 

        # Process message text
        messageText = MessagesProcessing(text)

        # Answer to chat
        resp = TelegramSendMessage(messageText, chatId)
                      
class AnotherHandler(webapp2.RequestHandler):
    def get(self):
        self.redirect('/')

# ============================================================

app = webapp2.WSGIApplication(routes=[  
    # Messages handlers
    ("/callback", CallbackHandler), # VK
    ("/facebookwebhook", FBWebhookHandler), # Facebook
    ("/webhook", WebhookHandler), # Telegram

    # Additional handlers
    ("/me", MeHandler), # Telegram
    ("/updates", GetUpdatesHandler), # Telegram
    ("/set_webhook", SetWebhookHandler), # Telegram  

    (r"/.*", AnotherHandler) ], debug=True)
