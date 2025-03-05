import tweepy
import json

with open("config.json", "r") as file:
    config = json.load(file)

# Extract credentials
credentials = config["Aalexhealth_token"]

# Initialize Tweepy Client
client = tweepy.Client(
    bearer_token=credentials["access_bearer_token"],
    consumer_key=credentials["consumer_key"],
    consumer_secret=credentials["consumer_secret"],
    access_token=credentials["access_token"],
    access_token_secret=credentials["access_secret"]
)
# Function to post a tweet
def post_tweet(message):
    try:
        # Posting a tweet
        tweet = client.search_recent_tweets(query="health",max_results=10)
        print(tweet)
    except Exception as e:
        print(f"Error posting tweet: {e}")

# Post a test tweet
post_tweet("Hello Guru")
