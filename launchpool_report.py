import asyncio
from twikit import Client
from configuration import get_twitter_credentials
from datetime import datetime, timezone
async def fetch_user_tweets_with_word(username, word, limit=5):
    client = Client()
    
    config = get_twitter_credentials()

    # Activate the client (required for guest access)
    await client.login(
        auth_info_1=config['login'],
        auth_info_2=config['email'],
        password=config['password']
    )
    
    # Get the user by screen name
    user = await client.get_user_by_screen_name(username)
    
    # Fetch tweets from the user's timeline
    tweets = await client.get_user_tweets(user.id, 'Tweets', count=limit)
    
    current_time = datetime.now(timezone.utc)
    matching_tweets = []
    
    for tweet in tweets:
        tweet_time_utc = tweet.created_at_datetime.replace(tzinfo=timezone.utc)
        time_diff = current_time - tweet_time_utc
        
        # Check if the specific word is in the tweet text
        if word.lower() in tweet.text.lower():
            matching_tweets.append({
                "text": tweet.text,
                "created_at": tweet.created_at,
                "time_ago": str(time_diff)
            })
    return matching_tweets