# Setting Up Your Telegram Bot for Rin

This guide will walk you through the process of creating a Telegram bot and configuring Rin to use it.

## Step 1: Create a New Bot with BotFather

1. Open Telegram and search for `@BotFather` in the search bar.
2. Start a chat with BotFather by clicking "Start".
3. Send the command `/newbot` to BotFather.
4. BotFather will ask you for a name for your bot. This is the display name that will appear in the user's contact list.
5. Next, BotFather will ask for a username for your bot. This must end with "bot" (e.g., "rin_assistant_bot").
6. Once you've provided a valid username, BotFather will generate a token for your bot. This token looks something like `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`.
7. **Important**: Keep this token secure and don't share it with others. This token allows anyone to control your bot.

## Step 2: Configure Rin to Use Your Telegram Bot

1. Open your `.env` file in the root directory of the Rin project.
2. Add your Telegram bot token to the `TELEGRAM_BOT_TOKEN` variable:
```
TELEGRAM_BOT_TOKEN="your_bot_token_here"
```
3. Save the file.

## Step 3: Start the Telegram Bot

Run the following command to start your Telegram bot:

```bash
rin telegram
```

The bot will continue running until you press Ctrl+C to stop it.

## Step 4: Interact with Your Bot

1. Open Telegram and search for your bot using the username you created.
2. Start a chat with your bot.
3. Send `/start` to begin the interaction.
4. You can now ask your bot questions just like you would in the command line interface.

## Troubleshooting

- If you see an error message about `TELEGRAM_BOT_TOKEN not found`, make sure you've added the token to your `.env` file correctly.
- If the bot doesn't respond, check that the token is valid and that you're running the `rin telegram` command.
- If you need to create a new token, you can send `/revoke` followed by `/newbot` to BotFather.

## Important Notes

- The Telegram bot runs as a separate process. You'll need to keep it running in a terminal window as long as you want your bot to be active.
- For production deployments, consider running the bot as a service or in a container. 