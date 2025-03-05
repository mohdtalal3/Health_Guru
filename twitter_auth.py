import tweepy

oauth1_user_handler = tweepy.OAuth1UserHandler(
    "v2bfgmF7wUH5QpDO1L4y07H8E", "mfkYoHl0CMAcUjWQi6F4B2AZxGmc7zV3ASp4ls9VEQdh2LZQdT",
    callback="oob"
)
print(oauth1_user_handler.get_authorization_url())
verifier = input("Input PIN: ")
access_token, access_token_secret = oauth1_user_handler.get_access_token(
    verifier
)

print(access_token,access_token_secret)