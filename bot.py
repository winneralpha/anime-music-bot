import discord
from discord.ext import commands
import yt_dlp
import asyncio
import random
import os

# ─── CONFIG ───────────────────────────────────────────────
TOKEN = os.environ.get("DISCORD_TOKEN")  # Remplace par ton token Discord

# Liste de tes openings (tu peux en ajouter autant que tu veux)
OPENINGS = [
    "Gurenge LiSA Demon Slayer opening",
    "Inferno Mrs Green Apple Dr Stone opening",
    "Silhouette KANA-BOON Naruto Shippuden opening",
    "Guren no Yumiya Attack on Titan opening",
    "Again FMA Brotherhood opening",
    "unravel Tokyo Ghoul opening",
    "Crossing Field Sword Art Online opening",
    "The Day My Hero Academia opening",
    "Odd Future My Hero Academia opening 4",
    "Blue Bird Naruto Shippuden opening",
]

# ─── SETUP ────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Options yt-dlp pour extraire l'audio YouTube
YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

# Stocke les guilds où le bot joue déjà
playing_guilds = set()


# ─── FONCTIONS ────────────────────────────────────────────
async def get_audio_url(query: str) -> str | None:
    """Cherche la musique sur YouTube et retourne l'URL audio."""
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            if "entries" in info and info["entries"]:
                return info["entries"][0]["url"]
        except Exception as e:
            print(f"Erreur yt-dlp : {e}")
    return None


async def play_next(voice_client, guild_id):
    """Lance le prochain opening en aléatoire."""
    if guild_id not in playing_guilds:
        return

    query = random.choice(OPENINGS)
    print(f"[{guild_id}] Lecture : {query}")

    url = await get_audio_url(query)
    if not url:
        print(f"[{guild_id}] Impossible de récupérer l'audio, on réessaie...")
        await asyncio.sleep(2)
        await play_next(voice_client, guild_id)
        return

    def after_play(error):
        if error:
            print(f"Erreur lecture : {error}")
        asyncio.run_coroutine_threadsafe(play_next(voice_client, guild_id), bot.loop)

    source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
    voice_client.play(source, after=after_play)


# ─── ÉVÉNEMENTS ───────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Bot connecté : {bot.user}")


@bot.event
async def on_voice_state_update(member, before, after):
    """Se connecte quand quelqu'un rejoint un salon vocal."""
    if member.bot:
        return

    guild = member.guild

    # Quelqu'un rejoint un salon vocal
    if after.channel and not before.channel:
        voice_client = guild.voice_client

        # Le bot n'est pas encore connecté
        if not voice_client:
            try:
                voice_client = await after.channel.connect()
                playing_guilds.add(guild.id)
                await play_next(voice_client, guild.id)
                print(f"✅ Connecté dans {after.channel.name} sur {guild.name}")
            except Exception as e:
                print(f"Erreur connexion : {e}")

    # Tout le monde a quitté le vocal → le bot se déconnecte
    if before.channel:
        humans = [m for m in before.channel.members if not m.bot]
        if len(humans) == 0:
            voice_client = guild.voice_client
            if voice_client and voice_client.channel == before.channel:
                playing_guilds.discard(guild.id)
                await voice_client.disconnect()
                print(f"🔇 Déconnecté de {before.channel.name} (salon vide)")


# ─── COMMANDES ────────────────────────────────────────────
@bot.command()
async def stop(ctx):
    """!stop — Arrête la musique et déconnecte le bot."""
    if ctx.voice_client:
        playing_guilds.discard(ctx.guild.id)
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Musique arrêtée !")
    else:
        await ctx.send("Je ne suis dans aucun salon vocal.")


@bot.command()
async def skip(ctx):
    """!skip — Passe à l'opening suivant."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Opening suivant !")
    else:
        await ctx.send("Aucune musique en cours.")


@bot.command()
async def volume(ctx, vol: int):
    """!volume <0-100> — Règle le volume."""
    if ctx.voice_client and ctx.voice_client.source:
        if 0 <= vol <= 100:
            ctx.voice_client.source = discord.PCMVolumeTransformer(
                ctx.voice_client.source, volume=vol / 100
            )
            await ctx.send(f"🔊 Volume réglé à {vol}%")
        else:
            await ctx.send("Le volume doit être entre 0 et 100.")
    else:
        await ctx.send("Aucune musique en cours.")


@bot.command()
async def liste(ctx):
    """!liste — Affiche la liste des openings."""
    msg = "🎵 **Liste des openings :**\n"
    for i, o in enumerate(OPENINGS, 1):
        msg += f"`{i}.` {o}\n"
    await ctx.send(msg)


# ─── LANCEMENT ────────────────────────────────────────────
bot.run(TOKEN)
