import asyncio
from sophie_bot.modules.welcomesecurity.utils_.emoji_captcha import EmojiCaptcha

def test():
    c = EmojiCaptcha()
    img = c.image
    print("Captcha image generated: bytes", len(img))

if __name__ == '__main__':
    test()
