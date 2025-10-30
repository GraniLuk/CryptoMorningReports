"""Configuration management and environment variable handling."""

import os

from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


def get_kucoin_credentials():
    return {
        "api_key": os.getenv("KUCOIN_API_KEY"),
        "api_secret": os.getenv("KUCOIN_API_SECRET"),
        "api_passphrase": os.getenv("KUCOIN_API_PASSPHRASE"),
    }


def get_twitter_credentials():
    return {
        "login": os.getenv("TWITTER_LOGIN"),
        "email": os.getenv("TWITTER_EMAIL"),
        "password": os.getenv("TWITTER_PASSWORD"),
        "auth_token": os.getenv("TWITTER_AUTH_TOKEN"),
        "ct0": os.getenv("TWITTER_CT0"),
    }
