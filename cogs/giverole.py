import os
import discord
from discord.ext import commands
import secrets
import string
from datetime import datetime, timedelta, timezone

class GiveRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.BASE_ROLE_NAME = os.getenv("Viewer")
        self.GUILD_ID = int(os.getenv('GUILD_ID')) if os.getenv('GUILD_ID') else None

        self.active_password = None
        self.password_expiry = None
        self.pending_requests = {}

    def generate_new_password(self):
        """Generál egy új, 12 karakteres jelszót, amely 24 óráig érvényes."""
        alphabet = string.ascii_letters + string.digits
        self.active_password = ''.join(secrets.choice(alphabet) for _ in range(12))
        self.password_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
        return self.active_password

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not self.GUILD_ID:
            return
        guild = self.bot.get_guild(self.GUILD_ID)
        if guild:
            role = discord.utils.get(guild.roles, name=self.BASE_ROLE_NAME)
            if role:
                await member.add_roles(role)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Bot üzenetek kihagyása
        if message.author.bot:
            return

        # 2. Csak DM-ek figyelése
        if not isinstance(message.channel, discord.DMChannel):
            return

        content = message.content.strip()
        user_id = message.author.id

        # 3. JELSZÓ GENERÁLÁS (CSAK HDANAVER)
        if content.lower() in ["generate password", "generate"]:
            # Kisbetűssé alakítjuk a nevedet, így biztosan egyezni fog ("hdanaver")
            if message.author.name.lower() != "hdanaver":
                await message.channel.send("❌ Nincs jogosultságod jelszót generálni!")
                return

            pwd = self.generate_new_password()
            await message.channel.send(
                f"🔑 **Új hitelesítési jelszó generálva!**\n"
                f"A jelszó: `{pwd}`\n"
                f"Ez a jelszó **24 óráig** érvényes."
            )
            return

        # 4. RANG IGÉNYLÉS ("give me [rang]")
        if content.lower().startswith("give me "):
            requested_role_name = content[8:].strip()

            if not self.GUILD_ID:
                await message.channel.send("Hiba: A szerver ID nincs beállítva.")
                return

            guild = self.bot.get_guild(self.GUILD_ID)
            if not guild:
                await message.channel.send("Hiba: A szerver nem található.")
                return

            role = discord.utils.get(guild.roles, name=requested_role_name)
            if not role:
                await message.channel.send(f"❌ Ilyen rang (`{requested_role_name}`) nem létezik a szerveren. Ellenőrizd a helyesírást!")
                return

            self.pending_requests[user_id] = requested_role_name
            await message.channel.send(f"✅ Rögzítve! A(z) **{requested_role_name}** rangot kérted. Most írd be DM-ben magát a jelszót a megerősítéshez:")
            return

        # 5. JELSZÓ ELLENŐRZÉSE
        if user_id in self.pending_requests:
            if not self.active_password or not self.password_expiry:
                await message.channel.send("Még nincs aktív jelszó a rendszerben. Kérj meg egy admint, hogy generáljon egyet!")
                return

            if datetime.now(timezone.utc) > self.password_expiry:
                self.pending_requests.pop(user_id, None)
                await message.channel.send("❌ Az aktuális jelszó lejárt! Kérj egy újat.")
                return

            if content == self.active_password:
                target_role_name = self.pending_requests.pop(user_id)
                
                guild = self.bot.get_guild(self.GUILD_ID)
                member = guild.get_member(user_id)

                if not member:
                    await message.channel.send("Nem talállak a szerveren! Biztosan bent vagy?")
                    return

                role = discord.utils.get(guild.roles, name=target_role_name)
                if not role:
                    await message.channel.send(f"Hiba: A(z) **{target_role_name}** rang közben eltűnt a szerverről.")
                    return

                if role in member.roles:
                    await message.channel.send("Már birtoklod ezt a rangot!")
                    return

                await member.add_roles(role)
                await message.channel.send(f"🎉 Siker! Megkaptad a(z) **{target_role_name}** rangot.")
                return
            else:
                await message.channel.send("❌ Hibás jelszó! Próbáld újra beírni a helyes jelszót.")
                return

        # 6. EGYÉB ÜZENETEK
        await message.channel.send("Üdv! Használd a `give me [Rang Neve]` formátumot (pl. `give me Uni victim`), majd válaszul add meg a jelszót.")


async def setup(bot):
    await bot.add_cog(GiveRole(bot))