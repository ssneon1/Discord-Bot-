

import asyncio
import logging
import os
import random
import re
from collections import defaultdict
from datetime import timedelta, datetime, timezone
from typing import Optional, Dict, List, Set, Union

# Try to import discord with error handling
discord_available = True
try:
    import discord
    from discord.ext import commands, tasks
except (ImportError, Exception) as e:
    discord_available = False
    print(f"Warning: Discord library not available. Error: {e}")

from dotenv import load_dotenv
import wikipedia
from duckduckgo_search import DDGS

try:
    import webserver  # type: ignore
except ImportError:
    webserver = None
import pytz
from datetime import datetime, time as dtime
from openai import OpenAI
from huggingface_hub import InferenceClient

load_dotenv()

if discord_available:
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    
    if not DISCORD_TOKEN:
        raise ValueError("DISCORD_TOKEN environment variable is not set")
    
    intents = discord.Intents.all()
    intents.message_content = True  # Required for accessing message content
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("discord_bot")
    
    if webserver:
        webserver.keep_alive()
else:
    print("Discord is not available. Running in offline mode for testing.")
    # Define dummy bot object for testing purposes
    class DummyBot:
        def __init__(self):
            pass
        def command(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
        def event(self, func):
            # Return the function as-is for offline mode
            return func
    
    # Define dummy tasks module
    class DummyLoop:
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, func):
            return func
    
    class DummyTasks:
        @staticmethod
        def loop(*args, **kwargs):
            return DummyLoop()
    
    tasks = DummyTasks()
    
    bot = DummyBot()

# Initialize Hugging Face client after loading environment variables
try:
    hf_token = os.getenv("HUGGING_FACE_TOKEN")
    if hf_token and hf_token != "your_hugging_face_token_here":
        client = InferenceClient(
            model="meta-llama/Llama-3.2-1B-Instruct",
            token=hf_token
        )
        # Validate the client with a test call
        try:
            client.text_generation("Test", max_new_tokens=1)
            print("✅ Hugging Face client initialized and verified successfully")
        except Exception as e:
            print(f"⚠️ Hugging Face token issue: {e}")
            print("⚠️ AI features will operate in fallback mode.")
            client = None
    else:
        print("⚠️ Hugging Face token not found. Using fallback responses.")
        client = None
except Exception as e:
    print(f"Warning: Could not initialize Hugging Face client: {e}")
    client = None

# Set your timezone (India Standard Time)
IST = pytz.timezone("Asia/Kolkata")

# Replace this with your channel ID
CHANNEL_ID = 1365013763241017558  # 👈 Replace with your actual channel ID

# ============================
# Constants & Globals
# ============================
ALLOWED_GUILD_ID = 123456789012345678  # Replace with your guild ID
SPAM_TIME_FRAME = 10
SPAM_MESSAGE_LIMIT = 5
TIMEOUT_DURATION = 30  # seconds

user_message_times: Dict[int, List[datetime]] = defaultdict(list)
if discord_available:
    user_recent_messages: Dict[int, List[discord.Message]] = defaultdict(list)
else:
    user_recent_messages: Dict[int, List] = defaultdict(list)
modmail_map: Dict[int, int] = {}

# ============================
# Banned Words Handler
# ============================
class BannedWords:
    def __init__(self):
        self.custom_words = {"global": set()}

    def add_custom_words(self, words, category="global"):
        if category not in self.custom_words:
            self.custom_words[category] = set()
        self.custom_words[category].update(word.lower() for word in words)

    def contains_banned_word(self, message):
        message_lower = message.lower()
        for word in self.custom_words.get("global", []):
            if re.search(rf"\b{re.escape(word)}\b", message_lower):
                return True
        return False

    def get_banned_words(self, message):
        message_lower = message.lower()
        found = []
        for word in self.custom_words.get("global", []):
            if re.search(rf"\b{re.escape(word)}\b", message_lower):
                found.append(word)
        return found


banned_word_list =[
            "fuck", "bitch", "bastard", "asshole", "cunt", "slut", "dick", "cock", "prick",
            "motherfucker", "pussy", "jerk", "shit", "moron", "crap", "damn", "retard",
            "whore", "fag", "faggot", "douchebag", "twat", "wanker", "nigga", "nigger",
            "son of a bitch", "kys", "kill yourself", "uninstall", "trash", "scrub",
            "dogwater", "suck", "ez", "loser", "fatherless", "adopted", "touch grass"
        
        
        # Hindi
            "chutiya", "madarchod", "bhosdiwala", "gaand", "loda", "behenchod", "randi",
            "kutta", "chut", "launda", "maa ki chut", "teri maa", "mc", "bc", "kutte", "randwa",
            "lund", "choot", "bhen ke laude", "teri maa ka bhosda", "gaandu", "chutiyapa",
            "bhosad", "bhosadi", "chutmarike", "gandmara", "lavde", "maa ka bhosda",
            "randi ka bacha", "teri maa randi", "teri behen randi", "chootiya", "jhaat", "jhaant",
            "bhonsdiwale", "maa chuda", "behen ke laude", "lund choos", "gaand mara", "choot chatora",
            "gel chodi gand andhi rand", "tere baap ki chut", "maa ke laude", "behen ke lund",
            "teri maa ki chut", "teri behen ki chut", "maa ka lund", "behen ka lund"
        
        
        # Marathi
       
            "gand", "chod", "zhaavla", "lavda", "bhosdi", "randi", "bhadwa", "kutta",
            "baapacha", "aichya gavat", "bawlat", "phodri", "gadhav", "akramhshi", "andya",
            "aighala", "zhatu", "zhavat", "bhund", "bocha", "bulli", "chut", "gandu",
            "haramkhor", "jhant", "kutra", "lavdya", "maaicha", "madarchod", "rand",
            "saala", "tharki", "bhosda", "chinar", "chutad", "fokatya", "ghandu", "zhavat",
            "aai zav", "aai zavli", "aai zavlya", "aai zavla", "aai zavlya cha", "aai zavlya chi",
            "aai zavlya che", "aai zavlya la", "aai zavlya ne", "aai zavlya ni", "aai zavlya cha","Tuzya aaila zaval","Zavnya"
        
        
        # Bengali
      
            "chod", "choda", "chudir baccha", "chudbo", "chudi", "loda", "lode", "lodachoda",
            "maa ke chudi", "bon chuda", "bokachoda", "shuar", "kukur", "chot", "chotmarani",
            "chudbaaz", "maachuda", "bonchuda", "tor maa ke chudi", "tor bon ke chudi", "lund",
            "gaandu", "randi", "haraami", "chinal", "boka", "pagol", "fatu", "dhorbo",
            "tor maa r choda", "tor bou r choda", "tor bon r choda", "tor maa r chod",
            "tor bou r chod", "tor bon r chod", "tor maa r chudi", "tor bou r chudi",
            "tor bon r chudi", "tor maa r chud", "tor bou r chud", "tor bon r chud"
      
        
        # Punjabi
        
            "chutiya", "madarchod", "behenchod", "randi", "tera baap", "maa da bhosda",
            "chod", "lund", "ghandu", "kutta", "suar da puttar", "behn di", "sala",
            "teri maa di", "teri behen di", "teri maa da", "teri behen da", "teri maa di chut",
            "teri behen di chut", "teri maa da lund", "teri behen da lund", "teri maa da bhosda",
            "teri behen da bhosda", "teri maa di gand", "teri behen di gand"
       
        
        # South Indian Languages (Tamil/Telugu/Kannada/Malayalam)
       
            "thevudiya", "pochi", "punda", "naaye", "kundi", "dengudu", "lavda", "kodaka",
            "sule", "soole", "bosi", "pund", "thendi", "thalla", "kazhutha", "nayinte",
            "dongamunda", "thikka", "sani", "kirik", "holeya", "gandu", "chamkili", "kuthra",
            "pakal", "kothi", "pucchi", "gotya", "chhinaal", "zhavli", "madarchod",
            "ninna amma", "ninna thayi", "ninna maga", "ninna thangi", "ninna appa",
            "amma na", "bejaar", "chut naku", "lund tinod", "sulu chuchu", "gand mara"
     
        
        # Gaming Slang
        
             "kill yourself","end yourself","fuck", "bitch", "asshole", "dick", "slut", "nigga",
             "madarchod", "bhosdike", "chutiya", "lund", "beti chod", "gaand", "randi",
             "bhenchod", "bhench*d", "mc", "bc", "chootiya", "kutte", "gandu",
             "lode", "lauda", "maa ka bhosda", "teri maa", "teri behen", "chodu", "randwa",
             "bol teri gand kaise maru", "gandmara", "chdmarike", "choot chatora",
             "gel chodi gand andhi rand", "lavde", "madar chod", "gand maar lunga",
             "tere baap ki chut hai", "tere maa market me nanga nach kr rahi hai",
             "kutta kamine bsdk chutiya", "teri maa randwi hai", "lund ke tope",
             "chut ke kitde", "chinal ki aulad", "chutmari ka choda", "teri chut", "bhg bsdk",
             "bhen ka lavda", "chut chatora", "jhaat bara bar", "me toh chut ka shikari hu", "bhosda", "chutad","jhat","अकराम्हशी","अकराम्हशीचा","अकराम्हशीच्या","आंद्या","आंद्याचा","आंद्याच्या","आंद्यात","आईघाला","आईघाल्","आईघाल्या","आईघाल्याचा","आईजवाडा","आईजवाडाचा","आईझव","आईझवली","आईझवलीचा","आईझवाडा","आईझवाडाचा","कँडल","कँडलचा","कँडलच्या","कृतघ्न","गांड","गांडचा","गांडच्या","गांडीचा","गांडीत","गांडू","गांडूचा","गांडूच्या","गांडूत","गाढव","गाढवागांडुळ","गोट्या","गोट्याचा","गोट्याच्या","गोट्यात","चावट","चीनाल","चीनालचा","चीनालच्या","चुत","चुतचा","चुतच्या","चुतत","चुतमारीचा","चुतमारीच्या","चुतमारीच्यात","छिनाल","छिनालचा","छिनालच्या","झवली","झवलीचा","झवलीत","झवाड्या","झवाड्याचा","झवाड्याच्या","झाटू","झाटूचा","झाटूच्या","झाटूत","नालायकच्यायला","पागलगुदा","पुच्ची","पुच्चीचा","पुच्चीच्या","पुच्चीत","फोकणीच्या","फोकणीच्याचा","फोकणीच्यात","फोद्री","फोद्रीचा","फोद्रीच्या","फोद्रीच्यात","फोद्रीत","बावळट","बावळटच्या","बावळटत","बुडाला","बुल्ली","बुल्लीचा","बुल्लीत","बेअक्कल","बेशरम","बोचा","बोचाच्या","बोचात","बोच्याबुल्लीच्या","भडवा","भडविच्याभिकारचोट","भडव्या","भडव्यात","भुंड्","भुंड्त","भुंड्यात","भुंड्यातत","भोक","भोकचा","भोकत","भोकाच्या","भोसडा","भोसडाचा","भोसडात","भोसडीच्या","भोसडीच्यात","मंद","माईचा","माईचात","माईच्या","मादरचोद","मारीच्या","मारीच्यात","मुठ्ठया","मुठ्ठयाचा","मुठ्ठयात","मूर्ख","रंडी","रंडीचा","रंडीच्या","रंडीच्यात","रंडीत","रांड",
"रांडचा","रांडच्या","रांडीच्या","रांडीच्यात","लवड्या","लवड्याचा","लवड्याच्या","लवड्यात"
"साला","हरामखोर","हलकट" "हरामखोरचा","हरामखोरच्या","हरामखोरात","akramhshi", "akramhshicha", "akramhshichya","andya", "andyacha", "andyachya", "andyat",
"aighala", "aighalya", "aighalyacha",
"aijawada", "aijawadacha",
"aizhav", "aizhavli", "aizhavlicha", "aizhawada", "aizhawadacha",
"candle", "candlecha", "candlechya",
"krutaghn",
"gand", "gandcha", "gandchya", "gandicha", "gandit",
"gandu", "ganducha", "ganduchya", "gandut",
"gadhav", "gadhavagandul",
"gotya", "gotyacha", "gotyachya", "gotyat",
"chawat", "chinal", "chinalcha", "chinalchya",
"chut", "chutcha", "chutchya", "chuttat",
"chutmari", "chutmarcha", "chutmarchyat",
"chhinaal", "chhinaalcha", "chhinaalchya","zhavli", "zhavlicha", "zhavlit",
"zhawadya", "zhawadyacha", "zhawadyachya",
"zhatu", "zhatucha", "zhatuchya", "zhatut",
"nalayakchyayla","pagalguda",
    # Family-Based
    "ninna amma chudrappa", "ninna thayi bosi", "ninna thayi chuchu", "ninna amma maga", "ninna thangi naakthini",
    "ninna magalu daari dalli", "thayi chut tinod maga", "ninna appa chut kaayi", "amma na naakthini", "bejaar thayi chut",

    # Mental/Character/Caste
    "gandu", "lusu", "loose huduga", "mental case", "buddhi illa", "tharle", "kirik", "mentalt",
    "chamkili", "chamaar maga", "holeya", "holeyaru", "basse kasta",

    # Animal
    "nayi", "handi", "saalige", "hasu", "kudure", "koli maga", "mooru nayi", "hakki maga", "hejjegalu", "enu gothilla nayi",

    # Gaming Slang
    "noob nayi", "camper sulen", "scope nodoke baralla", "ninna team full gandu", "clutch beda maga",
    "teri lobby gayi tel lagaake", "mic haaki mare", "stream sniping soole", "hacker nayi", "peek madoke baralla",
    "sulen jasti swalpa skill ko",

    # Combo Insults
    "ninna amma chut alli chalu aagidale", "chut thora maga", "lund ella alli ide",
    "ninna thayi soole dalli kelsa madtha idale", "pundeya gandu", "chut borege saku", "sulekke nayi kooda baralla",# Genital/Sexual
    "bhalu", "mukhrot dhula", "patar", "chutmarani", "chutkhaowa", "lund kha", "gaand phati gol",
    "chut dhula", "suri kha", "chut diya", "chut khai ase",

    # Family-Based
    "tor maari", "tor bou", "tor ma randi", "tor bhonti randi", "tor ma chut", "tor bou lund",
    "tor bhonti chut", "tor ma lund", "tor maa gaand diya", "tor bou randi", "tor maa chut khai ase",

    # Mental/Character
    "bokachoda", "bura bokachoda", "pagol", "uthoni", "bekar", "bhagwan r nai", "dhemeli",
    "ulta jukti diya", "bokami kori thaka", "matha dhula", "akkal nai", "moron",

    # Animal
    "suwor", "suworer baccha", "xial", "kutta", "kukura", "goru", "gadha", "bandor",
    "dhuli", "dhol", "kukurni", "suali kutta",

    # Gaming/Online
    "noob", "hack use kori khel", "lundor aim", "camper kutta", "tor aim chutot", "tor gaand te crosshair",
    "tor mouse gaandot", "tor ping chut", "camper randi", "aim assist randi",

    # Hybrid/Roasting
    "tor maari chut", "tor bou chut khai ase", "lund diya randi", "chut dhula bhonti",
    "tor aim maa te", "gaand khuli gol", "mobile te maa chut dise", "stream snipe kori chut kha",# Genital
    "chod", "choda", "chudir baccha", "chudbo", "chudi", "chudchhi", "chudachhi",
    "choda dibi", "chudi dibi", "chudiye debo", "chot", "chotmarani", "chotkhani",
    "chot khaowa", "chot chush", "loda", "lode", "lodachoda", "loda chusbi", "loda dhukabo",
    "biran", "biraler chot", "chudbaaz", "chuda player",

    # Family/Parental
    "tor maa ke chudi", "tor bon ke chudi", "maa chuda", "bon chuda", "maa ke loda",
    "maa r chot", "maa ke chodchi", "maa choder player", "tor bon choda",
    "maa ke chudbo", "maa ke chudiye debo", "maa r loda chushe felbi",
    "tor bou r chot", "bou ke chudchi", "bou ke lodai", "tor bou chudi",

    # Mental
    "bokachoda", "boka", "pagol", "pagla", "fatu", "boka choda", "byatha",
    "bhootni", "dhorbo", "brain nai", "buddhiheen",

    # Animal
    "shuar", "shuarer baccha", "kukur", "kukur choda", "bandor", "beral",
    "goru", "gadha", "ghoda", "suorer chhana", "bandorer chot",

    # Online Gaming
    "noob choda", "stream sniping randir baccha", "aim nai loder moto",
    "camperer maa choda", "gaand mara player", "neter chot", "crosshair maa r chot",
    "spray maa te", "hackerer chot", "loda aim assist", "jhari galo lobby",

    # Hybrid / Dank Combos
    "tor maa ke loda dhukiye debo", "tor bon er chot bhenge debo", "loda dhuke chudbo",
    "bou ke maa banabo", "stream kore maa chod", "chot e loda", "tor family ek shathe chudbo",
    "tor chot porjonto toxic", "loder moto speech", "maa bon ekta pod er upor"

 ]

banned_words = BannedWords()
banned_words.add_custom_words(banned_word_list, "global")


# ============================
# Friendly Replies & Fallbacks
# ============================
general_knowledge_qa = {
    "what is the capital of france": "Paris 🇫🇷",
    "who wrote harry potter": "J.K. Rowling ✍️",
    "what is the largest planet": "Jupiter is the largest planet in our solar system! 🪐",
    "who is the president of usa": "As of now, it's Joe Biden.",
    "what is pi": "Pi (π) is approximately 3.14159.",
    "what is the speed of light": "The speed of light is about 299,792 kilometers per second.",
    "who invented the telephone": "Alexander Graham Bell invented the telephone.",
    "how many continents are there": "There are 7 continents on Earth.",
    "what's the tallest mountain": "Mount Everest is the tallest mountain above sea level.",
    "when is independence day (india)": "India celebrates Independence Day on 15th August."
}

# Enhanced Happy/Funny Reply Maker - Now AI-powered
# This dictionary is kept for backward compatibility but AI responses are prioritized
funny_replies = {
    ("hello", "hi", "hey", "yo", "oye", "sup", "wassup", "namaste", "salaam", "good morning", "good afternoon", "good evening"): [],
    ("or", "or kya", "or batao", "or bhai", "aur bata", "aur kya", "kya scene hai"): [],
    ("how are you", "kaisa hai", "kya haal hai", "kaisi ho", "how's it going", "kaisi chal rahi hai life"): [],
    ("what's up", "whats up", "kya chal raha hai", "kya ho raha hai"): [],
    ("tell me a joke", "joke", "koi joke sunao", "make me laugh"): [],
    ("who made you", "creator", "banaya kisne", "who is your developer"): [],
    ("bye", "good night", "gn", "see you", "goodbye", "tc", "take care"): [],
    ("thanks", "thank you", "ty", "shukriya", "dhanyawad"): [],
    ("love you", "i love you bot", "ily bot", "luv u bot"): [],
    ("happy", "excited", "celebration", "party"): [],
    ("motivate", "inspire", "inspiration", "feel good"): []
}

async def generate_friendly_reply_with_ai(trigger: str, author_mention: str) -> str:
    """Generate a friendly reply using AI"""
    if client is None:
        # Enhanced fallback with more variety and humor
        enhanced_fallbacks = [
            f"Hey {author_mention}! 👋 What's crackin' my dude? Ready to make this server lit or what? 🔥",
            f"Yo {author_mention}! Wassup fam? Hope you're having a day better than my WiFi connection! 😂📶",
            f"Hello there {author_mention}! How's life treating you? Hope it's going smoother than butter on hot toast! 🧈😊",
            f"Hi {author_mention}! What's good? Ready to drop some knowledge bombs or just vibe? 💣💥",
            f"Hey {author_mention}! Long time no see! You been ghosting us or just busy being awesome? 👻✨",
            f"Sup {author_mention}! Hope your day is going better than a TikTok dance trend! 🕺📱",
            f"Hello {author_mention}! Ready to turn this chat into a party or should I start the music? 🎉🎵"
        ]
        return random.choice(enhanced_fallbacks)
    
    try:
        # Vary the prompt to make responses less predictable and more human-like
        human_like_prompts = [
            f"Respond naturally and casually as a friendly person would to: '{trigger}'. Address the user as {author_mention}. Be genuine and add some personality.",
            f"Act like a real friend replying to '{trigger}'. Include {author_mention} naturally. Keep it conversational and engaging.",
            f"Reply to '{trigger}' in a friendly, human way. Address {author_mention} like a real person would. Be authentic and warm.",
            f"React to this like a human would: '{trigger}'. Mention {author_mention} in a natural way. Be personable with some humor.",
            f"Reply like a real person chatting with a friend about: '{trigger}'. Use {author_mention} naturally. Be relatable.",
            f"Respond as if you're texting a friend: '{trigger}'. Address {author_mention} casually. Keep it real and friendly.",
        ]
        selected_prompt = random.choice(human_like_prompts)
        
        # Use Hugging Face Inference API (conversational)
        response = client.chat_completion(
            messages=[{"role": "user", "content": selected_prompt}],
            max_tokens=150,
            temperature=0.95,
            top_p=0.98,
        )
        
        reply = response.choices[0].message.content.strip()
        # Replace mention placeholder if needed
        return reply.replace('{mention}', author_mention)
    except Exception as e:
        log.error(f"AI Friendly reply generation error: {e}")
        # Check if it's an API-related error and use more robust fallback
        error_str = str(e)
        if 'API key' in error_str or '500' in error_str or 'Internal Server Error' in error_str:
            log.warning("API key or server issue detected. Using enhanced fallback responses.")
            enhanced_fallbacks = [
                f"Hey {author_mention}! Great to hear from you! What's on your mind?",
                f"Hi {author_mention}! That's interesting! Tell me more about it.",
                f"Hello {author_mention}! I'm enjoying our chat! 😊",
                f"Hey {author_mention}! That's a cool thing to share! 👍",
                f"Hi {author_mention}! Always fun talking with you! 🌟"
            ]
            return random.choice(enhanced_fallbacks)
        else:
            # Fallback to simple response
            return f"Hey {author_mention}! Nice to chat with you! 😊"


# The lists will be kept for backup purposes only

def get_backup_truth():
    truth_questions = [
        "What's the strangest dream you've ever had?",
        "Would you rather live without the internet or without AC/heater?",
        "What's the weirdest thing you've eaten?",
        "What's the most embarrassing thing that happened to you recently?",
        "If you could swap lives with someone for a day, who would it be?",
        "What's your most unusual talent?",
        "What's the weirdest thing you believed as a child?",
        "If you could instantly become an expert in any skill, what would it be?",
        "What's the most ridiculous thing you've argued about?",
        "What's the weirdest compliment you've ever received?"
    ]
    return random.choice(truth_questions)

def get_backup_dare():
    dare_challenges = [
        "Do your best impression of someone in your family.",
        "Sing the chorus of your favorite childhood song.",
        "Tell a joke and make at least one person laugh.",
        "Do 10 push-ups right now.",
        "Send a screenshot of your recent text messages (without showing names).",
        "Speak in an accent for the next 3 messages.",
        "Share your most embarrassing photo from your camera roll.",
        "Do your best dance move and send a video.",
        "Send a voice message singing 'Happy Birthday'.",
        "Make up a story about the last photo in your gallery."
    ]
    return random.choice(dare_challenges)

# Game responses
game_responses = {
    "rock": ["Rock crushes scissors! You win! 🪨", "Rock smashes scissors! Victory! 🪨", "Scissors get crushed by rock! 🪨"],
    "paper": ["Paper covers rock! You win! 📄", "Paper suffocates rock! Victory! 📄", "Rock gets covered by paper! 📄"],
    "scissors": ["Scissors cut paper! You win! ✂️", "Scissors slice through paper! Victory! ✂️", "Paper gets chopped by scissors! ✂️"]
}

# YouTube update phrases
youtube_updates = [
    "Check out this awesome video! 🎥",
    "Just uploaded something cool! 📽️",
    "New content is live! 📺",
    "Fresh video alert! 📷",
    "New upload - don't miss it! 📽️",
    "Latest video is now available! 🎬"
]

# Add more relatable fallback replies - Now AI-powered
# Static fallbacks are kept as backup
fallback_replies = [
    "Hmmm... interesting! Tumhe pata hai, honey never spoils. 😲",
    "Accha yeh batao, tum sabse zyada kis cheez mein expert ho?",
    "Waise, tumhe memes pasand hai? Main bhi meme lover hoon!",
    "Pata hai, octopus ke teen dil hote hain! 🐙",
    "Main samajh nahi paaya, but tumhare saath baat kar ke maza aata hai!",
    "Yeh question tough tha! Tum batao, kuch aur poochna hai?",
    "That's an interesting perspective! Tell me more. 🤔",
    "I hadn't thought of it that way before! 🧠",
    "Life's full of surprises, isn't it? 😄",
    "Sometimes the best conversations come from the simplest questions! 💬",
    "What an intriguing thought! Keep sharing. 🤗"
]

async def generate_fallback_reply_with_ai(message_content: str) -> str:
    """Generate a fallback reply using AI"""
    if client is None:
        # Enhanced fallback with more personality and humor
        enhanced_fallbacks = [
            "That's super interesting! Tell me more about that - I'm all ears! 👂✨",
            "Wow, you just dropped some serious knowledge! Mind blown! 🤯💥",
            "I love how you think! That's actually brilliant! 🧠💡",
            "Okay but can we talk about how cool that idea is for a sec? Amazing! ✨🔥",
            "You always come through with the good stuff! Love your energy! 💫😊",
            "That's the kind of thing that makes conversations worth having! Thanks for sharing! 🙌",
            "Bro, your brain works in mysterious and wonderful ways! Respect! 🙏😎"
        ]
        return random.choice(enhanced_fallbacks)
    
    try:
        # Vary the prompt to make responses less predictable and more human-like
        human_like_prompts = [
            f"Respond to this like a real person would: '{message_content}'. Be genuine and conversational with some personality.",
            f"Act like a friend replying to this message: '{message_content}'. Keep it natural and engaging.",
            f"Reply to '{message_content}' as if you're texting a friend. Be authentic with a touch of humor.",
            f"React to this message like a human would: '{message_content}'. Stay personable and relatable.",
            f"Reply like you're chatting with someone online: '{message_content}'. Be casual and friendly.",
            f"Respond as if you're a real person in a conversation about: '{message_content}'. Be warm and approachable.",
        ]
        selected_prompt = random.choice(human_like_prompts)
        
        # Use Hugging Face Inference API (conversational)
        response = client.chat_completion(
            messages=[{"role": "user", "content": selected_prompt}],
            max_tokens=150,
            temperature=0.95,
            top_p=0.98,
        )
        
        reply = response.choices[0].message.content.strip()
        return reply
    except Exception as e:
        log.error(f"AI Fallback reply generation error: {e}")
        # Check if it's an API-related error and use more robust fallback
        error_str = str(e)
        if 'API key' in error_str or '500' in error_str or 'Internal Server Error' in error_str:
            log.warning("API key or server issue detected. Using fallback responses.")
            enhanced_fallbacks = [
                "Thanks for sharing that!",
                "That's really interesting!",
                "I appreciate you telling me this.",
                "That's cool, tell me more!",
                "Nice! I enjoyed reading that."
            ]
            return random.choice(enhanced_fallbacks)
        else:
            return random.choice(fallback_replies)


# ============================
# General Knowledge Q&A
# ============================
general_knowledge_qa = {
    "who is the president of india": "As of 2025, the President of India is Droupadi Murmu.",
    "who is the prime minister of india": "As of 2025, the Prime Minister of India is Narendra Modi.",
    "capital of india": "The capital of India is New Delhi.",
    "national animal of india": "The national animal of India is the Bengal Tiger.",
}

# ============================
# Indian Festival Wishes
# ============================
indian_festivals = ["diwali", "holi", "dussehra", "navratri", "ganesh chaturthi", "makar sankranti", "janmashtami", "eid", "christmas", "new year"]

async def generate_festival_wish_with_ai(festival_name: str) -> str:
    """Generate a festival wish using AI"""
    if client is None:
        # Fallback wishes
        fallback_wishes = {
            "diwali": "Happy Diwali! May this Festival of Lights bring joy, prosperity, and happiness to your life! 🪔",
            "holi": "Happy Holi! May the colors of this beautiful festival fill your life with happiness and joy! 🎨",
            "dussehra": "Happy Dussehra! May this festival inspire you to triumph over evil and negativity! 🏆",
            "navratri": "Happy Navratri! Nine days of divine energy and devotion! 🌸",
            "ganesh chaturthi": "Happy Ganesh Chaturthi! May Lord Ganesha bless you with wisdom and prosperity! 🐘",
            "makar sankranti": "Happy Makar Sankranti! May this harvest festival bring abundance to your life! 🌾",
            "janmashtami": "Happy Janmashtami! Celebrating the birth of Lord Krishna with devotion and joy! 🎭",
            "eid": "Eid Mubarak! May this holy occasion bring peace and happiness to your life! 🌙",
            "christmas": "Merry Christmas! May this festive season fill your heart with love and joy! 🎄",
            "new year": "Happy New Year! May the upcoming year be filled with success and happiness! 🎉",
        }
        return fallback_wishes.get(festival_name, f"Wishing you a wonderful {festival_name.capitalize()}! 🎉")
    
    try:
        # Vary the prompt to make responses less predictable and more human-like
        human_like_prompts = [
            f"Write a heartfelt {festival_name} wish like a real person would send to friends/family. Include emojis.",
            f"Create a warm and genuine {festival_name} greeting as if from a friend. Add appropriate emojis.",
            f"Craft a personal {festival_name} wish that feels sincere and emotional. Include festive emojis.",
            f"Express warm {festival_name} wishes like you're messaging a loved one. Use relevant emojis.",
        ]
        selected_prompt = random.choice(human_like_prompts)
        
        # Use Hugging Face Inference API (conversational)
        response = client.chat_completion(
            messages=[{"role": "user", "content": selected_prompt}],
            max_tokens=150,
            temperature=0.9,
            top_p=0.95,
        )
        
        wish = response.choices[0].message.content.strip()
        return f"🎊 **{wish}** 🎊"
    except Exception as e:
        log.error(f"AI Festival wish generation error: {e}")
        # Check if it's an API-related error and use more robust fallback
        error_str = str(e)
        if 'API key' in error_str or '500' in error_str or 'Internal Server Error' in error_str:
            log.warning("API key or server issue detected. Using fallback festival wishes.")
            fallback_wishes = {
                "diwali": "Happy Diwali! May this Festival of Lights bring joy, prosperity, and happiness to your life! 🪔",
                "holi": "Happy Holi! May the colors of this beautiful festival fill your life with happiness and joy! 🎨",
                "dussehra": "Happy Dussehra! May this festival inspire you to triumph over evil and negativity! 🏆",
                "navratri": "Happy Navratri! Nine days of divine energy and devotion! 🌸",
                "ganesh chaturthi": "Happy Ganesh Chaturthi! May Lord Ganesha bless you with wisdom and prosperity! 🐘",
                "makar sankranti": "Happy Makar Sankranti! May this harvest festival bring abundance to your life! 🌾",
                "janmashtami": "Happy Janmashtami! Celebrating the birth of Lord Krishna with devotion and joy! 🎭",
                "eid": "Eid Mubarak! May this holy occasion bring peace and happiness to your life! 🌙",
                "christmas": "Merry Christmas! May this festive season fill your heart with love and joy! 🎄",
                "new year": "Happy New Year! May the upcoming year be filled with success and happiness! 🎉",
            }
            return f"🎊 **{fallback_wishes.get(festival_name, f'Wishing you a wonderful {festival_name.capitalize()}! 🎉')}** 🎊"
        else:
            fallback_wishes = {
            "diwali": "Happy Diwali! May this Festival of Lights bring joy, prosperity, and happiness to your life! 🪔",
            "holi": "Happy Holi! May the colors of this beautiful festival fill your life with happiness and joy! 🎨",
            "dussehra": "Happy Dussehra! May this festival inspire you to triumph over evil and negativity! 🏆",
            "navratri": "Happy Navratri! Nine days of divine energy and devotion! 🌸",
            "ganesh chaturthi": "Happy Ganesh Chaturthi! May Lord Ganesha bless you with wisdom and prosperity! 🐘",
            "makar sankranti": "Happy Makar Sankranti! May this harvest festival bring abundance to your life! 🌾",
            "janmashtami": "Happy Janmashtami! Celebrating the birth of Lord Krishna with devotion and joy! 🎭",
            "eid": "Eid Mubarak! May this holy occasion bring peace and happiness to your life! 🌙",
            "christmas": "Merry Christmas! May this festive season fill your heart with love and joy! 🎄",
            "new year": "Happy New Year! May the upcoming year be filled with success and happiness! 🎉",
        }
        return f"🎊 **{fallback_wishes.get(festival_name, f'Wishing you a wonderful {festival_name.capitalize()}! 🎉')}** 🎊"

# Check if today is an Indian festival
from datetime import date, datetime

def check_indian_festival():
    # Simple date checking for festivals (would need more complex logic for lunar calendar)
    today = date.today()
    month_day = f"{today.month}-{today.day}"
    month_day_year = f"{today.month}-{today.day}-{today.year}"
    
    # More comprehensive festival dates (these are approximate/common dates)
    # In reality, many Indian festivals follow lunar calendars which require more complex calculations
    festival_dates = {
        # Month-Day format
        "1-1": "new year",          # New Year
        "1-14": "makar sankranti",  # Makar Sankranti
        "1-26": "republic day",     # Republic Day (India)
        "8-15": "independence day", # Independence Day (India)
        "10-2": "gandhi jayanti",   # Gandhi Jayanti
        
        # Year-specific dates (month-day-year format)
        "3-13-2025": "holi",        # Holi 2025
        "3-14-2026": "holi",        # Holi 2026
        "10-27-2024": "diwali",     # Diwali 2024
        "11-16-2025": "diwali",     # Diwali 2025
        "10-2-2024": "dussehra",    # Dussehra 2024
        "10-12-2025": "dussehra",   # Dussehra 2025
        "9-7-2024": "ganesh chaturthi",  # Ganesh Chaturthi 2024
        "8-26-2025": "ganesh chaturthi", # Ganesh Chaturthi 2025
        "1-14-2024": "makar sankranti",  # Makar Sankranti 2024
        "1-15-2025": "makar sankranti",  # Makar Sankranti 2025
        "11-15-2024": "navratri",       # Navratri 2024
        "10-2-2025": "navratri",        # Navratri 2025
        "1-15-2025": "makar sankranti", # Another possible date for Makar Sankranti
        
        # Regular month-day format (recurring annually)
        "12-25": "christmas",       # Christmas
    }
    
    # Check for year-specific date first, then month-day
    result = festival_dates.get(month_day_year, None)
    if result is None:
        result = festival_dates.get(month_day, None)
    
    return result

def get_general_knowledge(content: str) -> Optional[str]:
    return general_knowledge_qa.get(content.lower().strip().rstrip("?"))

async def get_ai_response(prompt: str) -> str:
    """Generate human-like responses using AI API"""
    if client is None:
        # Enhanced fallback with service attitude and humor
        service_fallbacks = [
            "Bro, I'm here 24/7 ready to serve! What can I help you with today? 😎",
            "Your wish is my command! Need anything? I'm like your personal digital butler! 🎩",
            "Ready to assist, boss! Just say the word and I'll make it happen! 💪",
            "At your service! What's on the agenda today? Let's make magic happen! ✨",
            "Need help? I'm like the Swiss Army knife of bots - ready for anything! 🔧",
            "Hello! I'm programmed to make your day better. What can I do for you? 😊",
            "Sir/madam, how may I assist you today? I'm here to serve and entertain! 🤖"
        ]
        return random.choice(service_fallbacks)
    
    try:
        # Enhanced prompts for more realistic, service-oriented, and humorous responses
        enhanced_prompts = [
            f"You're a super helpful Discord bot with a funny personality. Someone said: '{prompt}'. Respond like a chill friend who's also your personal assistant. Be helpful, add humor, and maybe throw in some trending slang. Tag the user naturally if needed.",
            f"Act like a cool bot butler who's also your best friend. Someone messaged: '{prompt}'. Give a helpful response with jokes and casual vibes. Make it feel like you're genuinely excited to help!",
            f"You're both a service bot and entertainer. Someone said: '{prompt}'. Respond with enthusiasm, helpful advice, and funny commentary. Be like that friend who's always ready to help AND crack jokes.",
            f"Role: Helpful bot with amazing sense of humor. Message received: '{prompt}'. Reply like you're genuinely excited to assist, add some wit, and make the person feel like they just got VIP treatment.",
            f"You're a bot who combines excellent customer service with stand-up comedy skills. Someone typed: '{prompt}'. Help them out while keeping things light and entertaining. Think helpful + hilarious!",
            f"Personality: Super helpful friend-bot with killer comedic timing. Incoming message: '{prompt}'. Provide valuable assistance while being the kind of friend everyone wants - helpful, funny, and totally relatable."
        ]
        selected_prompt = random.choice(enhanced_prompts)
        
        # Use Hugging Face Inference API (conversational)
        response = client.chat_completion(
            messages=[{"role": "user", "content": selected_prompt}],
            max_tokens=200,
            temperature=0.95,
            top_p=0.98,
        )
        ai_reply = response.choices[0].message.content
        # Clean up the response to remove any bot-like prefixes
        if ai_reply.startswith("You are a friendly Discord bot") or "as an AI" in ai_reply or "I'm an AI" in ai_reply:
            # Generate a more specific response
            response = client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.95,
                top_p=0.98,
            )
            ai_reply = response.choices[0].message.content
        
        return ai_reply.strip()
    except Exception as e:
        log.error(f"AI API error: {e}")
        # Check if it's an API-related error and use more robust fallback
        error_str = str(e)
        if 'API key' in error_str or '500' in error_str or 'Internal Server Error' in error_str:
            log.warning("API key or server issue detected. Using enhanced fallback responses.")
            enhanced_fallbacks = [
                "That's an interesting point you've raised!",
                "Thanks for sharing your thoughts!",
                "I appreciate your message.",
                "That's a great thing to talk about!",
                "Interesting! Tell me more about this."
            ]
            return random.choice(enhanced_fallbacks)
        else:
            return random.choice(fallback_replies)

async def pick_friendly_reply(content: str, author_mention: str) -> Optional[str]:
    lowered = content.lower()
    for triggers, responses in funny_replies.items():
        if any(t in lowered for t in triggers):
            # Even if there are predefined responses, use AI for more natural replies
            return await generate_friendly_reply_with_ai(lowered, author_mention)
    # If no specific trigger found, still try to generate a relevant reply
    return await generate_friendly_reply_with_ai(lowered, author_mention)

async def duckduckgo_search(query: str) -> str:
    try:
        loop = asyncio.get_running_loop()
        def _sync_search():
            with DDGS() as ddgs:
                results = []
                for r in ddgs.text(query, max_results=3):
                    results.append(f"• [{r['title']}]({r['href']})\n{r['body']}")
                return "\n\n".join(results) if results else "No results found."
        return await loop.run_in_executor(None, _sync_search)
    except Exception as e:
        log.error(f"DuckDuckGo search error: {e}")
        return "Search failed. Please try again later."
@bot.event
async def on_member_join(member):
    if not discord_available:
        return
    try:
        file = discord.File("welcome.mp4", filename="welcome.mp4")
        embed = discord.Embed(
            title=f"🎮 Welcome to {member.guild.name}!",
            description="We're glad to have you here. Enjoy your time and follow the rules!",
            color=discord.Color.purple()
        )
        embed.set_footer(text="9ash Clan | Game On 🎮")
        await member.send(embed=embed, file=file)
        log.info(f"✅ Sent welcome video to {member.name}")
    except discord.Forbidden:
        log.warning(f"❌ Cannot send DM to {member.name}")
    except Exception as e:
        log.error(f"⚠️ Error sending welcome DM: {e}")
IST = pytz.timezone("Asia/Kolkata")  # Change if you're in a different timezone

@tasks.loop(minutes=1)
async def send_daily_greetings():
    now = datetime.now(IST).time()

    morning_time = dtime(7, 0)
    afternoon_time = dtime(12, 0)
    night_time = dtime(22, 0)

    try:
        channel = await bot.fetch_channel(CHANNEL_ID)  # ✅ Use fetch_channel
    except Exception as e:
        print(f"❌ Failed to fetch channel: {e}")
        return

    if now.hour == morning_time.hour and now.minute == morning_time.minute:
        await channel.send("🌅 **Good Morning, 9ash Clan warriors!** Time to rise and grind! 🎮")

    elif now.hour == afternoon_time.hour and now.minute == afternoon_time.minute:
        await channel.send("☀️ **Good Afternoon!** Hope you're having a power-packed day! 💪")

    elif now.hour == night_time.hour and now.minute == night_time.minute:
        await channel.send("🌙 **Good Night everyone!** Recharge well, tomorrow's another game day 💫")

    # Check for Indian festivals and send wishes
    festival = check_indian_festival()
    if festival and festival in indian_festivals:
        try:
            # Generate festival wish with AI
            festival_wish = await generate_festival_wish_with_ai(festival)
            await channel.send(festival_wish)
            
            # If there's an image file available, send it (optional)
            # This would require actual image files in your bot's directory
            # await channel.send(file=discord.File(f"images/{festival}.jpg"))
            
        except Exception as e:
            log.error(f"Error sending festival wish: {e}")


async def handle_wiki_search(message, query: str):
    try:
        async with message.channel.typing():
            clean_query = query.strip()
            if not clean_query:
                await message.reply("Please specify a search term after 'wiki'")
                return
            try:
                summary = wikipedia.summary(clean_query, sentences=3, auto_suggest=True)
                embed = discord.Embed(
                    title=f"Wikipedia: {clean_query}",
                    description=summary,
                    color=discord.Color.blue(),
                    url=f"https://en.wikipedia.org/wiki/{clean_query.replace(' ', '_')}"
                )
                await message.reply(embed=embed)
            except wikipedia.DisambiguationError as e:
                options = "\n".join(f"• {opt}" for opt in e.options[:5])
                await message.reply(f"Multiple matches found:\n{options}\n\nPlease be more specific!")
            except wikipedia.PageError:
                await message.reply(f"No Wikipedia page found for '{clean_query}'. Try different keywords?")
    except Exception as e:
        log.error(f"Wikipedia error: {e}")
        await message.reply("Wikipedia search failed. Try again later.")

async def handle_web_search(message, query: str):
    try:
        async with message.channel.typing():
            clean_query = query.strip()
            if not clean_query:
                await message.reply("Please specify a search term after 'search'")
                return
            results = await duckduckgo_search(clean_query)
            embed = discord.Embed(
                title=f"Search Results: {clean_query}",
                description=results,
                color=discord.Color.green()
            )
            await message.reply(embed=embed)
    except Exception as e:
        log.error(f"Web search error: {e}")
        await message.reply("Web search failed. Please try again later.")

@bot.command(name='festival_wish')
async def send_festival_wish(ctx, festival_name: str = None):
    if not discord_available:
        await ctx.send("Festival wishes are not available in offline mode.")
        return
    """Send a festival wish manually"""
    if festival_name is None:
        # List available festivals
        await ctx.send(f"Available festivals: {', '.join(indian_festivals)}")
        return
    
    festival_name = festival_name.lower()
    if festival_name in indian_festivals:
        festival_wish = await generate_festival_wish_with_ai(festival_name)
        await ctx.send(festival_wish)
    else:
        await ctx.send(f"Sorry, I don't have a wish for '{festival_name}'. Use `!festival_wish` to see available festivals.")

# Function to detect festival-related messages and respond appropriately
async def handle_festival_message(message):
    content = message.content.lower()
    
    for festival_name in indian_festivals:
        if festival_name in content:
            festival_wish = await generate_festival_wish_with_ai(festival_name)
            await message.channel.send(festival_wish)
            
            # Try to send an image if it exists
            try:
                image_path = f"images/{festival_name}.jpg"
                if os.path.exists(image_path):
                    await message.channel.send(file=discord.File(image_path))
            except Exception as e:
                log.error(f"Could not send festival image: {e}")
            break

@bot.command(name='help_cmd')
async def help_command(ctx):
    """Display available commands"""
    if not discord_available:
        await ctx.send("Help command is not available in offline mode.")
        return
    help_text = """
**Available Commands:**

**General:**
!help_cmd - Show this help message
!joke - Tell a random joke

**Games:**
!rps <choice> - Play Rock Paper Scissors (rock/paper/scissors)
!tictactoe <@opponent> - Play Tic Tac Toe with another player
!ttt <row> <col> - Make a move in Tic Tac Toe (0-2)
!hangman - Start a game of Hangman
!guess <letter> - Guess a letter in Hangman
!number_guess [min] [max] - Start a number guessing game
!guess_num <number> - Guess a number
!trivia - Play trivia
!riddle - Get a riddle to solve
!wouldyouRather - Play Would You Rather
!neverHaveIEver - Play Never Have I Ever
!2048 - Learn about the 2048 game
!games - List all available games

**Truth or Dare:**
!truth - Get a truth question
!dare - Get a dare challenge
!truthordare - Get a random truth or dare

**Festival:**
!festival_wish - List available festivals
!festival_wish <festival> - Send specific festival wish

**YouTube:**
!youtube [message] - Send a YouTube update
"""
    await ctx.send(help_text)

async def generate_truth_with_ai() -> str:
    """Generate a truth question using AI"""
    if client is None:
        return get_backup_truth()
    
    try:
        # Vary the prompt to make responses less predictable and more human-like
        human_like_prompts = [
            "Come up with a fun truth question for a party game. Make it interesting but not too personal.",
            "Think of a creative truth question that people would enjoy answering.",
            "Create an engaging truth question for a social game. Keep it fun!",
            "Give me a personal but light-hearted truth question for a group activity.",
        ]
        selected_prompt = random.choice(human_like_prompts)
        
        # Use Hugging Face Inference API (conversational)
        response = client.chat_completion(
            messages=[{"role": "user", "content": selected_prompt}],
            max_tokens=100,
            temperature=0.9,
            top_p=0.95,
        )
        
        question = response.choices[0].message.content.strip()
        # Ensure it ends with a question mark
        if not question.endswith('?'):
            question += '?'
        return f"Truth: {question}"
    except Exception as e:
        log.error(f"AI Truth generation error: {e}")
        return f"Truth: {get_backup_truth()}"

async def generate_dare_with_ai() -> str:
    """Generate a dare challenge using AI"""
    if client is None:
        return get_backup_dare()
    
    try:
        # Vary the prompt to make responses less predictable and more human-like
        human_like_prompts = [
            "Create a fun and harmless dare for a party game. Make it entertaining but safe.",
            "Think of a creative dare challenge that people would enjoy doing.",
            "Come up with an entertaining dare for a social game. Keep it light-hearted!",
            "Give me a fun dare challenge that's safe and amusing for a group activity.",
        ]
        selected_prompt = random.choice(human_like_prompts)
        
        # Use Hugging Face Inference API (conversational)
        response = client.chat_completion(
            messages=[{"role": "user", "content": selected_prompt}],
            max_tokens=100,
            temperature=0.9,
            top_p=0.95,
        )
        
        challenge = response.choices[0].message.content.strip()
        return f"Dare: {challenge}"
    except Exception as e:
        log.error(f"AI Dare generation error: {e}")
        return f"Dare: {get_backup_dare()}"

@bot.command(name='truth')
async def truth_command(ctx):
    """Get a random truth question"""
    if not discord_available:
        await ctx.send("Truth command is not available in offline mode.")
        return
    question = await generate_truth_with_ai()
    await ctx.send(question)

@bot.command(name='dare')
async def dare_command(ctx):
    """Get a random dare challenge"""
    if not discord_available:
        await ctx.send("Dare command is not available in offline mode.")
        return
    challenge = await generate_dare_with_ai()
    await ctx.send(challenge)

@bot.command(name='truthordare')
async def truth_or_dare_command(ctx):
    """Get either a truth or dare randomly"""
    if not discord_available:
        await ctx.send("Truth or Dare command is not available in offline mode.")
        return
    if random.choice([True, False]):
        question = await generate_truth_with_ai()
        await ctx.send(question)
    else:
        challenge = await generate_dare_with_ai()
        await ctx.send(challenge)

async def generate_game_response_with_ai(choice: str, bot_choice: str, result: str) -> str:
    """Generate a human-like game response using AI"""
    if client is None:
        # Fallback to predefined responses
        if result == "You win! 🎉":
            return random.choice(game_responses[choice])
        elif result == "I win! 😄":
            return random.choice(game_responses[bot_choice])
        else:
            return f"We both chose {choice}!"
    
    try:
        outcome = "won" if "win" in result else ("lost" if "win" in result.lower() else "tied")
        # Use Hugging Face Inference API (conversational)
        response = client.chat_completion(
            messages=[{"role": "user", "content": f"Create a fun, human-like response for a Rock Paper Scissors game where the user chose {choice}, bot chose {bot_choice}, and the user {'won' if outcome == 'won' else 'lost' if outcome == 'lost' else 'tied'}. Be casual, friendly and engaging."}],
            max_tokens=100,
            temperature=0.8,
            top_p=0.9,
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        log.error(f"AI Game response generation error: {e}")
        # Check if it's an API-related error and use more robust fallback
        error_str = str(e)
        if 'API key' in error_str or '500' in error_str or 'Internal Server Error' in error_str:
            log.warning("API key or server issue detected. Using enhanced game response.")
            # Create more engaging fallback responses
            if result == "You win! 🎉":
                return f"You got me this time! Good game! 🎉"
            elif result == "I win! 😄":
                return f"Haha! I win this round! Good try though! 😄"
            else:
                return f"Great minds think alike! We both picked {choice}! 😊"
        else:
            # Fallback to predefined responses
            if result == "You win! 🎉":
                return random.choice(game_responses[choice])
            elif result == "I win! 😄":
                return random.choice(game_responses[bot_choice])
            else:
                return f"We both chose {choice}!"

# Dictionary to store active games
active_games = {}

class TicTacToe:
    def __init__(self, player1, player2):
        self.board = [[None for _ in range(3)] for _ in range(3)]
        self.current_player = player1
        self.player1 = player1
        self.player2 = player2
        
    def make_move(self, row, col, player):
        if self.board[row][col] is None and player == self.current_player:
            self.board[row][col] = 'X' if player == self.player1 else 'O'
            self.current_player = self.player2 if player == self.player1 else self.player1
            return True
        return False
        
    def check_winner(self):
        # Check rows
        for row in self.board:
            if row[0] == row[1] == row[2] and row[0] is not None:
                return row[0]
        # Check columns
        for col in range(3):
            if self.board[0][col] == self.board[1][col] == self.board[2][col] and self.board[0][col] is not None:
                return self.board[0][col]
        # Check diagonals
        if self.board[0][0] == self.board[1][1] == self.board[2][2] and self.board[0][0] is not None:
            return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] and self.board[0][2] is not None:
            return self.board[0][2]
        # Check for tie
        if all(cell is not None for row in self.board for cell in row):
            return 'Tie'
        return None
        
    def board_str(self):
        result = "\n   0   1   2\n"
        for i, row in enumerate(self.board):
            result += f"{i}  {row[0] or ' '} | {row[1] or ' '} | {row[2] or ' '}\n"
            if i < 2:
                result += "  -----------\n"
        return result

class Hangman:
    def __init__(self):
        self.words = ["python", "discord", "bot", "programming", "computer", "science", "technology", "artificial", "intelligence", "machine"]
        self.word = random.choice(self.words).upper()
        self.guessed_letters = set()
        self.max_attempts = 6
        self.attempts_left = self.max_attempts
        
    def guess_letter(self, letter):
        letter = letter.upper()
        if letter in self.guessed_letters:
            return f"You already guessed '{letter}'!"
        self.guessed_letters.add(letter)
        if letter not in self.word:
            self.attempts_left -= 1
            return f"Wrong! '{letter}' is not in the word. Attempts left: {self.attempts_left}"
        else:
            return f"Correct! '{letter}' is in the word."
            
    def get_display_word(self):
        display = ""
        for char in self.word:
            if char in self.guessed_letters:
                display += char + " "
            else:
                display += "_ "
        return display
        
    def is_won(self):
        return all(char in self.guessed_letters for char in self.word)
        
    def is_lost(self):
        return self.attempts_left <= 0
        
    def get_status(self):
        status = f"Word: {self.get_display_word()}\nGuessed letters: {', '.join(sorted(self.guessed_letters)) if self.guessed_letters else 'None'}\nAttempts left: {self.attempts_left}/{self.max_attempts}\n"
        return status

class NumberGuessingGame:
    def __init__(self, min_num=1, max_num=100):
        self.min_num = min_num
        self.max_num = max_num
        self.secret_number = random.randint(min_num, max_num)
        self.guesses = []
        
    def make_guess(self, number):
        if number in self.guesses:
            return f"You already guessed {number}!"
        self.guesses.append(number)
        if number == self.secret_number:
            return f"🎉 Congratulations! You guessed the number {self.secret_number} in {len(self.guesses)} attempts! 🎉"
        elif number < self.secret_number:
            return f"Too low! Try a higher number."
        else:
            return f"Too high! Try a lower number."
            
    def get_hint(self):
        if len(self.guesses) == 0:
            return f"I'm thinking of a number between {self.min_num} and {self.max_num}. Can you guess it?"
        closest = min(self.guesses, key=lambda x: abs(x - self.secret_number))
        if closest == self.secret_number:
            return f"You already won! The number was {self.secret_number}."
        elif closest < self.secret_number:
            return f"The number is greater than {closest}."
        else:
            return f"The number is less than {closest}."

@bot.command(name='rps')
async def rock_paper_scissors(ctx, choice: str = None):
    """Play Rock Paper Scissors"""
    if not discord_available:
        await ctx.send("Rock Paper Scissors is not available in offline mode.")
        return
    if choice is None:
        await ctx.send("Please specify your choice: !rps rock, !rps paper, or !rps scissors")
        return
    
    choice = choice.lower()
    if choice not in ['rock', 'paper', 'scissors']:
        await ctx.send("Invalid choice! Please choose: rock, paper, or scissors")
        return
    
    bot_choice = random.choice(['rock', 'paper', 'scissors'])
    
    result = "It's a tie!"
    if (choice == 'rock' and bot_choice == 'scissors') or \
       (choice == 'paper' and bot_choice == 'rock') or \
       (choice == 'scissors' and bot_choice == 'paper'):
        result = "You win! 🎉"
    elif (choice == 'rock' and bot_choice == 'paper') or \
         (choice == 'paper' and bot_choice == 'scissors') or \
         (choice == 'scissors' and bot_choice == 'rock'):
        result = "I win! 😄"
    
    # Generate a human-like game response using AI
    game_response = await generate_game_response_with_ai(choice, bot_choice, result)
    
    await ctx.send(f"You chose {choice}, I chose {bot_choice}. {result}\n{game_response}")

async def generate_youtube_update_with_ai(custom_message: str = None) -> str:
    """Generate a YouTube update message using AI"""
    if client is None:
        # Fallback
        if custom_message:
            return f"{random.choice(youtube_updates)} {custom_message}"
        else:
            return random.choice(youtube_updates)
    
    try:
        prompt = "Create an engaging, human-like YouTube update message."
        if custom_message:
            prompt += f" Include this content: {custom_message}"
        
        # Use Hugging Face Inference API (conversational)
        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.7,
            top_p=0.9,
        )
        update_msg = response.choices[0].message.content.strip()
        return update_msg
    except Exception as e:
        log.error(f"AI YouTube update generation error: {e}")
        # Check if it's an API-related error and use more robust fallback
        error_str = str(e)
        if 'API key' in error_str or '500' in error_str or 'Internal Server Error' in error_str:
            log.warning("API key or server issue detected. Using fallback YouTube update.")
            enhanced_youtube_updates = [
                "Check out my latest video! Would love to hear your thoughts. 📺",
                "New content just dropped! Go check it out! 🎬",
                "I just posted something new! Link in bio! 📝",
                "Fresh upload is live! Don't forget to like and subscribe! 🔥",
                "My newest video is now available! Enjoy watching! 🎥"
            ]
            if custom_message:
                return f"{random.choice(enhanced_youtube_updates)} {custom_message}"
            else:
                return random.choice(enhanced_youtube_updates)
        else:
            if custom_message:
                return f"{random.choice(youtube_updates)} {custom_message}"
            else:
                return random.choice(youtube_updates)

@bot.command(name='youtube')
async def youtube_update(ctx, *, message: str = None):
    """Send a YouTube update message"""
    if not discord_available:
        await ctx.send("YouTube update command is not available in offline mode.")
        return
    
    update_msg = await generate_youtube_update_with_ai(message)
    await ctx.send(update_msg)

@bot.command(name='tictactoe')
async def tictactoe_start(ctx, opponent):
    """Start a game of Tic Tac Toe with another player"""
    if not discord_available:
        await ctx.send("Tic Tac Toe is not available in offline mode.")
        return
    
    game_id = f"ttt-{ctx.channel.id}-{ctx.author.id}-{opponent.id}"
    if game_id in active_games:
        await ctx.send("There's already an active game in this channel!")
        return
    
    game = TicTacToe(ctx.author, opponent)
    active_games[game_id] = game
    
    embed = discord.Embed(
        title="Tic Tac Toe Game Started!",
        description=f"{ctx.author.mention} vs {opponent.mention}\n{ctx.author.mention} is X, {opponent.mention} is O\n{ctx.author.mention} goes first!\n{game.board_str()}",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command(name='ttt')
async def ttt_move(ctx, row: int, col: int):
    """Make a move in Tic Tac Toe. Usage: !ttt <row> <col> (0-2)"""
    if not discord_available:
        await ctx.send("Tic Tac Toe is not available in offline mode.")
        return
    
    # Look for the game involving this channel and the author
    game_id = None
    game = None
    for gid, g in active_games.items():
        if gid.startswith(f"ttt-{ctx.channel.id}-") and ctx.author in [g.player1, g.player2]:
            game_id = gid
            game = g
            break
    
    if not game:
        await ctx.send("You're not in an active Tic Tac Toe game!")
        return
    
    if row < 0 or row > 2 or col < 0 or col > 2:
        await ctx.send("Row and column must be between 0 and 2!")
        return
    
    if game.make_move(row, col, ctx.author):
        winner = game.check_winner()
        
        if winner == 'Tie':
            embed = discord.Embed(
                title="Tic Tac Toe - Game Over!",
                description=f"It's a tie!\n{game.board_str()}",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
            del active_games[game_id]
        elif winner:
            winner_player = game.player1 if winner == 'X' else game.player2
            embed = discord.Embed(
                title="Tic Tac Toe - Game Over!",
                description=f"{winner_player.mention} wins!\n{game.board_str()}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            del active_games[game_id]
        else:
            embed = discord.Embed(
                title="Tic Tac Toe",
                description=f"{game.current_player.mention}'s turn\n{game.board_str()}",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
    else:
        await ctx.send("Invalid move! Either the spot is taken or it's not your turn.")

@bot.command(name='hangman')
async def hangman_start(ctx):
    """Start a game of Hangman"""
    if not discord_available:
        await ctx.send("Hangman is not available in offline mode.")
        return
    
    game_id = f"hangman-{ctx.channel.id}-{ctx.author.id}"
    if game_id in active_games:
        await ctx.send("You're already playing Hangman! Finish your current game first.")
        return
    
    game = Hangman()
    active_games[game_id] = game
    
    embed = discord.Embed(
        title="Hangman Game Started!",
        description=f"Guess the word! {game.get_status()}",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command(name='guess')
async def hangman_guess(ctx, letter: str):
    """Guess a letter in Hangman"""
    if not discord_available:
        await ctx.send("Hangman is not available in offline mode.")
        return
    
    game_id = f"hangman-{ctx.channel.id}-{ctx.author.id}"
    if game_id not in active_games:
        await ctx.send("You're not playing Hangman! Start a game with `!hangman` first.")
        return
    
    game = active_games[game_id]
    result = game.guess_letter(letter)
    
    embed = discord.Embed(
        title="Hangman",
        description=f"{result}\n{game.get_status()}",
        color=discord.Color.red() if "Wrong" in result else discord.Color.green()
    )
    
    if game.is_won():
        embed.title = "Hangman - You Won!"
        embed.color = discord.Color.green()
        embed.description = f"🎉 Congratulations! You guessed the word '{game.word}'! 🎉\n{game.get_status()}"
        del active_games[game_id]
    elif game.is_lost():
        embed.title = "Hangman - Game Over!"
        embed.color = discord.Color.red()
        embed.description = f"💀 You lost! The word was '{game.word}' 💀\n{game.get_status()}"
        del active_games[game_id]
    
    await ctx.send(embed=embed)

@bot.command(name='number_guess')
async def number_guess_start(ctx, min_num: int = 1, max_num: int = 100):
    """Start a number guessing game"""
    if not discord_available:
        await ctx.send("Number guessing game is not available in offline mode.")
        return
    
    game_id = f"number_guess-{ctx.channel.id}-{ctx.author.id}"
    if game_id in active_games:
        await ctx.send("You're already playing a number guessing game! Finish your current game first.")
        return
    
    if min_num >= max_num:
        await ctx.send("Minimum number must be less than maximum number!")
        return
    
    game = NumberGuessingGame(min_num, max_num)
    active_games[game_id] = game
    
    embed = discord.Embed(
        title="Number Guessing Game Started!",
        description=game.get_hint(),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command(name='guess_num')
async def number_guess(ctx, number: int):
    """Make a guess in the number guessing game"""
    if not discord_available:
        await ctx.send("Number guessing game is not available in offline mode.")
        return
    
    game_id = f"number_guess-{ctx.channel.id}-{ctx.author.id}"
    if game_id not in active_games:
        await ctx.send("You're not playing a number guessing game! Start one with `!number_guess` first.")
        return
    
    game = active_games[game_id]
    result = game.make_guess(number)
    
    embed = discord.Embed(
        title="Number Guessing Game",
        description=result,
        color=discord.Color.green() if "Congratulations" in result else discord.Color.red() if "low" in result or "high" in result else discord.Color.orange()
    )
    
    if f"guessed the number {game.secret_number}" in result:
        embed.title = "Number Guessing Game - You Won!"
        del active_games[game_id]
    else:
        embed.add_field(name="Hint", value=game.get_hint(), inline=False)
    
    await ctx.send(embed=embed)

async def generate_joke_with_ai(is_dark: bool = False) -> str:
    """Generate a joke using AI"""
    if client is None:
        # Fallback joke
        return "Why don't scientists trust atoms? Because they make up everything! 😂"
    
    try:
        # Vary the prompt to make responses less predictable and more human-like
        if is_dark:
            human_like_prompts = [
                "Tell me a dark or edgy joke that's clever but not offensive.",
                "Share a slightly twisted joke that makes people think.",
                "Give me a provocative but tasteful dark joke.",
                "Come up with a smart, slightly twisted joke."
            ]
        else:
            human_like_prompts = [
                "Tell me a really funny joke that people would enjoy.",
                "Share a clean and hilarious joke.",
                "Give me a joke that would make someone laugh out loud.",
                "Come up with a genuinely funny clean joke."
            ]
        
        content = random.choice(human_like_prompts)
        
        # Use Hugging Face Inference API (conversational)
        response = client.chat_completion(
            messages=[{"role": "user", "content": content}],
            max_tokens=150,
            temperature=0.9,
            top_p=0.95,
        )
        
        joke = response.choices[0].message.content.strip()
        return joke
    except Exception as e:
        log.error(f"AI Joke generation error: {e}")
        # Check if it's an API-related error and use more robust fallback
        error_str = str(e)
        if 'API key' in error_str or '500' in error_str or 'Internal Server Error' in error_str:
            log.warning("API key or server issue detected. Using enhanced fallback jokes.")
            enhanced_jokes = [
                "Why don't scientists trust atoms? Because they make up everything! 😂",
                "Why did the scarecrow win an award? He was outstanding in his field! 🌾",
                "I told my wife she was drawing her eyebrows too high. She looked surprised. 😮",
                "Why don't skeletons fight each other? They don't have the guts. 💀",
                "What do you call a fake noodle? An impasta! 🍝",
                "Why don't eggs tell jokes? They'd crack each other up! 🥚😂",
                "I'm reading a book about anti-gravity. It's impossible to put down! 📚🚀",
                "Why did the math book look sad? Because it had too many problems! 📖😢",
                "What do you call a bear with no teeth? A gummy bear! 🐻🍬",
                "Why did the computer go to the doctor? It had a virus! 💻🦠"
            ]
            return random.choice(enhanced_jokes)
        else:
            return "Why don't scientists trust atoms? Because they make up everything! 😂"

@bot.command(name='dark_joke')
async def tell_dark_joke(ctx):
    """Tell a dark joke"""
    if not discord_available:
        await ctx.send("Dark joke command is not available in offline mode.")
        return
    
    joke = await generate_joke_with_ai(is_dark=True)
    await ctx.send(joke)

@bot.command(name='normal_joke')
async def tell_normal_joke(ctx):
    """Tell a normal joke"""
    if not discord_available:
        await ctx.send("Normal joke command is not available in offline mode.")
        return
    
    joke = await generate_joke_with_ai(is_dark=False)
    await ctx.send(joke)

@bot.command(name='joke')
async def tell_joke(ctx):
    """Tell a random joke (either dark or normal)"""
    if not discord_available:
        await ctx.send("Joke command is not available in offline mode.")
        return
    
    # Randomly choose between dark and normal joke
    is_dark = random.choice([True, False])
    joke = await generate_joke_with_ai(is_dark=is_dark)
    await ctx.send(joke)
@bot.event
async def on_member_remove(member):
    if not discord_available:
        return
    channel = discord.utils.get(member.guild.text_channels, name="goodbye")  # Change channel name
    if channel:
        file = discord.File("goodbye.mp4", filename="goodbye.mp4")
        embed = discord.Embed(
            title=f"👋 {member.name} just left the server",
            description="Sad to see you go...",
            color=discord.Color.red()
        )
        embed.set_footer(text="9ash Clan Farewell")
        await channel.send(embed=embed, file=file)
@bot.event
async def on_ready():
    if not discord_available:
        return
    log.info("Logged in as %s (%s)", bot.user, bot.user.id)
    if webserver:
        webserver.keep_alive()
    clear_histories.start()
    send_daily_greetings.start()  # Add this line

@bot.event
async def on_message(message):
    if not discord_available:
        return
    if message.author.bot:
        return

    now = datetime.now(timezone.utc)
    uid = message.author.id

    # === SPAM Protection ===
    user_message_times[uid].append(now)
    user_message_times[uid] = [t for t in user_message_times[uid] if (now - t).total_seconds() <= SPAM_TIME_FRAME]
    user_recent_messages[uid].append(message)
    user_recent_messages[uid] = [m for m in user_recent_messages[uid] if (now - m.created_at).total_seconds() <= SPAM_TIME_FRAME]

    if len(user_message_times[uid]) >= SPAM_MESSAGE_LIMIT and not message.author.guild_permissions.administrator:
        try:
            for m in user_recent_messages[uid]:
                await m.delete()
            await message.channel.send(f"{message.author.mention} stop spamming! Timed-out for {TIMEOUT_DURATION}s.")
            until = discord.utils.utcnow() + timedelta(seconds=TIMEOUT_DURATION)
            await message.author.timeout(until, reason="Spam")
        except discord.Forbidden:
            await message.channel.send("⚠️ I lack permission to timeout users.")
        finally:
            user_message_times[uid].clear()
            user_recent_messages[uid].clear()
        return

    # === BANNED WORD CHECK ===
    if banned_words.contains_banned_word(message.content):
        bad_words = banned_words.get_banned_words(message.content)
        try:
            await message.delete()
            warning = (
                f"⚠️ {message.author.mention}, your message contained banned words: "
                f"||{', '.join(set(bad_words))}||\n"
                "**This violates our community guidelines.**"
            )
            await message.channel.send(warning, delete_after=10)
        except discord.Forbidden:
            await message.channel.send("⚠️ I lack permissions to delete messages.")
        return

    # === MODMAIL (DM) ===
    if isinstance(message.channel, discord.DMChannel):
        guild = bot.get_guild(ALLOWED_GUILD_ID)
        mod_channel = discord.utils.get(guild.text_channels, name="mod-mail") if guild else None
        if not mod_channel:
            await message.channel.send("❌ Mod-mail channel not found.")
            return
        embed = discord.Embed(
            title="📬 New Mod-mail",
            description=message.content,
            color=discord.Color.blue()
        )
        embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.display_avatar.url)
        sent = await mod_channel.send(embed=embed)
        modmail_map[sent.id] = message.author.id
        await message.channel.send("✅ Your message has been sent to the moderators!")
        return

    # === WIKI SEARCH ===
    if message.content.lower().startswith("wiki "):
        query = message.content[5:].strip()
        await handle_wiki_search(message, query)
        return

    # === DUCKDUCKGO SEARCH ===
    if message.content.lower().startswith(("search ", "!search ")):
        prefix = "search " if message.content.lower().startswith("search ") else "!search "
        query = message.content[len(prefix):].strip()
        await handle_web_search(message, query)
        return

    # === FESTIVAL WISHES ===
    await handle_festival_message(message)
    
    # === FRIENDLY REPLIES ===
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        lowered = message.content.lower()
        if (answer := get_general_knowledge(lowered)):
            await message.channel.send(answer)
            return
        
        try:
            # Try to generate a friendly reply using AI
            reply = await pick_friendly_reply(lowered, message.author.mention)
            if reply:
                await message.channel.send(reply)
                return
        except Exception as e:
            log.error(f"Error in pick_friendly_reply: {e}")
            await message.channel.send(f"Sorry {message.author.mention}, I had trouble processing your message. Please try again!")
            return
        
        try:
            # Use AI to generate human-like responses
            ai_response = await get_ai_response(message.content)
            if ai_response:
                await message.channel.send(ai_response)
            else:
                # Generate fallback reply using AI
                fallback_reply = await generate_fallback_reply_with_ai(message.content)
                await message.channel.send(fallback_reply)
        except Exception as e:
            log.error(f"Error in AI response generation: {e}")
            await message.channel.send(f"Sorry {message.author.mention}, I encountered an error processing your message.")
        return

    await bot.process_commands(message)

# Additional Games
@bot.command(name='trivia')
async def trivia_game(ctx):
    """Start a trivia game"""
    if not discord_available:
        await ctx.send("Trivia is not available in offline mode.")
        return
    
    # Sample trivia questions
    trivia_questions = [
        {"question": "What is the capital of France?", "answer": "paris", "options": ["Paris", "London", "Berlin", "Rome"]},
        {"question": "Which planet is known as the Red Planet?", "answer": "mars", "options": ["Venus", "Mars", "Jupiter", "Saturn"]},
        {"question": "What is the largest mammal in the world?", "answer": "blue whale", "options": ["Elephant", "Blue Whale", "Giraffe", "Hippopotamus"]},
        {"question": "How many elements are in the periodic table?", "answer": "118", "options": ["108", "118", "128", "98"]},
        {"question": "Who painted the Mona Lisa?", "answer": "leonardo da vinci", "options": ["Vincent van Gogh", "Pablo Picasso", "Leonardo da Vinci", "Michelangelo"]}
    ]
    
    question = random.choice(trivia_questions)
    
    embed = discord.Embed(
        title="🧠 Trivia Question!",
        description=f"{question['question']}\n\nOptions:\nA) {question['options'][0]}\nB) {question['options'][1]}\nC) {question['options'][2]}\nD) {question['options'][3]}\n\nType your answer!",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)
    
    # Store the answer temporarily for checking (in a real implementation, you'd want to implement a proper answer-checking mechanism)
    await ctx.send(f"*Answer: ||{question['answer']}||* (this is just for demo, implement proper answer checking for multiplayer)*")

@bot.command(name='riddle')
async def riddle_game(ctx):
    """Ask a riddle"""
    if not discord_available:
        await ctx.send("Riddles are not available in offline mode.")
        return
    
    riddles = [
        {"riddle": "I speak without a mouth and hear without ears. I have no body, but I come alive with the wind. What am I?", "answer": "echo"},
        {"riddle": "The more you take, the more you leave behind. What am I?", "answer": "footsteps"},
        {"riddle": "What has keys but can't open locks?", "answer": "piano"},
        {"riddle": "I'm tall when I'm young and short when I'm old. What am I?", "answer": "candle"},
        {"riddle": "What can travel around the world while staying in a corner?", "answer": "stamp"}
    ]
    
    riddle = random.choice(riddles)
    
    embed = discord.Embed(
        title="🤔 Riddle Time!",
        description=riddle["riddle"],
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)
    await ctx.send(f"*Answer: ||{riddle['answer']}||* (this is just for demo, implement proper answer checking for multiplayer)*")

@bot.command(name='wouldyouRather')
async def would_you_rather_game(ctx):
    """Play Would You Rather game"""
    if not discord_available:
        await ctx.send("Would You Rather is not available in offline mode.")
        return
    
    would_you_rather_options = [
        {"option1": "have the ability to fly", "option2": "be invisible whenever you want"},
        {"option1": "live without the internet", "option2": "live without air conditioning and heating"},
        {"option1": "be famous but unhappy", "option2": "be unknown but happy"},
        {"option1": "lose all your money", "option2": "lose all your photos"},
        {"option1": "have unlimited food", "option2": "have unlimited travel"}
    ]
    
    choice = random.choice(would_you_rather_options)
    
    embed = discord.Embed(
        title="🤔 Would You Rather...?",
        description=f"A) {choice['option1']}\nOR\nB) {choice['option2']}",
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)

@bot.command(name='neverHaveIEver')
async def never_have_i_ever_game(ctx):
    """Play Never Have I Ever game"""
    if not discord_available:
        await ctx.send("Never Have I Ever is not available in offline mode.")
        return
    
    never_have_i_ever_statements = [
        "eaten something off the floor more than 5 seconds after it fell",
        "pretended to like a gift I didn't want",
        "used the elevator when the stairs were right there",
        "said 'you too' when hanging up the phone first",
        "sent a text to the wrong person"
    ]
    
    statement = random.choice(never_have_i_ever_statements)
    
    embed = discord.Embed(
        title="🤫 Never Have I Ever...",
        description=f"Never have I ever {statement}",
        color=discord.Color.magenta()
    )
    await ctx.send(embed=embed)

@bot.command(name='2048')
async def twenty_forty_eight_game(ctx):
    """Simple 2048 game explanation"""
    if not discord_available:
        await ctx.send("2048 game is not available in offline mode.")
        return
    
    embed = discord.Embed(
        title="🎲 2048 Game",
        description="The 2048 game is a sliding puzzle game where you combine tiles with the same number to create a tile with the number 2048.\n\nUse arrow keys to move the tiles. When two tiles with the same number touch, they merge into one!",
        color=discord.Color.teal()
    )
    await ctx.send(embed=embed)

@bot.command(name='games')
async def games_list(ctx):
    """List all available games"""
    games_description = """
    🎮 **Available Games:**
    • `!rps <choice>` - Play Rock Paper Scissors
    • `!tictactoe <@opponent>` - Play Tic Tac Toe with a friend
    • `!hangman` - Play Hangman
    • `!number_guess [min] [max]` - Number guessing game
    • `!trivia` - Trivia questions
    • `!riddle` - Riddles to solve
    • `!wouldyouRather` - Would You Rather scenarios
    • `!neverHaveIEver` - Never Have I Ever challenges
    • `!2048` - Learn about the 2048 game
    """
    embed = discord.Embed(
        title="🎮 All Available Games",
        description=games_description,
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@tasks.loop(minutes=5)
async def clear_histories():
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=SPAM_TIME_FRAME)
    for uid in list(user_message_times):
        user_message_times[uid] = [t for t in user_message_times[uid] if t > cutoff]
        user_recent_messages[uid] = [m for m in user_recent_messages[uid] if m.created_at > cutoff]
        if not user_message_times[uid]:
            user_message_times.pop(uid, None)
            user_recent_messages.pop(uid, None)


# ============================
# Run Bot
# ============================
# Create a function to get the bot instance for Gunicorn
async def start_bot():
    if not discord_available:
        print("Discord is not available. Cannot start bot in online mode.")
        return
    try:
        await bot.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot crashed: {e}")
        raise

def run():
    """Function to run the bot, compatible with Gunicorn"""
    if discord_available:
        asyncio.run(start_bot())
    else:
        print("Running in offline mode. Discord functionality is not available.")

# For Render deployment compatibility
app = run

if __name__ == "__main__":
    run()
