import tweepy
import json
import random
import os
from ai_utils import *

def load_config():
    """Load Twitter API credentials from config file."""
    with open("config.json", "r") as file:
        config = json.load(file)
    return config["Aalexhealth_token"]

def initialize_twitter_client(credentials):
    """Initialize and return a Tweepy client with the given credentials."""
    client = tweepy.Client(
        bearer_token=credentials["access_bearer_token"],
        consumer_key=credentials["consumer_key"],
        consumer_secret=credentials["consumer_secret"],
        access_token=credentials["access_token"],
        access_token_secret=credentials["access_secret"]
    )
    
    # Initialize API v1.1 for media upload
    auth = tweepy.OAuth1UserHandler(
        credentials["consumer_key"],
        credentials["consumer_secret"],
        credentials["access_token"],
        credentials["access_secret"]
    )
    api = tweepy.API(auth)
    
    return client, api

def generate_tweet_only():
    """Generate a tweet without an image using the existing tweet prompts."""
    # Load prompt templates
    with open("prompts_template_alex.json", "r", encoding="utf-8") as file:
        prompt_data = json.load(file)
    
    # Select a random tweet prompt from the Image_prompts section
    image_templates = prompt_data["Image_prompts"]
    random_template = random.choice(image_templates)
    
    # Initialize the OpenAI client
    from openai import OpenAI
    import os
    from dotenv import load_dotenv
    
    # Load environment variables from .env file
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    
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

def post_tweet_with_image(client, api, tweet_text, image_path):
    """Post a tweet with an image."""
    try:
        # Upload the image
        media = api.media_upload(image_path)
        
        # Post the tweet with the media
        response = client.create_tweet(
            text=tweet_text,
            media_ids=[media.media_id]
        )
        print(f"Tweet with image posted successfully! Tweet ID: {response.data['id']}")
        return response
    except Exception as e:
        print(f"Error posting tweet with image: {e}")
        return None

def post_tweet_without_image(client, tweet_text):
    """Post a tweet without an image."""
    try:
        response = client.create_tweet(text=tweet_text)
        print(f"Tweet posted successfully! Tweet ID: {response.data['id']}")
        return response
    except Exception as e:
        print(f"Error posting tweet: {e}")
        return None

def post_random_tweet(image_probability=0.7):
    """
    Post a tweet with or without an image based on the given probability.
    
    Args:
        image_probability: Float between 0 and 1 representing the probability 
                          of posting a tweet with an image (default: 0.7)
    """
    # Load credentials and initialize clients
    credentials = load_config()
    client, api = initialize_twitter_client(credentials)
    
    # Decide whether to post with an image based on probability
    if random.random() < image_probability:
        print("Generating tweet with image...")
        result = generate_tweet_and_image()
        tweet_text = result["tweet"]
        image_path = result["image_path"]
        
        # Post tweet with image
        post_tweet_with_image(client, api, tweet_text, image_path)
    else:
        print("Generating tweet without image...")
        tweet_text = generate_tweet_only()
        
        # Post tweet without image
        post_tweet_without_image(client, tweet_text)

if __name__ == "__main__":
    # You can adjust the probability as needed
    post_random_tweet(image_probability=0.7) 