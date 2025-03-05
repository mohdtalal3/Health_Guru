import json
import os
import random
import requests
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()
# Access the OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")

if api_key is None:
    raise ValueError("OPENAI_API_KEY is not set. Please check your .env file.")

# Initialize the OpenAI client
client = OpenAI(api_key=api_key)

# Load prompt templates
with open("prompts_template_alex.json", "r", encoding="utf-8") as file:
    prompt_data = json.load(file)

def generate_tweet_and_image():
    # Select a random image prompt template
    image_templates = prompt_data["Image_prompts"]
    random_template = random.choice(image_templates)
    
    # Generate tweet using the tweet_text_prompt
    tweet_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": random_template["tweet_text_prompt"]}
        ],
        temperature=0.4
    )
    
    # Generate image using the image_prompt
    image_response = client.images.generate(
        model="dall-e-3",
        prompt=random_template["image_prompt"],
        quality="standard",
        n=1,
        size="1024x1024"
    )

    # Save the image
    image_url = image_response.data[0].url
    image_response = requests.get(image_url)
    image = Image.open(BytesIO(image_response.content))
    image.save("generated_image.png")

    # Extract and parse the tweet JSON response
    tweet_content = tweet_response.choices[0].message.content
    try:
        tweet_json = json.loads(tweet_content)
        tweet_text = tweet_json["tweet"]
    except (json.JSONDecodeError, KeyError):
        tweet_text = tweet_content

    return {
        "tweet": tweet_text,
        "image_path": "generated_image.png"
    }

def generate_tweet_only():
    # Select a random tweet prompt
    tweet_templates = prompt_data["tweet_prompt"]
    random_template = random.choice(tweet_templates)

    # Generate tweet using the tweet_text_prompt
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": random_template["tweet_text_prompt"]}
        ],
        temperature=0.4
    )

    # Extract and parse the tweet JSON response
    tweet_content = response.choices[0].message.content
    try:
        tweet_json = json.loads(tweet_content)
        return tweet_json["tweet"]
    except (json.JSONDecodeError, KeyError):
        return tweet_content

def generate_reply(user_tweet):
    """Generate a reply to a user's tweet using the OpenAI API."""
    try:
        # Get the reply prompt template
        prompt_template = prompt_data["reply_prompt"]
        
        # Create the full prompt by joining the task and instructions
        instructions = prompt_template["instructions"].copy()
        instructions[1] = f"User's Tweet: {user_tweet}"  # Update the user tweet
        prompt = prompt_template["task"] + "\n" + "\n".join(instructions)

        print(f"Generating reply to: {user_tweet}")
        
        # Generate a response using OpenAI's ChatCompletion
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt}
            ],
            temperature=0.4
        )

        # Extract and parse the reply JSON response
        reply_content = response.choices[0].message.content
        print(f"Raw AI response: {reply_content}")
        
        try:
            reply_json = json.loads(reply_content)
            return reply_json["reply"]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing JSON response: {e}. Using raw content instead.")
            # If we can't parse the JSON, just return the raw content
            # Clean up the response if it contains JSON-like content
            if "{" in reply_content and "}" in reply_content:
                # Try to extract just the reply text
                start = reply_content.find('"reply":')
                if start != -1:
                    start += 9  # Length of '"reply": "'
                    end = reply_content.find('"', start)
                    if end != -1:
                        return reply_content[start:end]
            
            return reply_content
    except Exception as e:
        print(f"Error generating reply: {e}")
        # Return a fallback response
        return "Thanks for reaching out! Check out our symptom tool at https://harley.healthchat.ai/ for personalized health insights. #HarleyAI #AskHarley"

# Only run this code if the file is executed directly, not when imported
if __name__ == "__main__":
    # Example usage:
    result = generate_tweet_and_image()
    print("Generated Tweet:", result["tweet"])
    print("Image saved at:", result["image_path"])

    # tweet = generate_tweet_only()
    # print("Generated Tweet:", tweet)

    # reply = generate_reply("Any doctors here? I've been coughing non-stop for three days.")
    # print("Generated Reply:", reply)