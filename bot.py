import os
import json
import asyncio
import discord
from discord.ext import commands

# Bot setup with updated intents
intents = discord.Intents.default()
intents.message_content = True

# File paths
QUESTIONS_FILE = 'questions.json'
LEADERBOARD_FILE = 'leaderboard.json'
CURRENT_QUESTION_FILE = 'current_question.json'

# Load questions from JSON
def load_questions():
    try:
        with open(QUESTIONS_FILE, 'r') as f:
            return json.load(f)['questions']
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Error: Could not load questions from {QUESTIONS_FILE}")
        return []

# Get current question index
def get_current_question_index():
    try:
        with open(CURRENT_QUESTION_FILE, 'r') as f:
            return json.load(f).get('no', 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0

# Save current question index
def save_current_question_index(index):
    with open(CURRENT_QUESTION_FILE, 'w') as f:
        json.dump({'no': index}, f)

# Load leaderboard from JSON
def load_leaderboard():
    try:
        with open(LEADERBOARD_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Initialize leaderboard if file doesn't exist
        return {"players": []}

# Update leaderboard
def update_leaderboard(username, points=1):
    leaderboard = load_leaderboard()
    
    # Find existing player or create new
    player = next((p for p in leaderboard['players'] if p['username'] == username), None)
    
    if player:
        player['score'] += points
        player['total_questions_answered'] += 1
    else:
        leaderboard['players'].append({
            'username': username,
            'score': points,
            'total_questions_answered': 1
        })
    
    # Sort leaderboard by score in descending order
    leaderboard['players'] = sorted(
        leaderboard['players'], 
        key=lambda x: x['score'], 
        reverse=True
    )
    
    # Save updated leaderboard
    with open(LEADERBOARD_FILE, 'w') as f:
        json.dump(leaderboard, f, indent=4)
    
    return leaderboard

# Format leaderboard for display
def format_leaderboard(leaderboard):
    if not leaderboard['players']:
        return "Leaderboard is empty!"
    
    # Create a formatted leaderboard string
    lb_text = "🏆 **QUIZ LEADERBOARD** 🏆\n\n"
    for i, player in enumerate(leaderboard['players'][:10], 1):
        lb_text += f"{i}. {player['username']} has {player['score']} points\n"
    
    return lb_text

# Quiz Bot Class
class QuizBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.questions = load_questions()

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        print('------')

    @commands.command(name='start_contest')
    async def start_quiz(self, ctx):
        if not self.questions:
            await ctx.send("No questions available. Please check the questions file.")
            return
        
        # Get the current question index
        no = get_current_question_index()
        
        # Find the question with the matching index
        question_data = next(
            (q for q in self.questions if q.get('no', 0) == no), 
            None
        )
        
        if not question_data:
            await ctx.send("No more questions available or invalid question index.")
            return
        
        # Send the question
        quiz_embed = discord.Embed(
            title="🤔 Quiz Question",
            description=question_data['question'],
            color=discord.Color.yellow()
        )
        await ctx.send(embed=quiz_embed)
        
        # Wait for answer
        def check(message):
            # Case-insensitive answer matching
            return message.channel == ctx.channel and \
                   message.content.lower() == question_data['answer'].lower()
        
        try:
            # Wait for correct answer with 30-second timeout
            msg = await self.wait_for('message', check=check, timeout=30.0)
            
            # Update leaderboard
            leaderboard = update_leaderboard(msg.author.name)
            
            # Congratulate the winner
            await ctx.send(f"🎉 Congratulations {msg.author.mention}! "
                           f"You answered correctly. Current score: {leaderboard['players'][0]['score']} points!")
            
            # Display leaderboard
            await ctx.send(format_leaderboard(leaderboard))
            
        except asyncio.TimeoutError:
            # No one answered in time
            await ctx.send(f"Time's up! The correct answer was: {question_data['answer']}")
        
        # Find the next index
        next_index = no + 1
        
        # Check if we've reached the end of questions
        if not any(q.get('no', 0) == next_index for q in self.questions):
            next_index = 0  # Reset to the first question
        
        # Save the next question index
        save_current_question_index(next_index)

    @commands.command(name='leaderboard')
    async def show_leaderboard(self, ctx):
        leaderboard = load_leaderboard()
        await ctx.send(format_leaderboard(leaderboard))

# Run the bot
def main():
    # Create bot instance with sequential question selection
    bot = QuizBot(command_prefix='/', intents=intents)
    
    # Run the bot (replace with your Discord bot token)
    bot.run('YOUR_DISCORD_BOT_TOKEN')

if __name__ == '__main__':
    main()