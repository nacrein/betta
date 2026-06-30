from . import config
from .bot import TTSBot


def main() -> None:
    config.require_token()
    bot = TTSBot()
    bot.run(config.TOKEN)


if __name__ == "__main__":
    main()
